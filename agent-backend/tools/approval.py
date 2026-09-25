"""Human-in-the-Loop (HITL) Approval State Manager.

Builds application state logic that:
1. Pauses execution when high-impact actions are proposed.
2. Prompts user/human operator with clear action summaries and parameter details.
3. Only triggers/fires the target tool once human approval is explicitly confirmed.
4. Safely cancels execution if rejected, recording full audit rationale.
"""

from datetime import datetime, timezone
import random
from typing import Any

from tools.registry import get_tool_registry
from tools.schemas import (
    ApprovalDecision,
    ApprovalExecutionResult,
    ApprovalRequest,
    ApprovalStatus,
)


class ApprovalManager:
    """State manager for human approval workflows."""

    def __init__(self) -> None:
        self._approvals: dict[str, ApprovalRequest] = {}

    def request_approval(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        requester: str,
        action_summary: str,
        risk_level: str = "HIGH",
    ) -> ApprovalRequest:
        """Create an approval request and pause execution.

        Tool is NOT executed at this point.
        """
        registry = get_tool_registry()
        tool = registry.get_tool(tool_name)
        if not tool:
            raise KeyError(f"Target tool '{tool_name}' not registered in tool registry.")

        random_id = random.randint(1000, 9999)
        approval_id = f"APPR-2026-{random_id}"
        now_iso = datetime.now(timezone.utc).isoformat()

        req = ApprovalRequest(
            approval_id=approval_id,
            tool_name=tool_name,
            action_summary=action_summary,
            parameters=parameters,
            requester=requester,
            risk_level=risk_level,
            status=ApprovalStatus.PENDING,
            created_at=now_iso,
            decided_at=None,
            reviewer=None,
            review_notes=None,
            execution_result=None,
        )
        self._approvals[approval_id] = req
        return req

    def get_approval(self, approval_id: str) -> ApprovalRequest | None:
        """Lookup an approval record by ID."""
        return self._approvals.get(approval_id)

    def get_pending_approvals(self) -> list[ApprovalRequest]:
        """Return all approvals currently waiting for human decision."""
        return [
            req
            for req in self._approvals.values()
            if req.status == ApprovalStatus.PENDING
        ]

    def decide_approval(
        self,
        approval_id: str,
        decision: ApprovalDecision,
        reviewer: str,
        notes: str,
    ) -> ApprovalExecutionResult:
        """Process human decision.

        If APPROVE: fires the target tool and records execution output.
        If REJECT: cancels execution, tool is never triggered.
        """
        req = self.get_approval(approval_id)
        if not req:
            raise KeyError(f"Approval request '{approval_id}' not found.")

        if req.status != ApprovalStatus.PENDING:
            return ApprovalExecutionResult(
                approval_id=approval_id,
                status=req.status,
                tool_fired=False,
                tool_output=req.execution_result,
                message=f"Approval request '{approval_id}' is already {req.status.value}.",
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        req.reviewer = reviewer
        req.review_notes = notes
        req.decided_at = now_iso

        if decision == ApprovalDecision.APPROVE:
            # Human approved -> Fire target tool now
            registry = get_tool_registry()
            tool_result = registry.execute_tool(req.tool_name, req.parameters)
            tool_output_dict = (
                tool_result.model_dump()
                if hasattr(tool_result, "model_dump")
                else dict(tool_result)
            )

            req.status = ApprovalStatus.APPROVED
            req.execution_result = tool_output_dict

            return ApprovalExecutionResult(
                approval_id=approval_id,
                status=ApprovalStatus.APPROVED,
                tool_fired=True,
                tool_output=tool_output_dict,
                message=(
                    f"Human approval confirmed by {reviewer}. "
                    f"Tool '{req.tool_name}' successfully executed."
                ),
            )
        else:
            # Human rejected -> Do not fire tool
            req.status = ApprovalStatus.REJECTED
            req.execution_result = None

            return ApprovalExecutionResult(
                approval_id=approval_id,
                status=ApprovalStatus.REJECTED,
                tool_fired=False,
                tool_output=None,
                message=(
                    f"Action rejected by {reviewer}. "
                    f"Tool '{req.tool_name}' was NOT executed. Reason: {notes}"
                ),
            )


# Global singleton instance
_approval_manager_instance = ApprovalManager()


def get_approval_manager() -> ApprovalManager:
    return _approval_manager_instance
