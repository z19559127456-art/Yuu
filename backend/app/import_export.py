"""
Import / Export — agents, conversations, and settings in JSON format.
"""
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from zipfile import ZipFile, ZIP_DEFLATED

from sqlalchemy.orm import Session

from app.models import Agent, Conversation, Message

logger = logging.getLogger(__name__)


@dataclass
class ExportResult:
    success: bool
    data: dict | None = None
    file_path: str = ""
    item_count: int = 0
    error: str = ""
    execution_time_ms: int = 0


@dataclass
class ImportResult:
    success: bool = False
    imported_agents: list[dict] = field(default_factory=list)
    imported_conversations: list[dict] = field(default_factory=list)
    skipped_count: int = 0
    errors: list[str] = field(default_factory=list)
    execution_time_ms: int = 0


class ImportExport:
    """Import and export agents, conversations, and settings."""

    EXPORT_VERSION = "1.0"

    # ---- Export ----

    def export_agents(
        self,
        db: Session,
        agent_ids: list[str] | None = None,
        include_conversations: bool = True,
        pretty: bool = True,
    ) -> ExportResult:
        """Export agents (and optionally their conversations) to a dict."""
        import time
        start = time.monotonic()

        try:
            query = db.query(Agent)
            if agent_ids:
                query = query.filter(Agent.id.in_(agent_ids))
            agents = query.all()

            if not agents:
                return ExportResult(
                    success=False,
                    error="没有找到可导出的 Agent",
                    execution_time_ms=int((time.monotonic() - start) * 1000),
                )

            agent_list = []
            for agent in agents:
                agent_data = agent.to_dict()
                if include_conversations:
                    convs = (
                        db.query(Conversation)
                        .filter(Conversation.agent_id == agent.id)
                        .all()
                    )
                    agent_data["conversations"] = []
                    for conv in convs:
                        conv_data = conv.to_dict()
                        msgs = (
                            db.query(Message)
                            .filter(Message.conversation_id == conv.id)
                            .order_by(Message.created_at)
                            .all()
                        )
                        conv_data["messages"] = [m.to_dict() for m in msgs]
                        agent_data["conversations"].append(conv_data)
                agent_list.append(agent_data)

            elapsed = int((time.monotonic() - start) * 1000)
            return ExportResult(
                success=True,
                data={
                    "export_version": self.EXPORT_VERSION,
                    "exported_at": datetime.now(timezone.utc).isoformat(),
                    "agents": agent_list,
                },
                item_count=len(agent_list),
                execution_time_ms=elapsed,
            )
        except Exception as e:
            logger.error(f"Export error: {e}")
            return ExportResult(
                success=False,
                error=str(e),
                execution_time_ms=int((time.monotonic() - start) * 1000),
            )

    def export_to_file(
        self,
        db: Session,
        file_path: str,
        agent_ids: list[str] | None = None,
        include_conversations: bool = True,
        compress: bool = False,
    ) -> ExportResult:
        """Export to a JSON file or zip archive."""
        result = self.export_agents(db, agent_ids, include_conversations)
        if not result.success:
            return result

        try:
            json_str = json.dumps(
                result.data,
                ensure_ascii=False,
                indent=2,
                default=str,
            )

            if compress:
                zip_path = file_path + ".zip" if not file_path.endswith(".zip") else file_path
                with ZipFile(zip_path, "w", ZIP_DEFLATED) as zf:
                    base_name = os.path.basename(file_path).replace(".zip", ".json")
                    zf.writestr(base_name, json_str.encode("utf-8"))
                result.file_path = zip_path
            else:
                json_path = file_path if file_path.endswith(".json") else file_path + ".json"
                os.makedirs(os.path.dirname(os.path.abspath(json_path)), exist_ok=True)
                with open(json_path, "w", encoding="utf-8") as f:
                    f.write(json_str)
                result.file_path = json_path

            return result
        except Exception as e:
            logger.error(f"Export to file error: {e}")
            return ExportResult(
                success=False,
                error=str(e),
            )

    # ---- Import ----

    def import_from_data(
        self,
        db: Session,
        data: dict,
        merge_mode: str = "skip",  # skip | overwrite | create_copy
    ) -> ImportResult:
        """Import agents and conversations from a dict.

        merge_mode:
        - skip: skip existing agents by ID
        - overwrite: overwrite existing agents by ID
        - create_copy: always create with new IDs
        """
        import time
        start = time.monotonic()

        result = ImportResult()

        try:
            version = data.get("export_version", "0.9")
            agents_data = data.get("agents", [])

            if not agents_data:
                result.errors.append("导入数据中没有 Agent")
                result.execution_time_ms = int((time.monotonic() - start) * 1000)
                return result

            for agent_data in agents_data:
                agent_id = agent_data.get("id", "")
                conversations_data = agent_data.pop("conversations", [])

                existing = (
                    db.query(Agent).filter(Agent.id == agent_id).first()
                    if agent_id else None
                )

                if existing:
                    if merge_mode == "skip":
                        result.skipped_count += 1
                        continue
                    elif merge_mode == "overwrite":
                        self._update_agent_from_dict(existing, agent_data)
                        agent = existing
                    else:  # create_copy
                        agent_data.pop("id", None)
                        agent = self._create_agent_from_dict(db, agent_data)
                else:
                    agent = self._create_agent_from_dict(db, agent_data)

                db.flush()
                agent_id = agent.id  # capture ID after flush
                result.imported_agents.append(agent.to_dict())

                # Import conversations
                for conv_data in conversations_data:
                    self._import_conversation(db, agent_id, conv_data, merge_mode)
                    result.imported_conversations.append({
                        "id": conv_data.get("id", ""),
                        "title": conv_data.get("title", ""),
                    })

            db.commit()

            elapsed = int((time.monotonic() - start) * 1000)
            result.success = True
            result.execution_time_ms = elapsed
            return result

        except Exception as e:
            db.rollback()
            logger.error(f"Import error: {e}")
            result.errors.append(str(e))
            result.execution_time_ms = int((time.monotonic() - start) * 1000)
            return result

    def import_from_file(
        self,
        db: Session,
        file_path: str,
        merge_mode: str = "skip",
    ) -> ImportResult:
        """Import from a JSON file or zip archive."""
        import time
        start = time.monotonic()

        try:
            ext = os.path.splitext(file_path)[1].lower()

            if ext == ".zip":
                with ZipFile(file_path, "r") as zf:
                    json_files = [n for n in zf.namelist() if n.endswith(".json")]
                    if not json_files:
                        return ImportResult(
                            errors=["ZIP 文件中没有找到 JSON"],
                            execution_time_ms=int((time.monotonic() - start) * 1000),
                        )
                    with zf.open(json_files[0]) as f:
                        data = json.loads(f.read().decode("utf-8"))
            elif ext == ".json":
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                return ImportResult(
                    errors=[f"不支持的文件格式: {ext}"],
                    execution_time_ms=int((time.monotonic() - start) * 1000),
                )

            return self.import_from_data(db, data, merge_mode=merge_mode)

        except Exception as e:
            logger.error(f"Import from file error: {e}")
            return ImportResult(
                errors=[str(e)],
                execution_time_ms=int((time.monotonic() - start) * 1000),
            )

    # ---- Internal helpers ----

    def _create_agent_from_dict(self, db: Session, data: dict) -> Agent:
        """Create a new Agent from a dict."""
        agent = Agent(
            name=data.get("name", "导入的Agent"),
            avatar=data.get("avatar", ""),
            role=data.get("role", ""),
            system_prompt=data.get("system_prompt", ""),
            model_provider=data.get("model_provider", "openai"),
            model_name=data.get("model_name", "gpt-4o"),
            temperature=data.get("temperature", 0.7),
            max_tokens=data.get("max_tokens", 4096),
            personality_json=json.dumps(data.get("personality", {}), ensure_ascii=False),
            tools_config_json=json.dumps(data.get("tools_config", {}), ensure_ascii=False),
            skills_json=json.dumps(data.get("skills", []), ensure_ascii=False),
            memory_config_json=json.dumps(data.get("memory_config", {}), ensure_ascii=False),
            concurrency_config_json=json.dumps(data.get("concurrency_config", {}), ensure_ascii=False),
            tags_json=json.dumps(data.get("tags", []), ensure_ascii=False),
            is_active=data.get("is_active", True),
        )
        db.add(agent)
        return agent

    def _update_agent_from_dict(self, agent: Agent, data: dict):
        """Update an existing Agent from a dict."""
        for field in (
            "name", "avatar", "role", "system_prompt",
            "model_provider", "model_name", "temperature", "max_tokens",
            "is_active",
        ):
            if field in data:
                setattr(agent, field, data[field])

        json_fields = {
            "personality": "personality_json",
            "tools_config": "tools_config_json",
            "skills": "skills_json",
            "memory_config": "memory_config_json",
            "concurrency_config": "concurrency_config_json",
            "tags": "tags_json",
        }
        for dict_key, attr in json_fields.items():
            if dict_key in data:
                setattr(agent, attr, json.dumps(data[dict_key], ensure_ascii=False))

        agent.updated_at = datetime.now(timezone.utc)

    def _import_conversation(
        self,
        db: Session,
        agent_id: str,
        conv_data: dict,
        merge_mode: str,
    ):
        """Import a single conversation with its messages."""
        conv_id = conv_data.get("id", "")
        messages_data = conv_data.pop("messages", [])

        existing = (
            db.query(Conversation).filter(Conversation.id == conv_id).first()
            if conv_id else None
        )

        if existing:
            if merge_mode == "skip":
                return
            elif merge_mode == "overwrite":
                existing.title = conv_data.get("title", existing.title)
                conv = existing
                # Delete existing messages
                db.query(Message).filter(
                    Message.conversation_id == conv.id
                ).delete()
            else:
                conv_data.pop("id", None)
                conv = Conversation(
                    agent_id=agent_id,
                    title=conv_data.get("title", "导入的对话"),
                )
                db.add(conv)
                db.flush()
                conv_id = conv.id
        else:
            conv = Conversation(
                id=conv_id or None,
                agent_id=agent_id,
                title=conv_data.get("title", "导入的对话"),
            )
            db.add(conv)
            db.flush()
            conv_id = conv.id

        for msg_data in messages_data:
            msg_data.pop("id", None)  # always create new message IDs
            msg = Message(
                conversation_id=conv_id,
                role=msg_data.get("role", "user"),
                type=msg_data.get("type", "text"),
                content=msg_data.get("content", ""),
                content_html=msg_data.get("content_html", ""),
                attachments_json=json.dumps(msg_data.get("attachments", []), ensure_ascii=False),
                tool_calls_json=json.dumps(msg_data.get("tool_calls", []), ensure_ascii=False),
                tool_results_json=json.dumps(msg_data.get("tool_results", []), ensure_ascii=False),
                status=msg_data.get("status", "sent"),
            )
            db.add(msg)

    @staticmethod
    def validate_export_data(data: dict) -> list[str]:
        """Validate export data structure and return a list of issues."""
        issues = []
        if not isinstance(data, dict):
            issues.append("根节点必须是 object")
            return issues

        if data.get("export_version", "") != ImportExport.EXPORT_VERSION:
            issues.append(f"版本号不匹配: 期望 {ImportExport.EXPORT_VERSION}")

        agents = data.get("agents", [])
        if not isinstance(agents, list):
            issues.append("agents 必须是数组")
            return issues

        for i, agent in enumerate(agents):
            if not agent.get("name"):
                issues.append(f"agents[{i}]: 缺少 name")
            if agent.get("conversations"):
                for j, conv in enumerate(agent["conversations"]):
                    if not conv.get("title"):
                        issues.append(f"agents[{i}].conversations[{j}]: 缺少 title")
                    if conv.get("messages"):
                        for k, msg in enumerate(conv["messages"]):
                            if not msg.get("role"):
                                issues.append(
                                    f"agents[{i}].conversations[{j}].messages[{k}]: 缺少 role"
                                )

        return issues
