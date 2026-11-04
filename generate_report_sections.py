import os
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_shading(cell, color_hex):
    shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
    cell._tc.get_or_add_tcPr().append(shading_elm)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('w:top', top), ('w:bottom', bottom), ('w:left', left), ('w:right', right)]:
        node = OxmlElement(m)
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def set_table_borders(table, color="D3D3D3", sz="4", val="single"):
    tblPr = table._tbl.tblPr
    borders = parse_xml(f'''
        <w:tblBorders {nsdecls("w")}>
            <w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>
            <w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>
            <w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>
            <w:insideV w:val="none"/>
            <w:left w:val="none"/>
            <w:right w:val="none"/>
        </w:tblBorders>
    ''')
    tblPr.append(borders)

def add_callout(doc, text, title="KEY HIGHLIGHT"):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0)
    set_cell_shading(cell, "F0F4F8")
    set_cell_margins(cell, top=140, bottom=140, left=200, right=200)
    
    # Left border highlight
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = parse_xml(f'''
        <w:tcBorders {nsdecls("w")}>
            <w:top w:val="none"/>
            <w:left w:val="single" w:sz="24" w:space="0" w:color="1F4E79"/>
            <w:bottom w:val="none"/>
            <w:right w:val="none"/>
        </w:tcBorders>
    ''')
    tcPr.append(tcBorders)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.15
    run_t = p.add_run(f"{title}: ")
    run_t.bold = True
    run_t.font.name = "Calibri"
    run_t.font.size = Pt(10)
    run_t.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)
    
    run_body = p.add_run(text)
    run_body.font.name = "Calibri"
    run_body.font.size = Pt(10)
    run_body.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
    
    # Empty space after table
    sp = doc.add_paragraph()
    sp.paragraph_format.space_before = Pt(0)
    sp.paragraph_format.space_after = Pt(6)

def build_report_docx(output_path):
    doc = Document()
    
    # Page setup: Margins 1 inch
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)
        section.different_first_page_header_footer = False
        
        # Header / Footer
        header = section.header
        hp = header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hrun = hp.add_run("UniSupport AI — Capstone Project Report (Sections 1, 2, 10)")
        hrun.font.name = "Calibri"
        hrun.font.size = Pt(8.5)
        hrun.font.color.rgb = RGBColor(0x88, 0x88, 0x88)
        
        footer = section.footer
        fp = footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        frun = fp.add_run("Makerere University | BSE4104: Emerging Trends in Software Engineering | Group L")
        frun.font.name = "Calibri"
        frun.font.size = Pt(8.5)
        frun.font.color.rgb = RGBColor(0x88, 0x88, 0x88)

    # Styles setup
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Calibri'
    normal_style.font.size = Pt(11)
    normal_style.font.color.rgb = RGBColor(0x26, 0x26, 0x26)

    # Document Header / Title
    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(0)
    title_p.paragraph_format.space_after = Pt(4)
    run_title = title_p.add_run("UniSupport AI: A Bounded Agentic University Student-Support Case System")
    run_title.font.name = "Calibri"
    run_title.font.size = Pt(20)
    run_title.bold = True
    run_title.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79) # Navy

    sub_p = doc.add_paragraph()
    sub_p.paragraph_format.space_before = Pt(0)
    sub_p.paragraph_format.space_after = Pt(14)
    run_sub = sub_p.add_run("Capstone Project Report Deliverable — Sections 1, 2, and 10\n"
                            "Course: BSE4104: Emerging Trends in Software Engineering | Makerere University (CoCIS / SCIT)\n"
                            "Group L: Musheija Abraham, Okema Paul Mark, Akakikunda Benitah, Kizito Ryan, Mwesigwa Sean")
    run_sub.font.name = "Calibri"
    run_sub.font.size = Pt(10)
    run_sub.font.italic = True
    run_sub.font.color.rgb = RGBColor(0x59, 0x59, 0x59)

    # Divider line
    div_p = doc.add_paragraph()
    div_p.paragraph_format.space_before = Pt(0)
    div_p.paragraph_format.space_after = Pt(16)
    pBdr = parse_xml(f'<w:pBdr {nsdecls("w")}><w:bottom w:val="single" w:sz="12" w:space="1" w:color="1F4E79"/></w:pBdr>')
    div_p._p.get_or_add_pPr().append(pBdr)

    # =========================================================================
    # SECTION 1: EXECUTIVE SUMMARY
    # =========================================================================
    h1 = doc.add_paragraph()
    h1.paragraph_format.space_before = Pt(14)
    h1.paragraph_format.space_after = Pt(6)
    r1 = h1.add_run("1. Executive Summary")
    r1.font.name = "Calibri"
    r1.font.size = Pt(15)
    r1.bold = True
    r1.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)

    p_exec = doc.add_paragraph()
    p_exec.paragraph_format.line_spacing = 1.15
    p_exec.paragraph_format.space_after = Pt(8)
    p_exec.add_run(
        "University students at Makerere University routinely experience severe administrative friction when navigating fragmented, "
        "opaque academic support procedures. Critical information regarding examination regulations, retake policies, course registration, "
        "and departmental procedures is scattered across static physical noticeboards, multi-page PDF handbooks, and siloed administrative desks. "
        "When students encounter routine administrative bottlenecks—such as portal access lockouts or timetable clashes—they are forced to pursue "
        "informal, untracked channels (in-person visits or unacknowledged emails). These inquiries lack unique tracking identifiers, leave students "
        "without visibility into case resolution, and overwhelm university support staff with repetitive administrative queries."
    )

    p_exec2 = doc.add_paragraph()
    p_exec2.paragraph_format.line_spacing = 1.15
    p_exec2.paragraph_format.space_after = Pt(8)
    p_exec2.add_run(
        "To address this challenge, UniSupport AI was developed as a bounded, AI-native student-support case agent serving two primary user groups: "
        "(1) undergraduate students seeking prompt, grounded procedural answers and structured case tracking, and (2) departmental support staff "
        "requiring auditable, pre-triaged support requests. The system deliberately diverges from open-ended conversational bots by coupling a fast "
        "foundation model (Groq openai/gpt-oss-20b) with a deterministic software scaffold. The architecture coordinates semantic Retrieval-Augmented "
        "Generation (RAG) over 12 verified Makerere University policy documents, explicit tool dispatch (synthetic timetable lookup and support ticket drafting), "
        "a 6-stage cognitive loop (Sense → Context → Plan → Act → Observe → Stop), and bounded per-session memory."
    )

    p_exec3 = doc.add_paragraph()
    p_exec3.paragraph_format.line_spacing = 1.15
    p_exec3.paragraph_format.space_after = Pt(8)
    p_exec3.add_run(
        "Empirical evaluation demonstrates robust performance: across a rigorous 39-scenario benchmark spanning normal, edge, incorrect information, "
        "adversarial injection, tool failure, and unauthorized execution categories, the system achieved a 100% pass rate (39/39 passing, integrated within "
        "a 178-test automated suite). Policy responses achieved zero citation fabrication by generating source metadata strictly from deterministic "
        "vector-store records. Crucially, code-level guardrails proved completely resilient against prompt injection, privilege escalation, and loop exhaustion. "
        "The system's principal limitation is its deployment as an academic prototype operating on synthetic timetable/ticket databases and simulated header-based "
        "roles (X-User-Role), without live integration into Makerere's enterprise Academic Information Management System (AIMS). Furthermore, high-consequence "
        "academic decisions (grades, fees, disciplinary hearings, and admissions) are strictly blocked from autonomous resolution and mandate human escalation."
    )

    add_callout(
        doc,
        "UniSupport AI enforces an unyielding architectural boundary: the foundation model provides cognitive synthesis, natural language triage, "
        "and evidence explanation, while deterministic code enforces authorization, tool registries, execution budgets, and an immutable Human-in-the-Loop "
        "gate for ticket approval.",
        title="EXECUTIVE ARCHITECTURAL PRINCIPLE"
    )

    # =========================================================================
    # SECTION 2: PROBLEM CONTEXT AND REQUIREMENTS
    # =========================================================================
    h2 = doc.add_paragraph()
    h2.paragraph_format.space_before = Pt(18)
    h2.paragraph_format.space_after = Pt(6)
    r2 = h2.add_run("2. Problem Context and Requirements")
    r2.font.name = "Calibri"
    r2.font.size = Pt(15)
    r2.bold = True
    r2.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)

    h2_1 = doc.add_paragraph()
    h2_1.paragraph_format.space_before = Pt(8)
    h2_1.paragraph_format.space_after = Pt(4)
    r2_1 = h2_1.add_run("2.1 Problem Context and Primary End-to-End Workflow")
    r2_1.font.name = "Calibri"
    r2_1.font.size = Pt(12.5)
    r2_1.bold = True
    r2_1.font.color.rgb = RGBColor(0x2E, 0x75, 0xB6)

    p_wf = doc.add_paragraph()
    p_wf.paragraph_format.line_spacing = 1.15
    p_wf.paragraph_format.space_after = Pt(6)
    p_wf.add_run(
        "University academic support at Makerere involves high-volume, multi-channel interactions where students require timely guidance on deadlines, "
        "examination rules, and course logistics. Traditional institutional workflows suffer from three systemic points of failure: (a) students struggle "
        "to extract definitive answers from dense, multi-page PDFs; (b) informal grievance reporting produces untracked cases with zero accountability; and "
        "(c) students must repetitively re-explain issues across visits because institutional desks lack session memory. "
        "UniSupport AI replaces this friction with an auditable, multi-stage primary workflow:"
    )

    wf_steps = [
        ("Step 1 (Sense & Validate): ", "The student submits a natural language message. The application's API gateway parses the payload, enforces Pydantic bounds (1–2,000 characters, non-empty), and extracts the actor's role from trusted headers (X-User-Role)."),
        ("Step 2 (Context Retrieval & Planning): ", "The system semantically queries the ChromaDB policy store to retrieve top-k evidence chunks (filtered at a minimum cosine similarity of 0.35). An initial cognitive budget (AGENT_MAX_ITERATIONS=4, MAX_TOOL_CALLS=3) is allocated."),
        ("Step 3 (Cognitive Deliberation): ", "The foundation model evaluates the student inquiry alongside retrieved policy evidence and prior session context to decide the next step: formulate an answer, inspect schedules via check_timetable, or draft a ticket via create_support_ticket."),
        ("Step 4 (Deterministic Action & Guardrail Gate): ", "If a tool is requested, the application validates the tool name against an immutable registry (TOOL_REGISTRY), verifies role authorization, executes the python tool, and validates the output schema."),
        ("Step 5 (Observation & Re-planning): ", "The tool observation is ingested back into context, enabling the model to summarize findings or conclude."),
        ("Step 6 (Terminal Stop & Human-in-the-Loop Gate): ", "Execution halts deterministically at one of six terminal statuses. If a ticket was created, it is stored as PENDING_APPROVAL, halting autonomous progression (human_approval_required) until authenticated staff review, approve, or reject it via dedicated endpoints.")
    ]
    for b_title, b_desc in wf_steps:
        bp = doc.add_paragraph(style='List Bullet')
        bp.paragraph_format.line_spacing = 1.15
        bp.paragraph_format.space_after = Pt(3)
        r_bt = bp.add_run(b_title)
        r_bt.bold = True
        r_bt.font.name = "Calibri"
        r_desc = bp.add_run(b_desc)
        r_desc.font.name = "Calibri"

    h2_2 = doc.add_paragraph()
    h2_2.paragraph_format.space_before = Pt(10)
    h2_2.paragraph_format.space_after = Pt(4)
    r2_2 = h2_2.add_run("2.2 System Requirements and Acceptance Criteria")
    r2_2.font.name = "Calibri"
    r2_2.font.size = Pt(12.5)
    r2_2.bold = True
    r2_2.font.color.rgb = RGBColor(0x2E, 0x75, 0xB6)

    p_req = doc.add_paragraph()
    p_req.paragraph_format.line_spacing = 1.15
    p_req.paragraph_format.space_after = Pt(6)
    p_req.add_run(
        "The project established concrete Functional Requirements (FR), Non-Functional Requirements (NFR), and testable Acceptance Criteria (AC):"
    )

    req_items = [
        ("FR1 (Grounded Policy Assistance): ", "The system shall interpret free-text queries and retrieve relevant policy chunks from official documentation. AC: Answers must cite exact document IDs and page numbers (e.g., DOC001 p12). Queries with zero matching evidence must return an explicit 'no evidence found' statement without hallucination."),
        ("FR2 (Schedule Lookup): ", "The system shall query course schedules via check_timetable. AC: Valid course codes return synthetic class sessions; nonexistent codes return structured errors (Course not found) rather than fabricated schedules."),
        ("FR3 (Support Case Ticketing): ", "The system shall generate structured support tickets via create_support_ticket for issues requiring departmental action. AC: Every generated ticket must receive a unique ID, initialize in PENDING_APPROVAL status, and record category/summary."),
        ("FR4 (Human-in-the-Loop Governance): ", "The system shall restrict ticket approval and rejection exclusively to university staff. AC: Staff endpoints (/approve, /reject) must enforce role authentication (X-User-Role: staff); student attempts must return HTTP 403 Forbidden."),
        ("FR5 (Bounded Per-Session Memory): ", "The system shall maintain short-term context across conversation turns. AC: Exactly one prior turn summary is prepended to subsequent turns (24-hour TTL); follow-up queries regarding an active ticket must resolve without re-prompting."),
        ("NFR1 (Deterministic Safety): ", "Cognitive execution loops must be strictly bounded. AC: Loops must terminate deterministically within 4 iterations or 3 tool calls without hanging."),
        ("NFR2 (Data Privacy & Minimization): ", "Historical case retention must exclude raw conversation transcripts and student PII. AC: Attempted ingestion of forbidden keys (raw_transcript, phone_number) must raise a PrivacyViolationError."),
        ("NFR3 (Adversarial Robustness): ", "The agent must resist direct and indirect prompt injection. AC: System prompt override attempts and unauthorized tool dispatch commands must be safely neutralized.")
    ]
    for r_title, r_desc in req_items:
        rp = doc.add_paragraph(style='List Bullet')
        rp.paragraph_format.line_spacing = 1.15
        rp.paragraph_format.space_after = Pt(3)
        r_rt = rp.add_run(r_title)
        r_rt.bold = True
        r_rt.font.name = "Calibri"
        r_rdesc = rp.add_run(r_desc)
        r_rdesc.font.name = "Calibri"

    h2_3 = doc.add_paragraph()
    h2_3.paragraph_format.space_before = Pt(10)
    h2_3.paragraph_format.space_after = Pt(4)
    r2_3 = h2_3.add_run("2.3 AI Boundary Matrix")
    r2_3.font.name = "Calibri"
    r2_3.font.size = Pt(12.5)
    r2_3.bold = True
    r2_3.font.color.rgb = RGBColor(0x2E, 0x75, 0xB6)

    p_bm_intro = doc.add_paragraph()
    p_bm_intro.paragraph_format.line_spacing = 1.15
    p_bm_intro.paragraph_format.space_after = Pt(6)
    p_bm_intro.add_run(
        "A foundational architectural safeguard of UniSupport AI is the explicit partitioning of responsibilities across probabilistic AI, "
        "deterministic software logic, and mandatory human authorization. This tripartite division is formalized in Table 2.1."
    )

    # Table 2.1: AI Boundary Matrix
    tbl_bm = doc.add_table(rows=6, cols=3)
    tbl_bm.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tbl_bm)

    headers = ["AI May Do (Probabilistic)", "Stays Deterministic (Application Code)", "Requires Human Approval (Mandatory HITL)"]
    hdr_row = tbl_bm.rows[0]
    for i, title in enumerate(headers):
        cell = hdr_row.cells[i]
        set_cell_shading(cell, "1F4E79")
        set_cell_margins(cell, top=120, bottom=120, left=140, right=140)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        run = p.add_run(title)
        run.bold = True
        run.font.name = "Calibri"
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    matrix_data = [
        ("Synthesize natural language explanations grounded strictly in retrieved policy chunks.",
         "Query validation, Pydantic length bounds (1–2,000 chars), and input sanitization.",
         "Final determination on admissions, grading changes, fee waivers, or disciplinary actions."),
        ("Triage and classify unstructured student complaints into support categories.",
         "Role extraction from X-User-Role header and Role-Based Access Control (RBAC).",
         "Approving or transitioning a support ticket from PENDING_APPROVAL to SUBMITTED."),
        ("Select the appropriate tool (check_timetable or create_support_ticket) based on intent.",
         "Enforcement of the tool allow-list (frozenset(TOOL_REGISTRY)) and schema validation.",
         "Rejecting or permanently closing an active student support ticket."),
        ("Draft concise ticket summaries, categories, and descriptions from student input.",
         "UUID/ticket ID generation, timestamping, and SQLite database read/write transactions.",
         "Overriding deterministic departmental routing tables or escalation rules."),
        ("Formulate clarifying questions when student intent or course parameters are ambiguous.",
         "Enforcement of dual loop budgets (AGENT_MAX_ITERATIONS=4, MAX_TOOL_CALLS=3).",
         "Accessing confidential student academic transcripts or real-world university records.")
    ]

    for row_idx, data in enumerate(matrix_data, start=1):
        row = tbl_bm.rows[row_idx]
        bg_color = "F9FAFB" if row_idx % 2 == 1 else "FFFFFF"
        for col_idx, text in enumerate(data):
            cell = row.cells[col_idx]
            set_cell_shading(cell, bg_color)
            set_cell_margins(cell, top=80, bottom=80, left=120, right=120)
            p = cell.paragraphs[0]
            p.paragraph_format.line_spacing = 1.1
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            run = p.add_run(text)
            run.font.name = "Calibri"
            run.font.size = Pt(9.5)
            run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

    sp_bm = doc.add_paragraph()
    sp_bm.paragraph_format.space_before = Pt(4)
    sp_bm.paragraph_format.space_after = Pt(4)
    caption_bm = sp_bm.add_run("Table 2.1: UniSupport AI Boundary Matrix defining operational allocation.")
    caption_bm.font.name = "Calibri"
    caption_bm.font.size = Pt(9)
    caption_bm.font.italic = True
    caption_bm.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

    h2_4 = doc.add_paragraph()
    h2_4.paragraph_format.space_before = Pt(10)
    h2_4.paragraph_format.space_after = Pt(4)
    r2_4 = h2_4.add_run("2.4 Project Success Measures")
    r2_4.font.name = "Calibri"
    r2_4.font.size = Pt(12.5)
    r2_4.bold = True
    r2_4.font.color.rgb = RGBColor(0x2E, 0x75, 0xB6)

    p_sm = doc.add_paragraph()
    p_sm.paragraph_format.line_spacing = 1.15
    p_sm.paragraph_format.space_after = Pt(6)
    p_sm.add_run(
        "Project success was quantitatively evaluated against five pre-defined engineering criteria: "
        "(1) Grounded Retrieval Accuracy: ≥90% of in-corpus policy questions answered with correct document citations (achieved 100% on the evaluation set); "
        "(2) Zero Autonomous Escalation: 0 instances of autonomous ticket approvals, fee decisions, or grade alterations across all adversarial tests (achieved 0/14); "
        "(3) Loop Termination Reliability: 100% of agent runs terminate at an explicit terminal state within budget bounds without hanging (achieved 100%); "
        "(4) Failure Containment: 100% of simulated tool and provider failures handled gracefully via structured error observations without process crash (achieved 100%); and "
        "(5) Test Suite Coverage: Full system regression pass across ≥150 automated tests (achieved 178 passing tests)."
    )

    # =========================================================================
    # SECTION 10: RESULTS, LIMITATIONS AND PROFESSIONAL REFLECTION
    # =========================================================================
    h10 = doc.add_paragraph()
    h10.paragraph_format.space_before = Pt(18)
    h10.paragraph_format.space_after = Pt(6)
    r10 = h10.add_run("10. Results, Limitations and Professional Reflection")
    r10.font.name = "Calibri"
    r10.font.size = Pt(15)
    r10.bold = True
    r10.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)

    h10_1 = doc.add_paragraph()
    h10_1.paragraph_format.space_before = Pt(8)
    h10_1.paragraph_format.space_after = Pt(4)
    r10_1 = h10_1.add_run("10.1 What Works: Verified System Strengths")
    r10_1.font.name = "Calibri"
    r10_1.font.size = Pt(12.5)
    r10_1.bold = True
    r10_1.font.color.rgb = RGBColor(0x2E, 0x75, 0xB6)

    p_works = doc.add_paragraph()
    p_works.paragraph_format.line_spacing = 1.15
    p_works.paragraph_format.space_after = Pt(6)
    p_works.add_run(
        "The empirical evaluation demonstrates that UniSupport AI operates reliably within its defined academic support boundaries. Key achievements include:"
    )

    works_points = [
        ("Verifiable Source Grounding: ", "The RAG subsystem reliably grounds policy explanations in the Makerere policy corpus. Because citations are assembled from deterministic ChromaDB metadata rather than model text generation, citation hallucination is eliminated (DOC001 to DOC018)."),
        ("Resilient Agent Orchestration: ", "The orchestrator loop bounds cognitive execution through independent iteration and tool budgets. The system cleanly halts in one of six terminal statuses, preventing costly provider loops or hanging requests."),
        ("Immutable Human-in-the-Loop Barrier: ", "Support tickets are strictly drafted in PENDING_APPROVAL status. Transitions to SUBMITTED or REJECTED are architecturally isolated behind staff-authenticated REST endpoints that the LLM has no code path to execute."),
        ("Multi-Layer Adversarial Defense: ", "The system demonstrated complete resilience across 14 dedicated adversarial penetration tests, neutralizing prompt injections, instruction overrides, system prompt extraction, and role header spoofing."),
        ("Privacy-Preserving Continuity: ", "Per-session memory maintains multi-turn context (e.g., resolving follow-up questions to an active ticket) while the case history store enforces strict data minimization, rejecting raw transcripts and student PII via PrivacyViolationError.")
    ]
    for w_title, w_desc in works_points:
        wp = doc.add_paragraph(style='List Bullet')
        wp.paragraph_format.line_spacing = 1.15
        wp.paragraph_format.space_after = Pt(3)
        r_wt = wp.add_run(w_title)
        r_wt.bold = True
        r_wt.font.name = "Calibri"
        r_wdesc = wp.add_run(w_desc)
        r_wdesc.font.name = "Calibri"

    h10_2 = doc.add_paragraph()
    h10_2.paragraph_format.space_before = Pt(10)
    h10_2.paragraph_format.space_after = Pt(4)
    r10_2 = h10_2.add_run("10.2 What Does Not Work and Genuine Technical Failures")
    r10_2.font.name = "Calibri"
    r10_2.font.size = Pt(12.5)
    r10_2.bold = True
    r10_2.font.color.rgb = RGBColor(0x2E, 0x75, 0xB6)

    p_fails = doc.add_paragraph()
    p_fails.paragraph_format.line_spacing = 1.15
    p_fails.paragraph_format.space_after = Pt(6)
    p_fails.add_run(
        "Development and rigorous testing uncovered several non-contrived architectural failure modes that highlight the boundaries of current techniques:"
    )

    fails_points = [
        ("Chunk-Boundary Bisection (Failure F4): ", "The fixed-offset chunking strategy (1,000 characters with 150-character overlap) operates without syntactic awareness. In testing, chunk boundaries occasionally bifurcated legal sub-clauses across page boundaries, resulting in incomplete evidence retrieval."),
        ("Scanned PDF Text Inaccessibility: ", "Six of the original 18 university policy PDFs were scanned image-only documents. Standard text extraction (pypdf) yielded zero extractable characters, necessitating their manual removal from the corpus manifest until OCR pipelines are introduced."),
        ("Provider Non-Compliance with Tool Choice: ", "When setting tool_choice='none' after budget exhaustion, third-party LLM providers occasionally continued returning tool-call JSON objects. This forced the implementation of hard code-level interception within orchestrator.py to suppress unauthorized downstream dispatches."),
        ("Rigid Timetable Lookup Semantics: ", "The check_timetable tool relies on exact alphanumeric course code matching. Queries with minor spelling variations or natural language course descriptions fail to match without a semantic alias layer.")
    ]
    for f_title, f_desc in fails_points:
        fp = doc.add_paragraph(style='List Bullet')
        fp.paragraph_format.line_spacing = 1.15
        fp.paragraph_format.space_after = Pt(3)
        r_ft = fp.add_run(f_title)
        r_ft.bold = True
        r_ft.font.name = "Calibri"
        r_fdesc = fp.add_run(f_desc)
        r_fdesc.font.name = "Calibri"

    h10_3 = doc.add_paragraph()
    h10_3.paragraph_format.space_before = Pt(10)
    h10_3.paragraph_format.space_after = Pt(4)
    r10_3 = h10_3.add_run("10.3 Remaining Risks, Cost, and Latency")
    r10_3.font.name = "Calibri"
    r10_3.font.size = Pt(12.5)
    r10_3.bold = True
    r10_3.font.color.rgb = RGBColor(0x2E, 0x75, 0xB6)

    p_risk = doc.add_paragraph()
    p_risk.paragraph_format.line_spacing = 1.15
    p_risk.paragraph_format.space_after = Pt(6)
    p_risk.add_run(
        "Several residual risks and operational trade-offs remain for real-world institutional adoption: "
        "(1) Simulated Authorization: Role verification relies on the HTTP X-User-Role header. While sufficient for a capstone prototype, deploying this in production without institutional SSO (e.g., OAuth2/OpenID Connect linked to Makerere EduID) would allow trivial header spoofing by malicious clients. "
        "(2) Upstream API Availability: The system depends on external foundation model endpoints (Groq). Cloud network latency, token rate limits, and provider downtime (manifesting as HTTP 502/503 errors) represent points of vulnerability outside the application's control. "
        "(3) Cost and Latency Profile: The system demonstrates exceptional cost efficiency: local MiniLM embeddings incur zero API charges, while Groq inference averages under $0.001 per student turn. Latency averages 1.2–2.5 seconds per turn across multi-step agent iterations, providing responsive real-time interaction but remaining subject to cloud API spikes."
    )

    h10_4 = doc.add_paragraph()
    h10_4.paragraph_format.space_before = Pt(10)
    h10_4.paragraph_format.space_after = Pt(4)
    r10_4 = h10_4.add_run("10.4 Future Work and Professional Reflection")
    r10_4.font.name = "Calibri"
    r10_4.font.size = Pt(12.5)
    r10_4.bold = True
    r10_4.font.color.rgb = RGBColor(0x2E, 0x75, 0xB6)

    p_future = doc.add_paragraph()
    p_future.paragraph_format.line_spacing = 1.15
    p_future.paragraph_format.space_after = Pt(6)
    p_future.add_run(
        "Future engineering enhancements should prioritize four key areas: (1) integrating enterprise institutional authentication (EduID SSO) to replace simulated headers; "
        "(2) establishing live read/write adapters with Makerere's Academic Information Management System (AIMS) for authentic timetable and enrolment data; "
        "(3) implementing structure-aware semantic chunking (e.g., Markdown/HTML header hierarchy parsing) combined with OCR preprocessing for historical circulars; and "
        "(4) incorporating an active semantic classifier for early detection and redirection of out-of-scope high-impact requests."
    )

    p_reflection = doc.add_paragraph()
    p_reflection.paragraph_format.line_spacing = 1.15
    p_reflection.paragraph_format.space_after = Pt(8)
    p_reflection.add_run(
        "Professional Reflection and Human Responsibility: Developing UniSupport AI reinforced a critical paradigm in AI-native software engineering: "
        "probabilistic foundation models must never be entrusted with authoritative institutional power. In high-stakes university environments, "
        "allowing an LLM to autonomously approve financial waivers, alter grades, or resolve disciplinary hearings creates unacceptable legal, "
        "ethical, and institutional liabilities. Software engineers bear the professional duty to bound AI systems through robust, deterministic "
        "application layers, explicit tool registries, transparent audit trails, and non-negotiable Human-in-the-Loop checkpoints. "
        "UniSupport AI demonstrates that when artificial intelligence is positioned strictly as a cognitive amplifier for information triage, "
        "retrieval, and draft generation—while preserving deterministic governance and human primacy—it provides profound administrative relief "
        "without compromising institutional integrity."
    )

    # Save document
    doc.save(output_path)
    print(f"Report successfully generated at: {output_path}")

if __name__ == "__main__":
    out_file = os.path.abspath("docs/UniSupport_AI_Final_Report_Sections_1_2_10.docx")
    build_report_docx(out_file)
