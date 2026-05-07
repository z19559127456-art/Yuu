"""
Tests for GroupChatBus — group management, participants, turn order, callbacks.
"""
import pytest
from app.group_chat_bus import (
    GroupChatBus, BusMessage, BusEvent,
    TurnStrategy, MessageScope,
)


class TestGroupChatBus:
    def test_create_group(self, db_session, sample_agent):
        bus = GroupChatBus(db=db_session)
        group = bus.create_group("测试群组", created_by=sample_agent.id, topic="AI话题")
        assert group.id is not None
        assert group.title == "测试群组"
        assert group.mode == "discussion"
        assert group.status == "active"

    def test_create_group_with_task_mode(self, db_session, sample_agent):
        bus = GroupChatBus(db=db_session)
        group = bus.create_group("任务组", sample_agent.id, mode="task")
        assert group.mode == "task"

    def test_archive_group(self, db_session, sample_agent):
        bus = GroupChatBus(db=db_session)
        group = bus.create_group("测试", sample_agent.id)
        result = bus.archive_group(group.id)
        assert result is True
        db_session.refresh(group)
        assert group.status == "archived"

    def test_archive_nonexistent(self, db_session):
        bus = GroupChatBus(db=db_session)
        result = bus.archive_group("no-such-group")
        assert result is False

    def test_add_participant(self, db_session, sample_agent):
        bus = GroupChatBus(db=db_session)
        group = bus.create_group("群组", sample_agent.id)
        result = bus.add_participant(group.id, sample_agent.id, role="moderator")
        assert result is True
        participants = bus.get_participants(group.id)
        assert len(participants) == 1
        assert participants[0].role == "moderator"

    def test_add_duplicate_participant(self, db_session, sample_agent):
        bus = GroupChatBus(db=db_session)
        group = bus.create_group("群组", sample_agent.id)
        bus.add_participant(group.id, sample_agent.id)
        result = bus.add_participant(group.id, sample_agent.id)
        assert result is True  # should not crash

    def test_add_participant_nonexistent_group(self, db_session, sample_agent):
        bus = GroupChatBus(db=db_session)
        result = bus.add_participant("no-such", sample_agent.id)
        assert result is False

    def test_remove_participant(self, db_session, sample_agent):
        bus = GroupChatBus(db=db_session)
        group = bus.create_group("群组", sample_agent.id)
        bus.add_participant(group.id, sample_agent.id)
        result = bus.remove_participant(group.id, sample_agent.id)
        assert result is True
        assert len(bus.get_participants(group.id)) == 0

    def test_remove_nonexistent_participant(self, db_session, sample_agent):
        bus = GroupChatBus(db=db_session)
        group = bus.create_group("群组", sample_agent.id)
        result = bus.remove_participant(group.id, "no-such-agent")
        assert result is False

    def test_get_active_agents(self, db_session, sample_agent):
        bus = GroupChatBus(db=db_session)
        group = bus.create_group("群组", sample_agent.id)
        bus.add_participant(group.id, sample_agent.id)
        agents = bus.get_active_agents(group.id)
        assert len(agents) == 1
        assert agents[0].name == "测试助手"

    def test_inactive_agent_excluded(self, db_session):
        from app.models import Agent
        agent = Agent(name="禁用", is_active=False)
        db_session.add(agent)
        db_session.commit()

        bus = GroupChatBus(db=db_session)
        g = bus.create_group("群组", agent.id)
        bus.add_participant(g.id, agent.id)
        agents = bus.get_active_agents(g.id)
        assert len(agents) == 0

    def test_message_callbacks(self, db_session, sample_agent):
        bus = GroupChatBus(db=db_session)
        callback_events = []

        def my_callback(event):
            callback_events.append(event)

        bus.on_message(my_callback)
        event = BusEvent(
            message=BusMessage(group_id="g1", sender_id=sample_agent.id, content="hello"),
            group=None,
            sender=sample_agent,
            participants=[],
        )
        bus._trigger_callbacks(event)
        assert len(callback_events) == 1

    def test_remove_callback(self, db_session):
        bus = GroupChatBus(db=db_session)
        events = []

        def cb(event):
            events.append(event)

        bus.on_message(cb)
        bus.remove_callback(cb)
        bus._trigger_callbacks(BusEvent(
            message=BusMessage(), group=None, sender=None, participants=[]
        ))
        assert len(events) == 0

    def test_callback_exception_isolation(self, db_session):
        bus = GroupChatBus(db=db_session)
        events = []

        def broken_callback(event):
            raise ValueError("oops")

        def good_callback(event):
            events.append(event)

        bus.on_message(broken_callback)
        bus.on_message(good_callback)
        bus._trigger_callbacks(BusEvent(
            message=BusMessage(), group=None, sender=None, participants=[]
        ))
        assert len(events) == 1

    def test_turn_strategy(self, db_session, sample_agent):
        bus = GroupChatBus(db=db_session)
        bus.set_turn_strategy("g1", "free")
        assert bus._strategy["g1"] == TurnStrategy.FREE

    def test_next_turn_round_robin(self, db_session, sample_agent):
        from app.models import Agent
        a2 = Agent(name="Agent2")
        db_session.add(a2)
        db_session.commit()

        bus = GroupChatBus(db=db_session)
        g = bus.create_group("群组", sample_agent.id)
        bus.add_participant(g.id, sample_agent.id)
        bus.add_participant(g.id, a2.id)

        # Should cycle through agents
        first = bus.next_turn(g.id)
        second = bus.next_turn(g.id)
        third = bus.next_turn(g.id)
        assert first is not None
        assert second is not None
        assert first != second
        assert third == first  # wraps around

    def test_discussion_rounds(self, db_session, sample_agent):
        bus = GroupChatBus(db=db_session)
        g = bus.create_group("群组", sample_agent.id)
        r = bus.start_round(g.id, topic="话题")
        assert r is not None
        assert r.round_number == 1

        r2 = bus.start_round(g.id, topic="话题2")
        assert r2.round_number == 2

        assert bus.end_round(r.id) is True

    def test_bus_message_dataclass(self):
        msg = BusMessage(
            id="m1", group_id="g1", sender_id="s1",
            sender_name="Alice", content="hello",
        )
        d = msg.to_dict()
        assert d["id"] == "m1"
        assert d["content"] == "hello"

    def test_cleanup(self, db_session):
        bus = GroupChatBus(db=db_session)
        bus.on_message(lambda e: None)
        bus.set_turn_strategy("g1", "free")
        bus.cleanup()
        assert len(bus._callbacks) == 0
        assert len(bus._strategy) == 0
