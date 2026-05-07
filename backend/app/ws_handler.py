"""
WebSocket message router — Agent CRUD, LLM streaming, conversation management,
tool execution, planning, group chat, memory, and message operations.
"""
import json
import os
import time
import asyncio
import logging
import traceback
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    Agent, Conversation, Message, Plan, SubTask, TaskExecution,
    GroupConversation, GroupParticipant,
)
from app.llm_client import LLMClient, LLMConfig, llm_client_from_agent
from app.context_manager import ContextManager

# Dialog B — tools
from app.cli_tool import CLITool
from app.web_tool import WebTool, WebAction
from app.ui_tool import UITool
from app.vision_tool import VisionTool

# Dialog C — planner/worker/critic/orchestrator
from app.planner import Planner
from app.worker import Worker
from app.critic import Critic
from app.orchestrator import Orchestrator
from app.concurrency import TaskQueue

# Dialog D — skills & memory
from app.skill_manager import SkillRegistry
from app.memory_manager import L1Cache, L2SummaryManager
from app.vector_memory import VectorMemory

# Dialog E — group chat & security
from app.collaboration_engine import CollaborationEngine
from app.group_chat_bus import GroupChatBus
from app.deadlock_detector import DeadlockDetector
from app.security import PermissionChecker, AuditLogger

logger = logging.getLogger(__name__)


def _send_json(ws, data):
    """Send a JSON message over WebSocket."""
    ws.send(json.dumps(data, ensure_ascii=False))


def _get_api_keys() -> dict:
    """Read API keys from environment."""
    return {
        "openai": os.getenv("OPENAI_API_KEY", ""),
        "anthropic": os.getenv("ANTHROPIC_API_KEY", ""),
    }


def _run_async(coro):
    """Run an async coroutine synchronously from a sync Flask-Sock handler."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    # Already in an event loop — shouldn't happen in Flask-Sock, but handle gracefully
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor() as pool:
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result()


def _extract_tool_calls(content: str) -> list[dict]:
    """Parse LLM output for tool call syntax.

    Looks for patterns like:
      TOOL_CALL: tool_name({"key": "value"})
    or JSON blocks containing tool_calls.
    """
    tool_calls = []
    lines = content.split("\n")
    for line in lines:
        line = line.strip()
        if line.startswith("TOOL_CALL:"):
            rest = line[len("TOOL_CALL:"):].strip()
            # Format: tool_name({"key": "value"})
            paren = rest.find("(")
            if paren > 0 and rest.endswith(")"):
                name = rest[:paren].strip()
                try:
                    args = json.loads(rest[paren + 1:-1])
                    tool_calls.append({"name": name, "arguments": args})
                except json.JSONDecodeError:
                    pass
    # Also look for JSON-based tool_calls in code fences
    import re
    pattern = r'```json\s*\{\s*"tool_calls":\s*\[(.*?)\]\s*\}\s*```'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        try:
            parsed = json.loads("{" + f'"tool_calls": [{match.group(1)}]' + "}")
            tool_calls.extend(parsed.get("tool_calls", []))
        except json.JSONDecodeError:
            pass
    return tool_calls


def _execute_single_tool(
    tool_name: str,
    arguments: dict,
    tools_config: dict,
    api_keys: dict,
) -> dict:
    """Execute a single tool by name and return the result dict."""
    start = time.time()

    try:
        if tool_name == "cli":
            cli_cfg = tools_config.get("cli", {})
            tool = CLITool(
                allowed_commands=cli_cfg.get("allowed_commands", []),
                blocked_commands=cli_cfg.get("blocked_commands", []),
            )
            command = arguments.get("command", "")
            result = _run_async(tool.execute(command))
            return {
                "success": result.success,
                "output": result.output,
                "error": result.stderr if not result.success else "",
                "duration_ms": int((time.time() - start) * 1000),
            }

        elif tool_name == "web":
            web_cfg = tools_config.get("web", {})
            tool = WebTool(
                max_pages=web_cfg.get("max_pages", 10),
                allowed_domains=web_cfg.get("allowed_domains", []),
                blocked_domains=web_cfg.get("blocked_domains", []),
            )
            action = arguments.get("action", "navigate")
            url = arguments.get("url", "")
            result = _run_async(tool.execute(WebAction(action=action, params={"url": url})))
            return {
                "success": result.success,
                "output": result.output or result.page_url,
                "error": result.error,
                "duration_ms": int((time.time() - start) * 1000),
            }

        elif tool_name == "ui":
            tool = UITool(
                require_confirmation=False,
                timeout_seconds=30,
            )
            action = arguments.get("action", "click")
            params = arguments.get("params", {})
            result = _run_async(tool.execute(action, **params))
            return {
                "success": getattr(result, "success", True),
                "output": getattr(result, "output", str(result)),
                "error": getattr(result, "error", ""),
                "duration_ms": int((time.time() - start) * 1000),
            }

        elif tool_name == "vision":
            tool = VisionTool(
                api_key=api_keys.get("openai", ""),
                provider=arguments.get("provider", "openai"),
            )
            image_source = arguments.get("image_source", "screenshot")
            prompt = arguments.get("prompt", "Describe this image.")
            result = _run_async(tool.analyze(image_source=image_source, prompt=prompt))
            return {
                "success": result.success,
                "output": result.analysis,
                "error": result.error,
                "duration_ms": int((time.time() - start) * 1000),
            }

        else:
            return {
                "success": False,
                "output": "",
                "error": f"Unknown tool: {tool_name}",
                "duration_ms": 0,
            }

    except Exception as e:
        logger.exception(f"Tool execution error: {tool_name}")
        return {
            "success": False,
            "output": "",
            "error": str(e),
            "duration_ms": int((time.time() - start) * 1000),
        }


def _execute_tool_calls(ws, db, agent, conversation_id, assistant_msg, tool_calls):
    """Execute tool calls from LLM function calling and append results."""
    for tc in tool_calls:
        tool_name = tc.get("name", "")
        arguments = tc.get("arguments", {})
        tools_config = json.loads(agent.tools_config_json or "{}")
        api_keys = _get_api_keys()

        # Notify frontend that a tool is being executed
        _send_json(ws, {
            "type": "tool_executing",
            "tool_name": tool_name,
            "arguments": arguments,
        })

        result = _execute_single_tool(tool_name, arguments, tools_config, api_keys)

        # Notify frontend of result
        _send_json(ws, {
            "type": "tool_result",
            "tool_call_id": tc.get("id", tool_name),
            "result": result.get("output", ""),
            "status": "success" if result.get("success") else "error",
            "error": result.get("error", ""),
        })

        # Log execution
        exec_record = TaskExecution(
            agent_id=agent.id,
            conversation_id=conversation_id,
            task_type=f"tool_{tool_name}",
            input_json=json.dumps(arguments, ensure_ascii=False),
            output_json=json.dumps(result, ensure_ascii=False),
            status="success" if result.get("success") else "failed",
            error_message=result.get("error", ""),
            duration_ms=result.get("duration_ms", 0),
        )
        db.add(exec_record)
    db.commit()


def handle_message(ws, data: dict, db: Session):
    """Route incoming WebSocket messages to the appropriate handler."""
    msg_type = data.get("type", "")

    # ---- Ping ----
    if msg_type == "ping":
        _send_json(ws, {"type": "pong"})
        return

    # ---- Agent CRUD ----
    if msg_type == "get_agents":
        agents = db.query(Agent).filter(Agent.is_active == True).all()
        _send_json(ws, {"type": "agent_list", "agents": [a.to_dict() for a in agents]})
        return

    if msg_type == "create_agent":
        name = data.get("name", "新Agent")
        agent = Agent(
            name=name,
            role=data.get("role", ""),
            system_prompt=data.get("system_prompt", "你是一个有用的AI助手。"),
            model_provider=data.get("model_provider", "openai"),
            model_name=data.get("model_name", "gpt-4o"),
            temperature=data.get("temperature", 0.7),
            max_tokens=data.get("max_tokens", 4096),
            api_base_url=data.get("api_base_url", ""),
            api_key=data.get("api_key", ""),
            personality_json=json.dumps(data.get("personality", {"style": "严谨", "tone": "专业", "verbosity": "concise"}), ensure_ascii=False),
            tools_config_json=json.dumps(data.get("tools_config", {
                "cli": {"enabled": False, "allowed_commands": [], "blocked_commands": []},
                "web": {"enabled": False, "max_pages": 10, "allowed_domains": [], "blocked_domains": []},
                "ui_automation": {"enabled": False},
                "vision": {"enabled": False},
            }), ensure_ascii=False),
            skills_json=json.dumps(data.get("skills", []), ensure_ascii=False),
            tags_json=json.dumps(data.get("tags", []), ensure_ascii=False),
            is_active=True,
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)
        _send_json(ws, {"type": "agent_created", "agent": agent.to_dict()})
        return

    if msg_type == "update_agent":
        agent_id = data.get("agent_id")
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            _send_json(ws, {"type": "error", "message": "Agent not found"})
            return

        if "name" in data:
            agent.name = data["name"]
        if "role" in data:
            agent.role = data["role"]
        if "system_prompt" in data:
            agent.system_prompt = data["system_prompt"]
        if "model_provider" in data:
            agent.model_provider = data["model_provider"]
        if "model_name" in data:
            agent.model_name = data["model_name"]
        if "temperature" in data:
            agent.temperature = data["temperature"]
        if "max_tokens" in data:
            agent.max_tokens = data["max_tokens"]
        if "api_base_url" in data:
            agent.api_base_url = data["api_base_url"]
        if "api_key" in data:
            agent.api_key = data["api_key"]
        if "personality" in data:
            agent.personality_json = json.dumps(data["personality"], ensure_ascii=False)
        if "tools_config" in data:
            agent.tools_config_json = json.dumps(data["tools_config"], ensure_ascii=False)
        if "skills" in data:
            agent.skills_json = json.dumps(data["skills"], ensure_ascii=False)
        if "tags" in data:
            agent.tags_json = json.dumps(data["tags"], ensure_ascii=False)
        if "is_active" in data:
            agent.is_active = data["is_active"]

        agent.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(agent)
        _send_json(ws, {"type": "agent_updated", "agent": agent.to_dict()})
        return

    if msg_type == "delete_agent":
        agent_id = data.get("agent_id")
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            _send_json(ws, {"type": "error", "message": "Agent not found"})
            return
        db.delete(agent)
        db.commit()
        _send_json(ws, {"type": "agent_deleted", "agent_id": agent_id})
        return

    # ---- Conversation CRUD ----
    if msg_type == "get_conversations":
        agent_id = data.get("agent_id")
        if not agent_id:
            _send_json(ws, {"type": "error", "message": "Missing agent_id"})
            return
        convs = (
            db.query(Conversation)
            .filter(Conversation.agent_id == agent_id)
            .order_by(Conversation.updated_at.desc())
            .all()
        )
        _send_json(ws, {
            "type": "conversation_list",
            "conversations": [c.to_dict() for c in convs],
        })
        return

    if msg_type == "get_messages":
        conversation_id = data.get("conversation_id")
        if not conversation_id:
            _send_json(ws, {"type": "error", "message": "Missing conversation_id"})
            return
        msgs = (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .all()
        )
        _send_json(ws, {
            "type": "message_list",
            "messages": [m.to_dict() for m in msgs],
        })
        return

    if msg_type == "create_conversation":
        agent_id = data.get("agent_id")
        if not agent_id:
            _send_json(ws, {"type": "error", "message": "Missing agent_id"})
            return
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            _send_json(ws, {"type": "error", "message": "Agent not found"})
            return

        conv = Conversation(agent_id=agent_id, title="新对话")
        db.add(conv)
        db.commit()
        db.refresh(conv)
        _send_json(ws, {"type": "conversation_created", "conversation": conv.to_dict()})
        return

    if msg_type == "delete_conversation":
        conv_id = data.get("conversation_id")
        conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
        if not conv:
            _send_json(ws, {"type": "error", "message": "Conversation not found"})
            return
        db.delete(conv)
        db.commit()
        _send_json(ws, {"type": "conversation_deleted", "conversation_id": conv_id})
        return

    # ---- Send Message (with LLM integration) ----
    if msg_type == "send_message":
        conversation_id = data.get("conversation_id")
        content = data.get("content", "")
        if not conversation_id or not content.strip():
            _send_json(ws, {"type": "error", "message": "Missing conversation_id or content"})
            return

        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conv:
            _send_json(ws, {"type": "error", "message": "Conversation not found"})
            return

        agent = db.query(Agent).filter(Agent.id == conv.agent_id).first()
        if not agent:
            _send_json(ws, {"type": "error", "message": "Agent not found"})
            return

        # 1. Save user message
        user_msg = Message(
            conversation_id=conversation_id,
            role="user",
            content=content.strip(),
        )
        db.add(user_msg)
        db.commit()
        db.refresh(user_msg)
        _send_json(ws, {"type": "new_message", "message": user_msg.to_dict()})

        # 2. Update conversation title from first message
        msg_count = db.query(Message).filter(Message.conversation_id == conversation_id).count()
        if msg_count <= 2:
            title = content.strip()[:50]
            if len(content.strip()) > 50:
                title += "…"
            conv.title = title
        conv.updated_at = datetime.now(timezone.utc)
        db.commit()

        # 3. Create assistant message placeholder
        assistant_msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content="",
            status="sending",
        )
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)
        _send_json(ws, {"type": "new_message", "message": assistant_msg.to_dict()})

        # 4. Build context and call LLM
        api_keys = _get_api_keys()
        context_mgr = ContextManager(db, api_keys)
        messages = context_mgr.build_messages(agent, conversation_id, content.strip())

        llm = llm_client_from_agent(agent, api_keys)

        # 5. Stream response
        full_content = ""
        try:
            for chunk in llm.stream_sync(messages):
                full_content += chunk
                # Send incremental update
                _send_json(ws, {
                    "type": "message_update",
                    "message_id": assistant_msg.id,
                    "content": full_content,
                })
                # Small delay to avoid flooding the socket
                time.sleep(0.02)

            # After streaming, check if LLM wants to call tools (function calling)
            tool_calls = _extract_tool_calls(full_content)
            if tool_calls:
                assistant_msg.tool_calls_json = json.dumps(tool_calls, ensure_ascii=False)
                _execute_tool_calls(ws, db, agent, conversation_id, assistant_msg, tool_calls)
        except Exception as e:
            logger.error(f"LLM streaming error: {e}")
            full_content += f"\n\n[生成失败: {e}]"

        # 6. Save final message
        assistant_msg.content = full_content
        assistant_msg.status = "sent"
        db.commit()
        db.refresh(assistant_msg)

        # Send final version
        _send_json(ws, {"type": "message_final", "message": assistant_msg.to_dict()})
        return

    # ---- Tool Calls ----
    if msg_type == "tool_call":
        conversation_id = data.get("conversation_id")
        tool_name = data.get("tool_name", "")
        arguments = data.get("arguments", {})

        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conv:
            _send_json(ws, {"type": "error", "message": "Conversation not found"})
            return

        agent = db.query(Agent).filter(Agent.id == conv.agent_id).first()
        if not agent:
            _send_json(ws, {"type": "error", "message": "Agent not found"})
            return

        tools_config = json.loads(agent.tools_config_json or "{}")
        api_keys = _get_api_keys()

        _send_json(ws, {
            "type": "tool_executing",
            "tool_name": tool_name,
            "arguments": arguments,
        })
        result = _execute_single_tool(tool_name, arguments, tools_config, api_keys)

        _send_json(ws, {
            "type": "tool_result",
            "tool_call_id": tool_name,
            "result": result.get("output", ""),
            "status": "success" if result.get("success") else "error",
            "error": result.get("error", ""),
        })

        # Log to TaskExecution
        exec_record = TaskExecution(
            agent_id=agent.id,
            conversation_id=conversation_id,
            task_type=f"tool_{tool_name}",
            input_json=json.dumps(arguments, ensure_ascii=False),
            output_json=json.dumps(result, ensure_ascii=False),
            status="success" if result.get("success") else "failed",
            duration_ms=result.get("duration_ms", 0),
        )
        db.add(exec_record)
        db.commit()
        return

    # ---- Plans ----
    if msg_type == "create_plan":
        conversation_id = data.get("conversation_id")
        goal = data.get("goal", "")
        context = data.get("context", "")

        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conv:
            _send_json(ws, {"type": "error", "message": "Conversation not found"})
            return
        agent = db.query(Agent).filter(Agent.id == conv.agent_id).first()
        if not agent:
            _send_json(ws, {"type": "error", "message": "Agent not found"})
            return

        try:
            api_keys = _get_api_keys()
            planner = Planner(db, api_keys)
            plan = _run_async(planner.create_plan(agent, conversation_id, goal, context or None))
            _send_json(ws, {"type": "plan_created", "plan": plan.to_dict()})

            # Optionally start PWC cycle
            orchestrator = Orchestrator(db, api_keys, plan_id=plan.id)
            _run_async(orchestrator.run_pwc_cycle())
            _send_json(ws, {"type": "plan_updated", "plan": plan.to_dict()})
        except Exception as e:
            logger.exception("Plan creation failed")
            _send_json(ws, {"type": "error", "message": f"Plan failed: {e}"})
        return

    if msg_type == "get_plans":
        conversation_id = data.get("conversation_id")
        query = db.query(Plan)
        if conversation_id:
            query = query.filter(Plan.conversation_id == conversation_id)
        plans = query.order_by(Plan.created_at.desc()).all()
        _send_json(ws, {"type": "plan_list", "plans": [p.to_dict() for p in plans]})
        return

    # ---- Group Chat ----
    if msg_type == "get_groups":
        groups = db.query(GroupConversation).order_by(GroupConversation.updated_at.desc()).all()
        result = []
        for g in groups:
            gd = g.to_dict()
            participants = db.query(GroupParticipant).filter(GroupParticipant.group_id == g.id).all()
            gd["participants"] = [p.to_dict() for p in participants]
            result.append(gd)
        _send_json(ws, {"type": "group_list", "groups": result})
        return

    if msg_type == "create_group":
        title = data.get("title", "新群聊")
        topic = data.get("topic", "")
        mode = data.get("mode", "discussion")
        participant_ids = data.get("participant_ids", [])

        group = GroupConversation(title=title, topic=topic, mode=mode, status="active")
        db.add(group)
        db.flush()

        for aid in participant_ids:
            participant = GroupParticipant(group_id=group.id, agent_id=aid)
            db.add(participant)

        db.commit()
        db.refresh(group)

        # Include participants in response
        gd = group.to_dict()
        gd["participants"] = [
            {"id": p.id, "group_id": p.group_id, "agent_id": p.agent_id, "role": p.role, "joined_at": p.joined_at.isoformat() if p.joined_at else ""}
            for p in db.query(GroupParticipant).filter(GroupParticipant.group_id == group.id).all()
        ]

        _send_json(ws, {"type": "group_created", "group": gd})
        return

    if msg_type == "group_send":
        group_id = data.get("group_id")
        content = data.get("content", "")

        group = db.query(GroupConversation).filter(GroupConversation.id == group_id).first()
        if not group:
            _send_json(ws, {"type": "error", "message": "Group not found"})
            return

        participants = db.query(GroupParticipant).filter(GroupParticipant.group_id == group_id).all()
        if not participants:
            _send_json(ws, {"type": "error", "message": "No participants in group"})
            return

        sender_id = participants[0].agent_id

        # 1. Echo user message to frontend
        _send_json(ws, {"type": "group_message", "message": {
            "group_id": group_id,
            "sender_id": sender_id,
            "content": content,
            "sender_name": "你",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }})

        # 2. Parse @mentions
        import re
        mention_pattern = re.compile(r'@(\S+)')
        mentioned_names = set(mention_pattern.findall(content))

        # 3. Each agent generates a response (only mentioned ones if @mentions present)
        api_keys = _get_api_keys()
        for p in participants:
            agent = db.query(Agent).filter(Agent.id == p.agent_id).first()
            if not agent or not agent.is_active:
                continue

            # If @mentions present, only respond if mentioned
            if mentioned_names and agent.name not in mentioned_names:
                continue

            try:
                llm = llm_client_from_agent(agent, api_keys)
                messages = [
                    {"role": "system", "content": agent.system_prompt or "你是一个有用的AI助手。"},
                    {"role": "user", "content": f"[群聊: {group.title}]\n用户说: {content}\n请以{agent.name}的身份回复。"},
                ]

                response = ""
                for chunk in llm.stream_sync(messages):
                    response += chunk

                _send_json(ws, {"type": "group_message", "message": {
                    "group_id": group_id,
                    "sender_id": agent.id,
                    "content": response.strip() or f"[{agent.name}: 无响应]",
                    "sender_name": agent.name,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }})
            except Exception as e:
                logger.exception(f"Agent {agent.name} response failed")
                _send_json(ws, {"type": "group_message", "message": {
                    "group_id": group_id,
                    "sender_id": agent.id,
                    "content": f"[{agent.name} 回复失败: {e}]",
                    "sender_name": agent.name,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }})
        return

    # ---- Memory Query ----
    if msg_type == "memory_query":
        agent_id = data.get("agent_id")
        query_text = data.get("query", "")
        k = data.get("k", 5)

        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            _send_json(ws, {"type": "error", "message": "Agent not found"})
            return

        try:
            api_keys = _get_api_keys()
            vm = VectorMemory(api_key=api_keys.get("openai", ""))
            results = _run_async(vm.search(agent_id=agent_id, query=query_text, k=k))
            _send_json(ws, {"type": "memory_result", "results": results})
        except Exception as e:
            logger.warning(f"Vector memory query failed, falling back to L2: {e}")
            summaries = (
                db.query(Agent)
                .filter(Agent.id == agent_id)
                .first()
            )
            _send_json(ws, {"type": "memory_result", "results": []})
        return

    # ---- Message Operations ----
    if msg_type == "edit_message":
        message_id = data.get("message_id")
        new_content = data.get("content", "")

        msg = db.query(Message).filter(Message.id == message_id).first()
        if not msg:
            _send_json(ws, {"type": "error", "message": "Message not found"})
            return

        old_content = msg.content
        msg.content = new_content
        msg.is_edited = True
        msg.edited_from = old_content[:100]
        msg.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(msg)
        _send_json(ws, {"type": "message_edited", "message": msg.to_dict()})
        return

    if msg_type == "recall_message":
        message_id = data.get("message_id")
        msg = db.query(Message).filter(Message.id == message_id).first()
        if not msg:
            _send_json(ws, {"type": "error", "message": "Message not found"})
            return

        msg.content = "[消息已撤回]"
        msg.status = "cancelled"
        msg.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(msg)
        _send_json(ws, {"type": "message_recalled", "message": msg.to_dict()})
        return

    if msg_type == "reference_message":
        conversation_id = data.get("conversation_id")
        message_id = data.get("message_id")
        ref_content = data.get("content", "")

        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conv:
            _send_json(ws, {"type": "error", "message": "Conversation not found"})
            return

        # Create a new message that references the original
        ref_msg = Message(
            conversation_id=conversation_id,
            role="user",
            content=ref_content,
            reply_to=message_id,
        )
        db.add(ref_msg)
        db.commit()
        db.refresh(ref_msg)
        _send_json(ws, {"type": "new_message", "message": ref_msg.to_dict()})
        return

    if msg_type == "get_history":
        conversation_id = data.get("conversation_id")
        query = db.query(TaskExecution)
        if conversation_id:
            query = query.filter(TaskExecution.conversation_id == conversation_id)
        records = query.order_by(TaskExecution.created_at.desc()).limit(100).all()
        _send_json(ws, {"type": "history_list", "records": [r.to_dict() for r in records]})
        return

    # ---- Unknown ----
    _send_json(ws, {"type": "error", "message": f"Unknown message type: {msg_type}"})


def handle_websocket(ws):
    """Main WebSocket loop — receive → parse → dispatch."""
    db: Session = SessionLocal()
    try:
        while True:
            raw = ws.receive()
            if raw is None:
                break
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as e:
                _send_json(ws, {"type": "error", "message": f"Invalid JSON: {e}"})
                continue

            try:
                handle_message(ws, data, db)
            except Exception as e:
                logger.exception("Handler error")
                _send_json(ws, {"type": "error", "message": str(e)})
    finally:
        db.close()
