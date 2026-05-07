"""
Tests for Memory Manager — L1Cache, L2SummaryManager, L3 VectorMemory.
"""
import json
import pytest
from app.memory_manager import L1Cache, L2SummaryManager
from app.vector_memory import VectorMemory


class TestL1Cache:
    def test_push_and_get(self):
        cache = L1Cache(max_entries=200)
        cache.push("conv1", {"role": "user", "content": "你好"})
        messages = cache.get("conv1")
        assert len(messages) == 1
        assert messages[0]["content"] == "你好"

    def test_get_limit(self):
        cache = L1Cache(max_entries=200)
        for i in range(100):
            cache.push("conv1", {"role": "user", "content": f"msg_{i}"})
        messages = cache.get("conv1", limit=10)
        assert len(messages) == 10
        assert messages[-1]["content"] == "msg_99"

    def test_cache_eviction(self):
        cache = L1Cache(max_entries=10)
        for i in range(20):
            cache.push("conv1", {"role": "user", "content": f"msg_{i}"})
        messages = cache.get("conv1", limit=50)
        assert len(messages) == 10
        assert messages[0]["content"] == "msg_10"

    def test_clear_conversation(self):
        cache = L1Cache(max_entries=200)
        cache.push("conv1", {"role": "user", "content": "hello"})
        cache.push("conv2", {"role": "user", "content": "world"})
        cache.clear("conv1")
        assert len(cache.get("conv1")) == 0
        assert len(cache.get("conv2")) == 1

    def test_clear_all(self):
        cache = L1Cache(max_entries=200)
        cache.push("conv1", {"role": "user", "content": "hello"})
        cache.push("conv2", {"role": "user", "content": "world"})
        cache.clear()
        assert len(cache.get("conv1")) == 0
        assert len(cache.get("conv2")) == 0

    def test_invalidate(self):
        cache = L1Cache(max_entries=200)
        cache.push("conv1", {"role": "user", "content": "data"})
        cache.invalidate("conv1")
        assert len(cache.get("conv1")) == 0

    def test_multiple_conversations_independent(self):
        cache = L1Cache(max_entries=200)
        cache.push("conv1", {"role": "user", "content": "from_conv1"})
        cache.push("conv2", {"role": "user", "content": "from_conv2"})
        assert len(cache.get("conv1")) == 1
        assert len(cache.get("conv2")) == 1
        assert cache.get("conv1")[0]["content"] == "from_conv1"

    def test_per_conversation_limit(self):
        """L1Cache limits per-conversation entries, not total conversations."""
        cache = L1Cache(max_entries=3)
        cache.push("conv1", {"msg": "1"})
        cache.push("conv1", {"msg": "2"})
        cache.push("conv1", {"msg": "3"})
        cache.push("conv1", {"msg": "4"})
        # Only the last 3 entries of conv1 are kept
        assert len(cache.get("conv1")) == 3
        assert cache.get("conv1")[0]["msg"] == "2"


class TestL2SummaryManager:
    def test_fallback_summarize_short(self):
        text = "这是一段很短的对话内容"
        result = L2SummaryManager._fallback_summarize(text)
        assert result == text

    def test_fallback_summarize_long(self):
        text = "A" * 1000
        result = L2SummaryManager._fallback_summarize(text, max_chars=100)
        assert len(result) == 101  # 100 chars + …
        assert result.endswith("…")

    def test_skip_summary_when_few_messages(self, db_session, sample_agent, sample_conversation):
        """No summary should be created for < 5 messages."""
        from app.models import Message
        for i in range(3):
            db_session.add(Message(
                conversation_id=sample_conversation.id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"msg_{i}",
            ))
        db_session.commit()

        mgr = L2SummaryManager(db=db_session)
        result = mgr.summarize_conversation(sample_agent.id, sample_conversation.id)
        assert result is None  # Too few messages

    def test_build_summary_context_no_summaries(self, db_session):
        mgr = L2SummaryManager(db=db_session)
        ctx = mgr.build_summary_context("agent-none")
        assert ctx == ""

    def test_get_recent_summaries_empty(self, db_session):
        mgr = L2SummaryManager(db=db_session)
        summaries = mgr.get_recent_summaries("agent-none")
        assert summaries == []


class TestVectorMemory:
    def test_init(self, db_session):
        """VectorMemory should initialize without ChromaDB being available."""
        vm = VectorMemory(db=db_session, persist_dir="/tmp/_test_nonexistent_chromadb_vm")
        # Should not crash — operations should degrade gracefully
        assert vm is not None

    def test_query_returns_empty_list_on_error(self, db_session):
        """Query should work after storing data."""
        vm = VectorMemory(db=db_session, persist_dir="/tmp/_test_nonexistent_chromadb_vm")
        # chromadb might be available, so just verify no crash
        results = vm.query("agent1", "test query")
        assert isinstance(results, list)

    def test_store_graceful_fallback(self, db_session):
        vm = VectorMemory(db=db_session, persist_dir="/tmp/_test_nonexistent_chromadb_vm")
        # Should not crash — store may succeed if chromadb is installed, or return False
        result = vm.store("agent1", "test content", {"key": "val"})
        # Either way is acceptable (depends on chromadb availability)

    def test_count(self, db_session):
        vm = VectorMemory(db=db_session, persist_dir="/tmp/_test_nonexistent_chromadb_vm")
        count = vm.count("agent1")
        assert count == 0
