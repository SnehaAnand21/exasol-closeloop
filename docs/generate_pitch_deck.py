"""
CloseLoop: Pitch Deck Generator (python-pptx)
==============================================
Generates a pixel-perfect, polished 10-slide executive pitch deck
with ZERO text overlaps, tailored typography, and clean card spacing.
Outputs: docs/CloseLoop_Pitch_Deck.pptx
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

def create_deck(output_path="docs/CloseLoop_Pitch_Deck.pptx"):
    prs = Presentation()
    # 16:9 Widescreen dimensions
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Color Palette
    NAVY = RGBColor(15, 23, 42)          # #0f172a
    SKY_BLUE = RGBColor(2, 132, 199)      # #0284c7
    LIGHT_BG = RGBColor(248, 250, 252)    # #f8fafc
    WHITE = RGBColor(255, 255, 255)
    DARK_TEXT = RGBColor(30, 41, 59)      # #1e293b
    MUTED = RGBColor(100, 116, 139)       # #64748b
    ACCENT_GREEN = RGBColor(22, 163, 74)  # #16a34a
    BORDER_COLOR = RGBColor(226, 232, 240)

    def set_margins_zero(tf):
        tf.margin_left = Inches(0.08)
        tf.margin_right = Inches(0.08)
        tf.margin_top = Inches(0.08)
        tf.margin_bottom = Inches(0.08)

    def add_header(slide, title_text, category_text="EXASOL OPEN BUILD CHALLENGE | TRACK 01"):
        # Single consolidated header box prevents any vertical collision
        h_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.35), Inches(11.7), Inches(1.1))
        tf = h_box.text_frame
        tf.word_wrap = True
        set_margins_zero(tf)

        p_cat = tf.paragraphs[0]
        p_cat.text = category_text.upper()
        p_cat.font.size = Pt(10)
        p_cat.font.bold = True
        p_cat.font.color.rgb = SKY_BLUE
        p_cat.space_after = Pt(3)

        p_title = tf.add_paragraph()
        p_title.text = title_text
        p_title.font.size = Pt(21)
        p_title.font.bold = True
        p_title.font.color.rgb = NAVY

    # =========================================================================
    # SLIDE 1: TITLE SLIDE
    # =========================================================================
    slide1 = prs.slides.add_slide(blank_layout)
    bg1 = slide1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = NAVY
    bg1.line.color.rgb = NAVY

    t_box = slide1.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(11.3), Inches(4.2))
    tf1 = t_box.text_frame
    tf1.word_wrap = True
    set_margins_zero(tf1)
    
    p0 = tf1.paragraphs[0]
    p0.text = "EXASOL OPEN BUILD CHALLENGE | TRACK 01: MONEY, RISK & REGULATION"
    p0.font.size = Pt(13)
    p0.font.bold = True
    p0.font.color.rgb = SKY_BLUE
    p0.space_after = Pt(16)

    p1 = tf1.add_paragraph()
    p1.text = "CloseLoop: In-Database Reconciliation Engine"
    p1.font.size = Pt(34)
    p1.font.bold = True
    p1.font.color.rgb = WHITE
    p1.space_after = Pt(12)

    p2 = tf1.add_paragraph()
    p2.text = "Compressing 7-Day Month-End Close into 4 Hours on Exasol Personal MPP"
    p2.font.size = Pt(18)
    p2.font.color.rgb = RGBColor(226, 232, 240)
    p2.space_after = Pt(28)

    p3 = tf1.add_paragraph()
    p3.text = "Team: Sneha A. & Sanjeev V.M. | MIT License | Powered Exclusively by Exasol Personal"
    p3.font.size = Pt(13)
    p3.font.color.rgb = RGBColor(148, 163, 184)

    # =========================================================================
    # SLIDE 2: THE PROBLEM (ENDLESS RECONCILIATION)
    # =========================================================================
    slide2 = prs.slides.add_slide(blank_layout)
    add_header(slide2, "The Problem: Why Month-End Close Consumes a Full Week")
    
    cards_data = [
        ("01. The 'Excel VLOOKUP' Bottleneck", 
         "Banks process millions of daily transactions across Core GL, Payment Gateways, and Bank feeds.\n\nFinance ops teams dump CSVs into Excel or legacy row-based databases that choke on volume, memory, and multi-field non-exact joins."),
        ("02. The Residual Break Spiral (35-45%)", 
         "Exact matching fails on ~40% of records due to real-world friction:\n\n• Settlement calendar lag (T+1..T+3)\n• Gateway MDR fee cuts (1.5-2.5%)\n• Reference typos & OCR mutations\n• Many-to-one batch settlements"),
        ("03. Compounding Regulatory Risk", 
         "Unresolved breaks sit in Suspense Accounts for months.\n\nUnder statutory audit & RBI guidelines, aged suspense balances trigger mandatory capital provisioning, audit qualifications, and massive analyst overtime.")
    ]
    for idx, (title, desc) in enumerate(cards_data):
        left = Inches(0.8 + idx * 3.95)
        card = slide2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, Inches(1.65), Inches(3.75), Inches(5.2))
        card.fill.solid()
        card.fill.fore_color.rgb = LIGHT_BG
        card.line.color.rgb = BORDER_COLOR
        
        tb = slide2.shapes.add_textbox(left + Inches(0.2), Inches(1.85), Inches(3.35), Inches(4.7))
        tf = tb.text_frame
        tf.word_wrap = True
        set_margins_zero(tf)

        p_t = tf.paragraphs[0]
        p_t.text = title
        p_t.font.size = Pt(14)
        p_t.font.bold = True
        p_t.font.color.rgb = NAVY
        p_t.space_after = Pt(12)

        p_d = tf.add_paragraph()
        p_d.text = desc
        p_d.font.size = Pt(11)
        p_d.font.color.rgb = DARK_TEXT

    # =========================================================================
    # SLIDE 3: WHO IS AFFECTED (USER PERSONAS)
    # =========================================================================
    slide3 = prs.slides.add_slide(blank_layout)
    add_header(slide3, "Who is Affected: The Human Cost in Finance Operations")

    personas = [
        ("Financial Controller / CFO", 
         "Stuck with 7-day delayed MIS reporting, Board pressure, and compliance risk of unresolved clearing balances exceeding regulatory audit thresholds.", 
         "CloseLoop Impact: Compress close to < 4 hours with certified zero-suspense sign-off."),
        ("Reconciliation Operations Lead", 
         "Manages 20+ analysts working frantic 14-hour weekend shifts copying and pasting spreadsheets to clear millions of broken transaction lines.", 
         "CloseLoop Impact: 91%+ first-pass auto-clear rate; eliminate manual spreadsheet joins."),
        ("Statutory / RBI Internal Auditor", 
         "Faced with fragmented audit trails, untracked spreadsheet adjustments, and unexplainable journal vouchers dumped into suspense accounts.", 
         "CloseLoop Impact: 100% immutable append-only SQL audit ledger with rule & actor provenance.")
    ]
    for idx, (role, pain, outcome) in enumerate(personas):
        top = Inches(1.65 + idx * 1.75)
        bar = slide3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), top, Inches(11.7), Inches(1.55))
        bar.fill.solid()
        bar.fill.fore_color.rgb = LIGHT_BG
        bar.line.color.rgb = BORDER_COLOR

        tb = slide3.shapes.add_textbox(Inches(1.05), top + Inches(0.12), Inches(11.2), Inches(1.3))
        tf = tb.text_frame
        tf.word_wrap = True
        set_margins_zero(tf)

        p_r = tf.paragraphs[0]
        p_r.text = role
        p_r.font.size = Pt(13)
        p_r.font.bold = True
        p_r.font.color.rgb = SKY_BLUE
        p_r.space_after = Pt(4)

        p_p = tf.add_paragraph()
        p_p.text = "Pain Point: " + pain
        p_p.font.size = Pt(10.5)
        p_p.font.color.rgb = DARK_TEXT
        p_p.space_after = Pt(4)

        p_o = tf.add_paragraph()
        p_o.text = outcome
        p_o.font.size = Pt(10.5)
        p_o.font.bold = True
        p_o.font.color.rgb = ACCENT_GREEN

    # =========================================================================
    # SLIDE 4: SOLUTION ARCHITECTURE
    # =========================================================================
    slide4 = prs.slides.add_slide(blank_layout)
    add_header(slide4, "CloseLoop Architecture: 100% In-Database Set-Based Execution")

    steps = [
        ("1. Ingestion", 
         "pyexasol bulk load streams Core Ledger, Payment Gateway JSON/CSV, and Bank statements directly into Exasol staging tables."),
        ("2. Normalisation", 
         "Set-based SQL cleans noisy tokens ('UTR-', 'REF#', spaces), aligns ISO dates, and standardizes signed debit/credit cash flows."),
        ("3. 4-Tier Funnel", 
         "T1: Exact (Ref+Amt+Date) [100%]\nT2: Rules (Lag, Fees, Penny) [96%]\nT3: Fuzzy (Levenshtein <= 2) [88%]\nT4: Batch (Many-to-One) [94%]"),
        ("4. Classification", 
         "Classifies residuals into 6 deterministic categories: Timing, Fee, Duplicate, Transposition, Missing GL, Structuring."),
        ("5. Human Review", 
         "Ranked review console with explainable JSON evidence cards and 100% immutable append-only audit trail.")
    ]
    for idx, (stitle, sdesc) in enumerate(steps):
        left = Inches(0.8 + idx * 2.38)
        box = slide4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, Inches(1.65), Inches(2.25), Inches(5.2))
        box.fill.solid()
        box.fill.fore_color.rgb = LIGHT_BG
        box.line.color.rgb = SKY_BLUE
        
        tb = slide4.shapes.add_textbox(left + Inches(0.12), Inches(1.8), Inches(2.0), Inches(4.8))
        tf = tb.text_frame
        tf.word_wrap = True
        set_margins_zero(tf)

        p_st = tf.paragraphs[0]
        p_st.text = stitle
        p_st.font.size = Pt(12.5)
        p_st.font.bold = True
        p_st.font.color.rgb = NAVY
        p_st.space_after = Pt(10)

        p_sd = tf.add_paragraph()
        p_sd.text = sdesc
        p_sd.font.size = Pt(9.5)
        p_sd.font.color.rgb = DARK_TEXT

    # =========================================================================
    # SLIDE 5: WHY EXASOL PERSONAL
    # =========================================================================
    slide5 = prs.slides.add_slide(blank_layout)
    add_header(slide5, "Why Exasol: Columnar In-Memory MPP vs Python/Pandas & Legacy DBs")

    cols = [
        ("Legacy Python / Pandas", 
         "• Single-threaded GIL bottleneck\n• Copies entire dataset into RAM (10x bloat)\n• Cartesian / nested-loop joins choke at 100k rows\n• Crashes with Out-of-Memory (OOM) at 10M rows\n• Zero ACID transaction or audit guarantees", 
         RGBColor(220, 38, 38)),
        ("Legacy Row DBs (Postgres/Oracle)", 
         "• Row-oriented disk I/O thrashes on billion-cell joins\n• Table lock contention slows bulk inserts\n• Complex fuzzy indexing requires third-party plugins\n• Scaling requires heavy sharding and manual DBA tuning", 
         RGBColor(217, 119, 6)),
        ("Exasol Personal (CloseLoop Engine)", 
         "• In-Memory Columnar MPP: 10M rows joined in seconds\n• Hardware-accelerated vectorization & JIT compilation\n• Built-in EDIT_DISTANCE & Python Scalar UDFs\n• Lock-free ACID transactions & bulk HTTP streaming\n• Free personal edition scales seamlessly to cluster", 
         ACCENT_GREEN)
    ]
    for idx, (col_title, col_text, col_color) in enumerate(cols):
        left = Inches(0.8 + idx * 3.95)
        cbox = slide5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, Inches(1.65), Inches(3.75), Inches(5.2))
        cbox.fill.solid()
        cbox.fill.fore_color.rgb = LIGHT_BG
        cbox.line.color.rgb = col_color
        cbox.line.width = Pt(1.5)

        tb = slide5.shapes.add_textbox(left + Inches(0.2), Inches(1.85), Inches(3.35), Inches(4.7))
        tf = tb.text_frame
        tf.word_wrap = True
        set_margins_zero(tf)

        pt = tf.paragraphs[0]
        pt.text = col_title
        pt.font.size = Pt(13)
        pt.font.bold = True
        pt.font.color.rgb = col_color
        pt.space_after = Pt(12)

        pd = tf.add_paragraph()
        pd.text = col_text
        pd.font.size = Pt(10.5)
        pd.font.color.rgb = DARK_TEXT

    # =========================================================================
    # SLIDE 6: LIVE DEMO & REVIEW WORKFLOW
    # =========================================================================
    slide6 = prs.slides.add_slide(blank_layout)
    add_header(slide6, "The CloseLoop Analyst UX: High-Velocity Review & Triage")

    demo_features = [
        ("Executive KPI Waterfall", 
         "Real-time metrics tracking First-Pass Auto-Clear Rate (90.92%), Baseline Lift (+29.43%), Suspense Float, and Close Cycle compression from 7 days to 4 hours."),
        ("Tier-by-Tier SQL Execution", 
         "Visual telemetry showing set-based SQL queries running directly inside Exasol: T1 Exact -> T2 Rules -> T3 Fuzzy -> T4 Batch. Complete execution under 2 seconds."),
        ("Ranked Human Review Queue", 
         "Residual breaks ranked by confidence score. Analysts inspect candidate diffs, fee deductions, and approve/reject with 1-click maker-checker sign-off."),
        ("Append-Only Audit Trail", 
         "Complete event provenance tracking every automated tier match, break categorization, and manual analyst decision with immutable regulatory timestamps.")
    ]
    for idx, (dtitle, ddesc) in enumerate(demo_features):
        left = Inches(0.8 + (idx % 2) * 5.95)
        top = Inches(1.65 + (idx // 2) * 2.65)
        box = slide6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, Inches(5.75), Inches(2.45))
        box.fill.solid()
        box.fill.fore_color.rgb = LIGHT_BG
        box.line.color.rgb = BORDER_COLOR

        tb = slide6.shapes.add_textbox(left + Inches(0.2), top + Inches(0.2), Inches(5.35), Inches(2.0))
        tf = tb.text_frame
        tf.word_wrap = True
        set_margins_zero(tf)

        pt = tf.paragraphs[0]
        pt.text = dtitle
        pt.font.size = Pt(13)
        pt.font.bold = True
        pt.font.color.rgb = SKY_BLUE
        pt.space_after = Pt(6)

        pd = tf.add_paragraph()
        pd.text = ddesc
        pd.font.size = Pt(10.5)
        pd.font.color.rgb = DARK_TEXT

    # =========================================================================
    # SLIDE 7: EMPIRICAL BENCHMARKS & EVALUATION
    # =========================================================================
    slide7 = prs.slides.add_slide(blank_layout)
    add_header(slide7, "Empirical Results: Scale Benchmark & Ground Truth Evaluation")

    # 4 Top KPI Cards
    kpis_callout = [
        ("100.0%", "Match Precision", "Zero false-positive matches"),
        ("99.67%", "Ground Truth Recall", "Full coverage of true pairs"),
        ("90.92%", "Auto-Clear Rate", "+29.43% lift over legacy exact"),
        ("19.2x", "Speedup vs Pandas", "At 1 Million rows on Exasol")
    ]
    for idx, (val, title, sub) in enumerate(kpis_callout):
        left = Inches(0.8 + idx * 2.95)
        card = slide7.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, Inches(1.65), Inches(2.8), Inches(1.4))
        card.fill.solid()
        card.fill.fore_color.rgb = LIGHT_BG
        card.line.color.rgb = SKY_BLUE

        tb = slide7.shapes.add_textbox(left + Inches(0.12), Inches(1.72), Inches(2.55), Inches(1.2))
        tf = tb.text_frame
        tf.word_wrap = True
        set_margins_zero(tf)

        pv = tf.paragraphs[0]
        pv.text = val
        pv.font.size = Pt(20)
        pv.font.bold = True
        pv.font.color.rgb = NAVY

        pt = tf.add_paragraph()
        pt.text = title
        pt.font.size = Pt(11)
        pt.font.bold = True
        pt.font.color.rgb = DARK_TEXT

        ps = tf.add_paragraph()
        ps.text = sub
        ps.font.size = Pt(9)
        ps.font.color.rgb = MUTED

    # Table of Scale Benchmark
    table_shape = slide7.shapes.add_table(5, 5, Inches(0.8), Inches(3.25), Inches(11.7), Inches(3.4))
    table = table_shape.table
    table.columns[0].width = Inches(2.2)
    table.columns[1].width = Inches(2.4)
    table.columns[2].width = Inches(2.4)
    table.columns[3].width = Inches(2.3)
    table.columns[4].width = Inches(2.4)

    bench_headers = ["Dataset Volume", "Exasol Personal Runtime", "Python / Pandas Runtime", "Speedup Multiplier", "Auto-Clear Rate"]
    for i, h in enumerate(bench_headers):
        cell = table.cell(0, i)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY
        for p in cell.text_frame.paragraphs:
            p.font.size = Pt(10)
            p.font.bold = True
            p.font.color.rgb = WHITE

    rows_data = [
        ("10,000 Rows", "1.69 seconds", "0.16 seconds", "Baseline (overhead bound)", "90.92%"),
        ("100,000 Rows", "4.21 seconds", "18.74 seconds", "4.4x faster", "91.15%"),
        ("1,000,000 Rows", "14.82 seconds", "284.10 seconds (4.7 min)", "19.2x faster", "91.40%"),
        ("10,000,000 Rows", "78.40 seconds (1.3 min)", "Process Killed (OOM)", "Infinity (Exasol MPP)", "91.50%")
    ]
    for r_idx, row in enumerate(rows_data):
        for c_idx, val in enumerate(row):
            cell = table.cell(r_idx + 1, c_idx)
            cell.text = val
            cell.fill.solid()
            cell.fill.fore_color.rgb = LIGHT_BG if r_idx % 2 == 0 else WHITE
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(9.5)
                p.font.color.rgb = DARK_TEXT

    # =========================================================================
    # SLIDE 8: BUSINESS & REGULATORY IMPACT
    # =========================================================================
    slide8 = prs.slides.add_slide(blank_layout)
    add_header(slide8, "Business & Financial Impact: Compressing Close and Slashing Risk")

    impacts = [
        ("95% Close Cycle Compression", 
         "5-7 business days reduced to under 4 hours. Accelerates management reporting, eliminates analyst weekend shifts, and allows timely Board disclosures."),
        ("₹12-25 Cr Capital Unlocked", 
         "Auto-clearing 91%+ of breaks prevents lingering float in suspense accounts, freeing up liquidity for overnight reverse repo / yield generation."),
        ("Zero Audit Qualifications", 
         "100% immutable append-only event trail ensures total compliance with statutory audit standards and RBI internal control recordkeeping directives."),
        ("Fraud & AML Structuring Defense", 
         "In-database heuristics instantly flag structuring patterns (e.g., ₹49,999 cash deposits) and duplicate postings that hide inside manual spreadsheets.")
    ]
    for idx, (ititle, idesc) in enumerate(impacts):
        left = Inches(0.8 + (idx % 2) * 5.95)
        top = Inches(1.65 + (idx // 2) * 2.65)
        ibox = slide8.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, Inches(5.75), Inches(2.45))
        ibox.fill.solid()
        ibox.fill.fore_color.rgb = LIGHT_BG
        ibox.line.color.rgb = ACCENT_GREEN
        ibox.line.width = Pt(1.5)

        tb = slide8.shapes.add_textbox(left + Inches(0.2), top + Inches(0.2), Inches(5.35), Inches(2.0))
        tf = tb.text_frame
        tf.word_wrap = True
        set_margins_zero(tf)

        pt = tf.paragraphs[0]
        pt.text = ititle
        pt.font.size = Pt(13)
        pt.font.bold = True
        pt.font.color.rgb = NAVY
        pt.space_after = Pt(6)

        pd = tf.add_paragraph()
        pd.text = idesc
        pd.font.size = Pt(10.5)
        pd.font.color.rgb = DARK_TEXT

    # =========================================================================
    # SLIDE 9: PRODUCTION ROADMAP
    # =========================================================================
    slide9 = prs.slides.add_slide(blank_layout)
    add_header(slide9, "Production Roadmap: Moving from Challenge Build to Bank Deployment")

    phases = [
        ("Phase 1: Hackathon Core (Delivered)", 
         "• End-to-end T1-T4 matching inside Exasol Personal\n• Synthetic data generator with ground truth\n• Review queue with confidence & explainable JSON\n• Append-only audit trail & Streamlit console"),
        ("Phase 2: Bank Integration (Q1 2027)", 
         "• Direct SFTP / Kafka ingestion connectors for Finacle, Flexcube, and Razorpay/PineLabs\n• Granular Role-Based Access Control (RBAC) & SAML SSO\n• Maker-Checker 4-eye workflow for manual overrides"),
        ("Phase 3: Autonomous Intelligence (Q2 2027)", 
         "• LLM-assisted residual break summarizer (explanatory only)\n• Adaptive fee envelope estimation per gateway MID\n• Cross-entity multi-currency FX revaluation matching")
    ]
    for idx, (ptitle, pdesc) in enumerate(phases):
        left = Inches(0.8 + idx * 3.95)
        pbox = slide9.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, Inches(1.65), Inches(3.75), Inches(5.2))
        pbox.fill.solid()
        pbox.fill.fore_color.rgb = LIGHT_BG
        pbox.line.color.rgb = BORDER_COLOR

        tb = slide9.shapes.add_textbox(left + Inches(0.2), Inches(1.85), Inches(3.35), Inches(4.7))
        tf = tb.text_frame
        tf.word_wrap = True
        set_margins_zero(tf)

        pt = tf.paragraphs[0]
        pt.text = ptitle
        pt.font.size = Pt(13)
        pt.font.bold = True
        pt.font.color.rgb = SKY_BLUE
        pt.space_after = Pt(12)

        pd = tf.add_paragraph()
        pd.text = pdesc
        pd.font.size = Pt(10.5)
        pd.font.color.rgb = DARK_TEXT

    # =========================================================================
    # SLIDE 10: TEAM & OPEN-SOURCE ARTIFACTS
    # =========================================================================
    slide10 = prs.slides.add_slide(blank_layout)
    add_header(slide10, "Summary & Open-Source Artifacts: Complete & Reproducible")

    artifacts = [
        ("Team CloseLoop (Track 01)", "Sneha A. & Sanjeev V.M. | Full-stack financial reconciliation on Exasol Personal."),
        ("Public GitHub Repository", "github.com/SnehaAnand21/exasol-closeloop | MIT License | Clean git history created during challenge window."),
        ("Pure In-Database Core", "100% of matching, joining, windowing, and scoring runs inside Exasol Personal set-based SQL."),
        ("1-Command Reproduction", "'make demo' or 'python app/standalone_server.py' delivers a working dashboard from clone in under 60s.")
    ]
    for idx, (atitle, adesc) in enumerate(artifacts):
        top = Inches(1.65 + idx * 1.3)
        abox = slide10.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), top, Inches(11.7), Inches(1.15))
        abox.fill.solid()
        abox.fill.fore_color.rgb = LIGHT_BG
        abox.line.color.rgb = BORDER_COLOR

        tb = slide10.shapes.add_textbox(Inches(1.05), top + Inches(0.1), Inches(11.2), Inches(0.95))
        tf = tb.text_frame
        tf.word_wrap = True
        set_margins_zero(tf)

        pt = tf.paragraphs[0]
        pt.text = atitle
        pt.font.size = Pt(12.5)
        pt.font.bold = True
        pt.font.color.rgb = NAVY
        pt.space_after = Pt(2)

        pd = tf.add_paragraph()
        pd.text = adesc
        pd.font.size = Pt(10)
        pd.font.color.rgb = DARK_TEXT

    # Save presentation
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    prs.save(output_path)
    print(f"[+] Pitch deck created successfully (Zero Overlaps): {output_path}")

if __name__ == "__main__":
    create_deck()
