"""Tests for Human-in-the-Loop (HITL) approval state logic and SubmitGradeAppealTool."""

from fastapi.testclient import TestClient
import pytest

from main import app
from tools import (
    AppealType,
    ApprovalDecision,
    ApprovalDecisionInput,
    ApprovalStatus,
    SubmitGradeAppealInput,
    SubmitGradeAppealOutput,
    SubmitGradeAppealTool,
    get_approval_manager,
    get_tool_registry,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Tool 4: SubmitGradeAppealTool Unit Tests
# ---------------------------------------------------------------------------
def test_submit_grade_appeal_tool_success() -> None:
    tool = SubmitGradeAppealTool()
    raw_input = {
        "student_id": "2100701234",
        "course_code": "BSE4104",
        "semester": "2026/2027-SEM1",
        "appeal_type": AppealType.REMARKING.value,
        "claimed_score": 75.0,
        "justification": "Examination paper question 4 marking scheme was omitted in score tally.",
        "confirm_fee_obligation": True,
        "auth_token": "valid-student-token",
    }
    result = tool.execute(raw_input)

    assert isinstance(result, SubmitGradeAppealOutput)
    assert result.success is True
    assert result.status == "LODGED"
    assert result.appeal_id is not None
    assert result.appeal_id.startswith("APPL-2026-")
    assert result.appeal_fee_ugx == 50000
    assert result.course_code == "BSE4104"
    assert result.error is None


def test_submit_grade_appeal_missing_fee_confirmation() -> None:
    tool = SubmitGradeAppealTool()
    raw_input = {
        "student_id": "2100701234",
        "course_code": "BSE4104",
        "justification": "Valid grounds for remarking but fee refused.",
        "confirm_fee_obligation": False,  # Refused fee
        "auth_token": "valid-token",
    }
    result = tool.execute(raw_input)

    assert result.success is False
    assert result.status == "INVALID_INPUT"
    assert "fee obligation" in result.error


def test_submit_grade_appeal_unauthorized() -> None:
    tool = SubmitGradeAppealTool()
    raw_input = {
        "student_id": "2100701234",
        "course_code": "BSE4104",
        "justification": "Valid grounds for remarking justification text.",
        "confirm_fee_obligation": True,
        "auth_token": "unauthorized",
    }
    result = tool.execute(raw_input)

    assert result.success is False
    assert result.status == "UNAUTHORIZED"
    assert "AUTH_DENIED" in result.error


# ---------------------------------------------------------------------------
# Human-in-the-Loop State Logic Tests
# ---------------------------------------------------------------------------
def test_approval_manager_pause_and_approve_fires_tool() -> None:
    mgr = get_approval_manager()
    params = {
        "student_id": "2100701234",
        "course_code": "BSE4104",
        "semester": "2026/2027-SEM1",
        "appeal_type": AppealType.REMARKING.value,
        "justification": "Requesting remarking for BSE4104 final examination script.",
        "confirm_fee_obligation": True,
        "auth_token": "valid-student-token",
    }

    # Step 1: Request approval -> Pauses execution
    req = mgr.request_approval(
        tool_name="submit_grade_appeal",
        parameters=params,
        requester="2100701234",
        action_summary="Submit academic grade appeal with 50,000 UGX fee charge.",
    )

    assert req.status == ApprovalStatus.PENDING
    assert req.execution_result is None
    assert req in mgr.get_pending_approvals()

    # Step 2: Human approves -> Tool is fired
    result = mgr.decide_approval(
        approval_id=req.approval_id,
        decision=ApprovalDecision.APPROVE,
        reviewer="Academic Advisor Dr. Grace",
        notes="Verified grounds and student fee acknowledgment.",
    )

    assert result.status == ApprovalStatus.APPROVED
    assert result.tool_fired is True
    assert result.tool_output is not None
    assert result.tool_output["success"] is True
    assert result.tool_output["status"] == "LODGED"
    assert "successfully executed" in result.message


def test_approval_manager_reject_prevents_tool_firing() -> None:
    mgr = get_approval_manager()
    params = {
        "student_id": "2100701234",
        "course_code": "BSE4104",
        "justification": "Requesting appeal without valid grounds or evidence.",
        "confirm_fee_obligation": True,
        "auth_token": "valid-student-token",
    }

    # Step 1: Request approval -> Pauses execution
    req = mgr.request_approval(
        tool_name="submit_grade_appeal",
        parameters=params,
        requester="2100701234",
        action_summary="Submit academic grade appeal.",
    )

    # Step 2: Human rejects -> Tool is NOT fired
    result = mgr.decide_approval(
        approval_id=req.approval_id,
        decision=ApprovalDecision.REJECT,
        reviewer="Department Chair",
        notes="Grounds insufficient; please consult course coordinator first.",
    )

    assert result.status == ApprovalStatus.REJECTED
    assert result.tool_fired is False
    assert result.tool_output is None
    assert "was NOT executed" in result.message


# ---------------------------------------------------------------------------
# API Endpoints Integration Tests
# ---------------------------------------------------------------------------
def test_api_execute_high_impact_tool_pauses_for_approval() -> None:
    payload = {
        "tool_name": "submit_grade_appeal",
        "parameters": {
            "student_id": "2100701234",
            "course_code": "BSE4104",
            "semester": "2026/2027-SEM1",
            "appeal_type": "REMARKING",
            "justification": "Marks calculated incorrectly during final compilation.",
            "confirm_fee_obligation": True,
            "auth_token": "valid-token",
        },
    }
    # Direct execution should pause and prompt for human approval
    res = client.post("/api/v1/tools/execute", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "PAUSED_PENDING_APPROVAL"
    assert "approval_id" in data
    approval_id = data["approval_id"]

    # Now decide approval via API
    decide_res = client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={
            "decision": "APPROVE",
            "reviewer": "Dean of Faculty",
            "notes": "Approved for senate review.",
        },
    )
    assert decide_res.status_code == 200
    decide_data = decide_res.json()
    assert decide_data["status"] == "APPROVED"
    assert decide_data["tool_fired"] is True
    assert decide_data["tool_output"]["status"] == "LODGED"
