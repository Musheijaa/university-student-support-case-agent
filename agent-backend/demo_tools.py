"""Tool Demonstration Script for Week 4 Evaluation & Presentation.

Run this script to demonstrate that all registered tools work as expected across:
1. Tool Discovery & JSON Schema generation
2. Happy-path tool executions (Ticket Creation, Case Status Lookup, Timetable Query)
3. Input validation failure handling
4. Authorization & permission failure handling
5. Non-existent resource & edge case handling

Usage:
    python demo_tools.py
"""

import json
from tools import TicketCategory, TicketPriority, get_tool_registry


def print_section(title: str) -> None:
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_result(label: str, result: dict) -> None:
    print(f"\n---> [Scenario]: {label}")
    print(json.dumps(result, indent=2))


def main() -> None:
    print_section("WEEK 4 TOOLS DEMONSTRATION & VERIFICATION")
    registry = get_tool_registry()

    # -----------------------------------------------------------------------
    # Step 1: Tool Discovery and Cataloging
    # -----------------------------------------------------------------------
    print_section("1. TOOL CATALOGUE & JSON SCHEMA EXPORT")
    tools = registry.list_tools()
    print(f"Registered Tools Count: {len(tools)}")
    for t in tools:
        print(f" - {t.name}: {t.tool_purpose}")

    schemas = registry.get_all_json_schemas()
    print("\nSample LLM Function Schema Export (create_support_ticket):")
    print(json.dumps(schemas[0], indent=2))

    # -----------------------------------------------------------------------
    # Step 2: Tool 1 - create_support_ticket Scenarios
    # -----------------------------------------------------------------------
    print_section("2. TOOL 1: create_support_ticket DEMONSTRATIONS")

    # Happy Path
    res1 = registry.execute_tool(
        "create_support_ticket",
        {
            "student_id": "2100701234",
            "category": TicketCategory.ACADEMIC_REGISTRAR.value,
            "subject": "Missing Exam Grade for BSE4104",
            "description": "I sat for the BSE4104 final examination but my grade is missing on the portal.",
            "priority": TicketPriority.HIGH.value,
            "auth_token": "valid-student-token-123",
        },
    )
    print_result("Happy Path (Ticket Created)", res1.model_dump())
    created_ticket_id = res1.ticket_id

    # Validation Failure
    res2 = registry.execute_tool(
        "create_support_ticket",
        {
            "student_id": "   ",  # Invalid blank student ID
            "category": TicketCategory.IT_SUPPORT.value,
            "subject": "Short",  # Too short (min 5 chars)
            "description": "Short",  # Too short (min 10 chars)
            "auth_token": "valid-token",
        },
    )
    print_result("Validation Failure (Missing / Invalid Input)", res2.model_dump())

    # Authorization Failure
    res3 = registry.execute_tool(
        "create_support_ticket",
        {
            "student_id": "2100701234",
            "category": TicketCategory.FINANCIAL_AID.value,
            "subject": "Tuition Verification Issue",
            "description": "Tuition receipt has not cleared on student portal.",
            "auth_token": "unauthorized",  # Forbidden token
        },
    )
    print_result("Authorization Failure (Invalid Token)", res3.model_dump())

    # -----------------------------------------------------------------------
    # Step 3: Tool 2 - get_case_status Scenarios
    # -----------------------------------------------------------------------
    print_section("3. TOOL 2: get_case_status DEMONSTRATIONS")

    # Happy Path (Query newly created ticket)
    if created_ticket_id:
        res4 = registry.execute_tool(
            "get_case_status",
            {
                "case_id": created_ticket_id,
                "student_id": "2100701234",
                "auth_token": "valid-student-token",
            },
        )
        print_result(f"Happy Path (Lookup Created Ticket '{created_ticket_id}')", res4.model_dump())

    # Case Not Found
    res5 = registry.execute_tool(
        "get_case_status",
        {
            "case_id": "TICK-2026-9999",  # Non-existent
            "student_id": "2100701234",
            "auth_token": "valid-token",
        },
    )
    print_result("Resource Not Found (Non-existent Case ID)", res5.model_dump())

    # Ownership Mismatch Authorization Failure
    res6 = registry.execute_tool(
        "get_case_status",
        {
            "case_id": "TICK-2026-1001",  # Belongs to student 2100701234
            "student_id": "2100709999",  # Student ID mismatch
            "auth_token": "student-token-9999",
        },
    )
    print_result("Authorization Failure (Student ID Ownership Mismatch)", res6.model_dump())

    # -----------------------------------------------------------------------
    # Step 4: Tool 3 - check_timetable Scenarios
    # -----------------------------------------------------------------------
    print_section("4. TOOL 3: check_timetable DEMONSTRATIONS")

    # Happy Path (Found Schedule)
    res7 = registry.execute_tool(
        "check_timetable",
        {
            "student_id": "2100701234",
            "course_code": "BSE4104",
            "semester": "2026/2027-SEM1",
            "auth_token": "valid-token",
        },
    )
    print_result("Happy Path (Found Schedule for BSE4104)", res7.model_dump())

    # Empty Schedule Found (Clean handling without error)
    res8 = registry.execute_tool(
        "check_timetable",
        {
            "student_id": "2100701234",
            "course_code": "UNKNOWN999",
            "semester": "2026/2027-SEM1",
            "auth_token": "valid-token",
        },
    )
    print_result("Empty Schedule Handling (Unknown Course Code)", res8.model_dump())

    # -----------------------------------------------------------------------
    # Step 5: Human-in-the-Loop (HITL) Approval & High-Impact Tool
    # -----------------------------------------------------------------------
    print_section("5. HUMAN-IN-THE-LOOP (HITL) APPROVAL STATE WORKFLOW")
    from tools import ApprovalDecision, get_approval_manager

    mgr = get_approval_manager()

    appeal_params = {
        "student_id": "2100701234",
        "course_code": "BSE4104",
        "semester": "2026/2027-SEM1",
        "appeal_type": "REMARKING",
        "claimed_score": 78.5,
        "justification": "Marks calculated incorrectly on Question 3 during final exam compilation.",
        "confirm_fee_obligation": True,
        "auth_token": "valid-student-token",
    }

    # Step A: Propose high-impact action -> Execution pauses
    print("\n[AI Agent attempts high-impact action 'submit_grade_appeal'...]")
    approval_req = mgr.request_approval(
        tool_name="submit_grade_appeal",
        parameters=appeal_params,
        requester="2100701234",
        action_summary="Submit academic grade appeal with 50,000 UGX fee charge to Senate Committee.",
        risk_level="HIGH",
    )
    print_result("Execution Paused (Approval Request Created)", approval_req.model_dump())

    # Step B: Human Approves -> Tool FIRES
    print(f"\n[Prompting Human Reviewer for decision on {approval_req.approval_id}...]")
    approval_outcome = mgr.decide_approval(
        approval_id=approval_req.approval_id,
        decision=ApprovalDecision.APPROVE,
        reviewer="Faculty Academic Advisor (Dr. Grace)",
        notes="Reviewed student grounds and confirmed student fee deposit agreement.",
    )
    print_result("Human Decision = APPROVE -> Target Tool Fired!", approval_outcome.model_dump())

    # Step C: Demonstrating Rejection -> Tool is BLOCKED from firing
    print("\n[Demonstrating Rejection Scenario...]")
    rejected_req = mgr.request_approval(
        tool_name="submit_grade_appeal",
        parameters=appeal_params,
        requester="2100701234",
        action_summary="Submit unverified grade appeal.",
        risk_level="HIGH",
    )
    rejection_outcome = mgr.decide_approval(
        approval_id=rejected_req.approval_id,
        decision=ApprovalDecision.REJECT,
        reviewer="Department Head",
        notes="No preliminary consultation with examiner; appeal grounds dismissed.",
    )
    print_result("Human Decision = REJECT -> Tool Blocked (Never Fired)", rejection_outcome.model_dump())

    print_section("DEMONSTRATION COMPLETED SUCCESSFULLY")


if __name__ == "__main__":
    main()

