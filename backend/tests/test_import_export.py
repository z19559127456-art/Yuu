"""
Tests for ImportExport — export/import agents and conversations.
"""
import json
import pytest
from datetime import datetime, timezone

from app.import_export import ImportExport, ExportResult, ImportResult


class TestImportExport:
    def test_export_empty_database(self, db_session):
        ie = ImportExport()
        result = ie.export_agents(db=db_session)
        assert result.success is False
        assert "没有找到" in result.error

    def test_export_single_agent(self, db_session, sample_agent):
        ie = ImportExport()
        result = ie.export_agents(db=db_session, agent_ids=[sample_agent.id])
        assert result.success is True
        assert result.item_count == 1
        assert result.data is not None
        assert result.data["export_version"] == "1.0"
        assert result.data["agents"][0]["name"] == "测试助手"

    def test_export_with_conversations(self, db_session, sample_agent, sample_conversation):
        from app.models import Message
        db_session.add(Message(conversation_id=sample_conversation.id, role="user", content="你好"))
        db_session.add(Message(conversation_id=sample_conversation.id, role="assistant", content="你好！"))
        db_session.commit()

        ie = ImportExport()
        result = ie.export_agents(db=db_session, include_conversations=True)
        assert result.success is True
        agent_data = result.data["agents"][0]
        assert len(agent_data["conversations"]) == 1
        assert len(agent_data["conversations"][0]["messages"]) == 2

    def test_export_to_json_file(self, db_session, sample_agent, tmp_path):
        ie = ImportExport()
        file_path = str(tmp_path / "test_export.json")
        result = ie.export_to_file(db=db_session, file_path=file_path)
        assert result.success is True
        assert result.file_path.endswith(".json")
        # Verify file content
        with open(result.file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["export_version"] == "1.0"
        assert len(data["agents"]) == 1

    def test_import_skip_existing(self, db_session, sample_agent):
        """merge_mode='skip' should skip existing agents."""
        export_data = {
            "export_version": "1.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "agents": [sample_agent.to_dict()],
        }
        ie = ImportExport()
        result = ie.import_from_data(db=db_session, data=export_data, merge_mode="skip")
        assert result.success is True
        assert result.skipped_count == 1
        assert len(result.imported_agents) == 0

    def test_import_overwrite_existing(self, db_session, sample_agent):
        """merge_mode='overwrite' should update existing agents."""
        agent_dict = sample_agent.to_dict()
        agent_dict["name"] = "已更新助手"
        export_data = {
            "export_version": "1.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "agents": [agent_dict],
        }
        ie = ImportExport()
        result = ie.import_from_data(db=db_session, data=export_data, merge_mode="overwrite")
        assert result.success is True
        db_session.refresh(sample_agent)
        assert sample_agent.name == "已更新助手"

    def test_import_create_copy(self, db_session, sample_agent):
        """merge_mode='create_copy' should create new agents with new IDs."""
        export_data = {
            "export_version": "1.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "agents": [sample_agent.to_dict()],
        }
        ie = ImportExport()
        result = ie.import_from_data(db=db_session, data=export_data, merge_mode="create_copy")
        assert result.success is True
        assert len(result.imported_agents) == 1
        assert result.imported_agents[0]["id"] != sample_agent.id

    def test_import_new_agent(self, db_session):
        """Import an agent that doesn't exist yet."""
        agent_data = {
            "id": "new-agent-1",
            "name": "导入的助手",
            "role": "助手",
            "model_provider": "openai",
            "model_name": "gpt-4o",
            "temperature": 0.7,
            "max_tokens": 4096,
            "personality": {"style": "友好"},
            "tools_config": {"cli": {"enabled": False}},
            "skills": [],
            "memory_config": {},
            "concurrency_config": {},
            "tags": [],
            "is_active": True,
        }
        export_data = {
            "export_version": "1.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "agents": [agent_data],
        }
        ie = ImportExport()
        result = ie.import_from_data(db=db_session, data=export_data)
        assert result.success is True
        assert len(result.imported_agents) == 1
        assert result.imported_agents[0]["name"] == "导入的助手"

    def test_import_empty_data(self, db_session):
        export_data = {"export_version": "1.0", "agents": []}
        ie = ImportExport()
        result = ie.import_from_data(db=db_session, data=export_data)
        assert result.success is False

    def test_import_with_conversations(self, db_session):
        """Import with conversations and messages."""
        agent_data = {
            "id": "agent-with-conv",
            "name": "有对话的Agent",
            "conversations": [
                {
                    "id": "conv-1",
                    "title": "测试对话",
                    "messages": [
                        {"role": "user", "content": "你好", "type": "text"},
                        {"role": "assistant", "content": "你好！", "type": "text"},
                    ],
                }
            ],
        }
        export_data = {"export_version": "1.0", "agents": [agent_data]}
        ie = ImportExport()
        result = ie.import_from_data(db=db_session, data=export_data)
        assert result.success is True
        assert len(result.imported_conversations) == 1

    def test_validate_export_data_valid(self):
        data = {
            "export_version": "1.0",
            "agents": [{"name": "Agent1", "conversations": [{"title": "对话1", "messages": [{"role": "user", "content": "hi"}]}]}],
        }
        issues = ImportExport.validate_export_data(data)
        assert issues == []

    def test_validate_export_data_missing_name(self):
        data = {
            "export_version": "1.0",
            "agents": [{"name": ""}],
        }
        issues = ImportExport.validate_export_data(data)
        assert len(issues) > 0
        assert any("name" in issue for issue in issues)

    def test_validate_export_data_wrong_version(self):
        data = {"export_version": "0.5", "agents": []}
        issues = ImportExport.validate_export_data(data)
        assert any("版本号" in issue for issue in issues)

    def test_export_result_dataclass(self):
        r = ExportResult(success=True, item_count=5, file_path="/tmp/export.json")
        assert r.success is True
        assert r.item_count == 5

    def test_import_result_dataclass(self):
        r = ImportResult(success=True, imported_agents=[{"id": "1"}], skipped_count=2)
        assert r.success is True
        assert len(r.imported_agents) == 1

    def test_export_handles_exception(self, db_session, mocker):
        ie = ImportExport()
        mocker.patch.object(db_session, "query", side_effect=Exception("DB error"))
        result = ie.export_agents(db=db_session)
        assert result.success is False
        assert "DB error" in result.error
