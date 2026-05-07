"""
数据迁移脚本 — 支持数据库版本升级和回滚。

用法:
  python -m scripts.migrate status              # 查看当前版本
  python -m scripts.migrate upgrade             # 升级到最新版本
  python -m scripts.migrate upgrade --target 2  # 升级到指定版本
  python -m scripts.migrate downgrade --target 0  # 回滚到指定版本
  python -m scripts.migrate history             # 查看迁移历史

数据库版本通过 _migrations 表追踪，每次迁移有 up/down 两个方向。
"""
import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

from app.database import Base, SQLALCHEMY_DATABASE_URL
from app.config import config

logger = logging.getLogger("migrate")
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")


engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ---------------------------------------------------------------------------
# 迁移注册表 — 每个迁移是一个 (version, name, up_sql, down_sql) 元组
# version 从 1 开始递增，0 表示初始空库
# ---------------------------------------------------------------------------

MIGRATIONS = [
    # v1: 初始 schema（所有 Phase 1-3 模型的基线）
    {
        "version": 1,
        "name": "initial_schema",
        "description": "创建所有核心表的初始版本",
        "up": None,   # None = 使用 Base.metadata.create_all
        "down": None,  # None = 使用 Base.metadata.drop_all
    },
    # v2: 添加 L3 向量记忆索引表
    {
        "version": 2,
        "name": "add_vector_memory_index",
        "description": "为向量记忆添加全文搜索索引",
        "up": """
            CREATE INDEX IF NOT EXISTS idx_vector_memory_agent
                ON vector_memory_entries(agent_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_vector_memory_chunk
                ON vector_memory_entries(chunk_id);
        """,
        "down": """
            DROP INDEX IF EXISTS idx_vector_memory_agent;
            DROP INDEX IF EXISTS idx_vector_memory_chunk;
        """,
    },
    # v3: 添加审计日志索引 + 性能优化
    {
        "version": 3,
        "name": "add_audit_performance_indexes",
        "description": "为审计日志和高频查询添加性能索引",
        "up": """
            CREATE INDEX IF NOT EXISTS idx_audit_agent_time
                ON audit_logs(agent_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_audit_action
                ON audit_logs(action, created_at);
            CREATE INDEX IF NOT EXISTS idx_messages_conv_time
                ON messages(conversation_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_subtasks_plan_status
                ON subtasks(plan_id, status);
            CREATE INDEX IF NOT EXISTS idx_plans_agent_status
                ON plans(agent_id, status);
        """,
        "down": """
            DROP INDEX IF EXISTS idx_audit_agent_time;
            DROP INDEX IF EXISTS idx_audit_action;
            DROP INDEX IF EXISTS idx_messages_conv_time;
            DROP INDEX IF EXISTS idx_subtasks_plan_status;
            DROP INDEX IF EXISTS idx_plans_agent_status;
        """,
    },
    # v4: 添加消息全文搜索支持
    {
        "version": 4,
        "name": "add_message_fts",
        "description": "为消息内容添加全文搜索虚拟表",
        "up": """
            CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                content,
                content_rowid='rowid',
                tokenize='unicode61'
            );
        """,
        "down": """
            DROP TABLE IF EXISTS messages_fts;
        """,
    },
    # v5: 添加 Agent 标签和分组支持
    {
        "version": 5,
        "name": "add_agent_tags_index",
        "description": "为 Agent 标签 JSON 字段添加辅助表和索引",
        "up": """
            CREATE TABLE IF NOT EXISTS agent_tags (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
                tag TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(agent_id, tag)
            );
            CREATE INDEX IF NOT EXISTS idx_agent_tags_tag
                ON agent_tags(tag);
            CREATE INDEX IF NOT EXISTS idx_conversations_updated
                ON conversations(updated_at);
        """,
        "down": """
            DROP TABLE IF EXISTS agent_tags;
            DROP INDEX IF EXISTS idx_agent_tags_tag;
            DROP INDEX IF EXISTS idx_conversations_updated;
        """,
    },
    # v6: 添加消息 group_id 字段（群聊消息分组支持）
    {
        "version": 6,
        "name": "add_message_group_id",
        "description": "为 messages 表添加 group_id 列以支持群聊消息持久化",
        "up": """
            ALTER TABLE messages ADD COLUMN group_id VARCHAR;
            CREATE INDEX IF NOT EXISTS idx_messages_group_id
                ON messages(group_id, created_at);
        """,
        "down": """
            DROP INDEX IF EXISTS idx_messages_group_id;
        """,
    },
]

LATEST_VERSION = max(m["version"] for m in MIGRATIONS) if MIGRATIONS else 0


# ---------------------------------------------------------------------------
# 内部工具函数
# ---------------------------------------------------------------------------

def _ensure_migration_table():
    """确保 _migrations 追踪表存在。"""
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS _migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                applied_at TEXT NOT NULL,
                direction TEXT NOT NULL DEFAULT 'up'
            )
        """))
        conn.commit()


def _get_current_version() -> int:
    """获取当前数据库版本。如果 _migrations 表不存在则返回 0。"""
    inspector = inspect(engine)
    if "_migrations" not in inspector.get_table_names():
        # 检查是否有其他表存在（可能是在迁移系统之前创建的）
        tables = inspector.get_table_names()
        if tables:
            # 如果有任何已知的表，假定为 v1
            known_tables = {"agents", "conversations", "messages", "plans", "subtasks"}
            if known_tables & set(tables):
                return 1
        return 0

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT MAX(version) FROM _migrations WHERE direction = 'up'")
        ).fetchone()
        return row[0] if row[0] is not None else 0


def _record_migration(version: int, name: str, description: str, direction: str):
    """在 _migrations 表中记录一次迁移。"""
    with engine.connect() as conn:
        conn.execute(
            text(
                "INSERT INTO _migrations (version, name, description, applied_at, direction) "
                "VALUES (:version, :name, :description, :applied_at, :direction)"
            ),
            {
                "version": version,
                "name": name,
                "description": description,
                "applied_at": datetime.now(timezone.utc).isoformat(),
                "direction": direction,
            },
        )
        conn.commit()


def _get_migration(version: int) -> Optional[dict]:
    """按版本号获取迁移定义。"""
    for m in MIGRATIONS:
        if m["version"] == version:
            return m
    return None


def _run_sql(sql: str):
    """执行原始 SQL（多条语句用分号分隔）。"""
    if not sql or not sql.strip():
        return
    with engine.connect() as conn:
        for statement in sql.strip().split(";"):
            stmt = statement.strip()
            if stmt:
                try:
                    conn.execute(text(stmt))
                except Exception as e:
                    logger.warning("SQL 执行警告 (已跳过): %s — %s", stmt[:80], e)
        conn.commit()


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------

def upgrade(target: Optional[int] = None):
    """升级数据库到 target 版本（默认最新）。"""
    _ensure_migration_table()
    current = _get_current_version()
    target = target or LATEST_VERSION

    if current >= target:
        logger.info("数据库已是最新版本 v%d，无需升级。", current)
        return

    logger.info("升级数据库: v%d → v%d", current, target)

    for m in MIGRATIONS:
        if m["version"] <= current:
            continue
        if m["version"] > target:
            break

        logger.info("应用迁移 v%d: %s — %s", m["version"], m["name"], m["description"])

        if m["up"] is not None:
            _run_sql(m["up"])
        else:
            # 完整 schema 创建
            from app.models import (  # noqa: F401
                Agent, Conversation, Message, TaskRecord, MemorySummary,
                WebRecord, UIRecord, VisionRecord, Plan, SubTask,
                TaskExecution, SkillRecord, VectorMemoryEntry,
                GroupConversation, GroupParticipant, DiscussionRound, AuditLog,
            )
            Base.metadata.create_all(bind=engine)

        _record_migration(m["version"], m["name"], m["description"], "up")
        logger.info("✓ 迁移 v%d 完成", m["version"])

    logger.info("数据库升级完成: v%d → v%d", current, _get_current_version())


def downgrade(target: int):
    """回滚数据库到 target 版本。"""
    _ensure_migration_table()
    current = _get_current_version()

    if current <= target:
        logger.info("数据库已在 v%d，无需回滚。", current)
        return

    logger.info("回滚数据库: v%d → v%d", current, target)

    # 从高版本到低版本反向执行 down
    for m in reversed(MIGRATIONS):
        if m["version"] <= target:
            break
        if m["version"] > current:
            continue

        logger.info("回滚迁移 v%d: %s", m["version"], m["name"])

        if m["down"] is not None:
            _run_sql(m["down"])
        else:
            Base.metadata.drop_all(bind=engine)

        _record_migration(m["version"], m["name"], m["description"], "down")
        logger.info("✓ 回滚 v%d 完成", m["version"])

    logger.info("数据库回滚完成: v%d → v%d", current, _get_current_version())


def reset():
    """完全重置数据库（删除所有表并重建到最新版本）。"""
    logger.warning("即将完全重置数据库！所有数据将被删除。")
    response = input("确认操作？输入 'yes' 继续: ")
    if response.lower() != "yes":
        logger.info("已取消。")
        return

    Base.metadata.drop_all(bind=engine)
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS _migrations"))
        conn.commit()

    logger.info("所有表已删除，开始重建...")
    upgrade(target=LATEST_VERSION)
    logger.info("数据库已重置到最新版本 v%d。", LATEST_VERSION)


def history():
    """显示迁移历史。"""
    _ensure_migration_table()
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT version, name, description, applied_at, direction "
                 "FROM _migrations ORDER BY applied_at")
        ).fetchall()

    if not rows:
        logger.info("没有迁移记录。当前版本: v%d", _get_current_version())
        return

    print(f"\n{'版本':<6} {'名称':<30} {'方向':<6} {'时间':<26} 描述")
    print("-" * 110)
    for r in rows:
        direction = "↑" if r.direction == "up" else "↓"
        print(f"v{r.version:<5} {r.name:<30} {direction:<6} {r.applied_at:<26} {r.description}")


def status():
    """显示当前数据库版本状态。"""
    current = _get_current_version()
    print(f"当前数据库版本: v{current}")
    print(f"最新可用版本:   v{LATEST_VERSION}")

    if current < LATEST_VERSION:
        pending = [m for m in MIGRATIONS if m["version"] > current]
        print(f"\n待应用的迁移 ({len(pending)}):")
        for m in pending:
            print(f"  v{m['version']}: {m['name']} — {m['description']}")
    elif current == LATEST_VERSION:
        print("\n数据库已是最新版本。 ✓")
    else:
        print(f"\n⚠ 数据库版本 (v{current}) 超过已知最新版本 (v{LATEST_VERSION})")


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Yu — 数据库迁移工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m scripts.migrate status
  python -m scripts.migrate upgrade
  python -m scripts.migrate upgrade --target 3
  python -m scripts.migrate downgrade --target 0
  python -m scripts.migrate history
  python -m scripts.migrate reset
        """,
    )

    sub = parser.add_subparsers(dest="command", help="可用命令")

    sub.add_parser("status", help="显示当前数据库版本状态")
    sub.add_parser("history", help="显示迁移历史记录")
    sub.add_parser("reset", help="完全重置数据库（危险操作）")

    up_parser = sub.add_parser("upgrade", help="升级数据库到最新版本")
    up_parser.add_argument("--target", type=int, default=None, help="目标版本号（默认: 最新）")

    down_parser = sub.add_parser("downgrade", help="回滚数据库到指定版本")
    down_parser.add_argument("--target", type=int, required=True, help="目标版本号")

    args = parser.parse_args()

    if args.command == "status":
        status()
    elif args.command == "history":
        history()
    elif args.command == "upgrade":
        upgrade(target=args.target)
    elif args.command == "downgrade":
        downgrade(target=args.target)
    elif args.command == "reset":
        reset()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
