"""
Human-in-the-loop Approval Manager.

Provides approval checkpoints at critical decision points:
- Tool execution (dangerous tools like CLI, UI automation)
- Plan approval (before executing a plan)
- Final result review (before considering task complete)
- Dangerous action in dialogues
"""
import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session

from app.models import ApprovalRecord

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 数据类
# ---------------------------------------------------------------------------

@dataclass
class ApprovalConfig:
    """Approval behavior configuration."""
    default_timeout: float = 60.0  # seconds
    require_tool_approval: bool = True
    require_plan_approval: bool = True
    require_final_approval: bool = True
    dangerous_tools: list[str] = field(default_factory=lambda: ["cli", "ui_automation"])


@dataclass
class ApprovalRequest:
    """An in-flight approval request."""
    id: str = ""
    type: str = ""  # tool_execution / plan_approval / final_result / dangerous_action
    context: dict = field(default_factory=dict)
    requester: str = ""  # agent_id or 'system'
    status: str = "pending"  # pending / approved / rejected / modified / timeout
    created_at: float = 0.0
    timeout_at: float = 0.0
    user_response: Optional[dict] = None

    def to_dict(self) -> dict:
        return {
            "request_id": self.id,
            "type": self.type,
            "context": self.context,
            "requester": self.requester,
            "timeout_seconds": max(0, int(self.timeout_at - time.time())),
            "status": self.status,
        }


# ---------------------------------------------------------------------------
# 审批管理器
# ---------------------------------------------------------------------------

class ApprovalManager:
    """
    Human-in-the-loop approval manager.

    Usage:
        mgr = ApprovalManager(db, ws_callback)
        result = await mgr.request_approval(
            type="tool_execution",
            context={"tool_name": "cli", "command": "ls"},
        )
        if result.status == "approved":
            # proceed
    """

    def __init__(
        self,
        db: Session,
        ws_send_callback: Optional[Callable[[dict], None]] = None,
        config: Optional[ApprovalConfig] = None,
    ):
        self.db = db
        self._ws_callback = ws_send_callback
        self.config = config or ApprovalConfig()
        self._pending: dict[str, ApprovalRequest] = {}
        self._events: dict[str, asyncio.Event] = {}
        self._results: dict[str, ApprovalRequest] = {}

    def set_ws_callback(self, callback: Callable[[dict], None]):
        """Set the callback for sending approval requests to the frontend."""
        self._ws_callback = callback

    async def request_approval(
        self,
        approval_type: str,
        context: dict,
        timeout: Optional[float] = None,
    ) -> ApprovalRequest:
        """
        Send an approval request to the frontend and wait for response.

        Returns the resolved ApprovalRequest (approved/rejected/modified/timeout).
        """
        timeout_sec = timeout if timeout is not None else self.config.default_timeout
        now = time.time()

        req = ApprovalRequest(
            id=self._gen_id(),
            type=approval_type,
            context=context,
            requester=context.get("agent_id", "system"),
            created_at=now,
            timeout_at=now + timeout_sec,
        )

        self._pending[req.id] = req
        self._events[req.id] = asyncio.Event()

        # Send to frontend
        if self._ws_callback:
            try:
                self._ws_callback({
                    "type": "approval_request",
                    "request_id": req.id,
                    "approval_type": req.type,
                    "context": req.context,
                    "requester": req.requester,
                    "timeout_seconds": timeout_sec,
                    "dangerous": req.type in ("tool_execution", "dangerous_action"),
                })
            except Exception as e:
                logger.error("Failed to send approval request: %s", e)

        # Wait for response or timeout
        try:
            await asyncio.wait_for(
                self._events[req.id].wait(),
                timeout=timeout_sec,
            )
            # Event was set by submit_response
            resolved = self._results.pop(req.id, req)
        except asyncio.TimeoutError:
            # Timeout — auto-reject
            logger.warning("Approval %s timed out after %ss", req.id, timeout_sec)
            req.status = "timeout"
            req.user_response = {"response": "timeout", "feedback": "审批超时，自动拒绝"}
            resolved = req

            if self._ws_callback:
                self._ws_callback({
                    "type": "approval_timeout",
                    "request_id": req.id,
                    "approval_type": req.type,
                })

        # Cleanup
        self._pending.pop(req.id, None)
        self._events.pop(req.id, None)

        # Record to DB
        self._record_approval(resolved)

        return resolved

    def submit_response(
        self,
        request_id: str,
        response: str,
        feedback: str = "",
        modified_params: Optional[dict] = None,
    ) -> bool:
        """
        Called by ws_handler when the frontend responds to an approval request.

        response: 'approved' | 'rejected' | 'modified'
        """
        req = self._pending.get(request_id)
        if not req:
            logger.warning("Unknown approval request: %s", request_id)
            return False

        req.status = response
        req.user_response = {
            "response": response,
            "feedback": feedback,
            "modified_params": modified_params or {},
        }
        self._results[request_id] = req

        # Wake the waiting coroutine
        event = self._events.get(request_id)
        if event:
            event.set()

        logger.info("Approval %s resolved: %s (by user)", request_id, response)
        return True

    def cancel_pending(self, reason: str = "session ended"):
        """Cancel all pending approvals (e.g., on disconnect)."""
        for req_id, req in list(self._pending.items()):
            req.status = "timeout"
            req.user_response = {"response": "timeout", "feedback": reason}
            self._results[req_id] = req
            event = self._events.get(req_id)
            if event:
                event.set()
            self._pending.pop(req_id, None)
            self._events.pop(req_id, None)

    def is_dangerous_tool(self, tool_name: str) -> bool:
        """Check if a tool requires approval."""
        return tool_name in self.config.dangerous_tools

    def should_approve_tool(self, tool_name: str) -> bool:
        """Check if this tool requires human approval before execution."""
        return self.config.require_tool_approval and self.is_dangerous_tool(tool_name)

    def should_approve_plan(self) -> bool:
        """Check if plan approval is required."""
        return self.config.require_plan_approval

    def should_approve_final(self) -> bool:
        """Check if final result approval is required."""
        return self.config.require_final_approval

    def _record_approval(self, req: ApprovalRequest):
        """Persist the approval result to the database."""
        try:
            record = ApprovalRecord(
                request_id=req.id,
                approval_type=req.type,
                requester=req.requester,
                context_json=json.dumps(req.context, ensure_ascii=False),
                response=req.status,
                user_feedback=req.user_response.get("feedback", "") if req.user_response else "",
                modified_params_json=json.dumps(
                    req.user_response.get("modified_params", {}) if req.user_response else {},
                    ensure_ascii=False,
                ),
                timeout_seconds=int(req.timeout_at - req.created_at) if req.created_at else 60,
                responded_at=datetime.now(timezone.utc) if req.status != "pending" else None,
            )
            self.db.add(record)
            self.db.commit()
        except Exception as e:
            logger.error("Failed to record approval: %s", e)
            self.db.rollback()

    @staticmethod
    def _gen_id() -> str:
        return str(uuid.uuid4())
