"""
L3 向量记忆 — ChromaDB 持久化语义搜索
"""
import json
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.config import config
from app.models import VectorMemoryEntry

logger = logging.getLogger(__name__)


class VectorMemory:
    """基于 ChromaDB 的长期向量记忆。

    使用注意：需要先安装 chromadb (`pip install chromadb`)。
    如果 chromadb 不可用，所有操作将静默降级（返回空结果）。
    """

    def __init__(
        self,
        db: Session,
        persist_dir: Optional[Path] = None,
        collection_name: str = "agent_memories",
    ):
        self.db = db
        self.persist_dir = persist_dir or config.CHROMADB_PATH
        self.collection_name = collection_name
        self._collection = None
        self._client = None
        self._ready = False
        self._init_chroma()

    # ------------------------------------------------------------------
    # 初始化
    # ------------------------------------------------------------------

    def _init_chroma(self):
        try:
            import chromadb
            self._client = chromadb.PersistentClient(path=str(self.persist_dir))
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            self._ready = True
            logger.info("ChromaDB 已连接: %s (%s)", self.collection_name, self.persist_dir)
        except ImportError:
            logger.warning("chromadb 未安装，向量记忆功能不可用 (pip install chromadb)")
        except Exception as e:
            logger.error("ChromaDB 初始化失败: %s", e)

    # ------------------------------------------------------------------
    # 写入
    # ------------------------------------------------------------------

    def store(
        self,
        agent_id: str,
        text: str,
        metadata: Optional[dict] = None,
        conversation_id: str = "",
    ) -> bool:
        """存入一条向量记忆。"""
        if not self._ready or not text.strip():
            return False

        doc_id = str(uuid.uuid4())
        meta = {
            "agent_id": agent_id,
            "conversation_id": conversation_id or "",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **(metadata or {}),
        }

        try:
            self._collection.add(
                documents=[text],
                metadatas=[meta],
                ids=[doc_id],
            )

            # 同步记录到关系库
            entry = VectorMemoryEntry(
                agent_id=agent_id,
                chunk_id=doc_id,
                content=text[:500],
                metadata_json=json.dumps(meta, ensure_ascii=False),
            )
            self.db.add(entry)
            self.db.commit()
            return True
        except Exception as e:
            logger.error("向量记忆存储失败: %s", e)
            return False

    def store_batch(self, agent_id: str, items: list[dict]) -> int:
        """批量存入，items 每项: {"text": ..., "metadata": {...}}。"""
        success = 0
        for item in items:
            if self.store(agent_id, item["text"], item.get("metadata")):
                success += 1
        return success

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def query(
        self,
        agent_id: str,
        query_text: str,
        top_k: int = 5,
        filter_metadata: Optional[dict] = None,
    ) -> list[dict[str, Any]]:
        """语义搜索最相关的记忆片段。"""
        if not self._ready:
            return []

        # 构建过滤条件
        where = {"agent_id": agent_id}
        if filter_metadata:
            where.update(filter_metadata)

        try:
            results = self._collection.query(
                query_texts=[query_text],
                n_results=min(top_k, 50),
                where=where,
            )

            hits = []
            if results["ids"]:
                for i, doc_id in enumerate(results["ids"][0]):
                    hits.append({
                        "chunk_id": doc_id,
                        "text": results["documents"][0][i] if results["documents"] else "",
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": results["distances"][0][i] if results["distances"] else 0.0,
                    })
            return hits
        except Exception as e:
            logger.error("向量记忆查询失败: %s", e)
            return []

    # ------------------------------------------------------------------
    # 管理
    # ------------------------------------------------------------------

    def delete_by_agent(self, agent_id: str) -> int:
        """删除某 Agent 的所有向量记忆。"""
        if not self._ready:
            return 0

        try:
            count = self._collection.delete(where={"agent_id": agent_id})
            deleted = self.db.query(VectorMemoryEntry).filter(
                VectorMemoryEntry.agent_id == agent_id
            ).delete()
            self.db.commit()
            logger.info("已删除 agent %s 的向量记忆: chroma=%s db=%d", agent_id, count, deleted)
            return deleted
        except Exception as e:
            logger.error("删除向量记忆失败: %s", e)
            return 0

    def count(self, agent_id: Optional[str] = None) -> int:
        """统计记忆条目数。"""
        q = self.db.query(VectorMemoryEntry)
        if agent_id:
            q = q.filter(VectorMemoryEntry.agent_id == agent_id)
        return q.count()

    @property
    def is_ready(self) -> bool:
        return self._ready
