"""
CloseLoop: PDF Pitch Deck Generator using Matplotlib
====================================================
Renders the complete 10-slide executive presentation into a crisp, widescreen PDF.
Outputs: docs/CloseLoop_Pitch_Deck.pdf
"""

import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.patches as patches

def generate_pdf_deck(output_pdf="docs/CloseLoop_Pitch_Deck.pdf"):
    pdf_pages = PdfPages(output_pdf)

    # Slide themes & color palette
    NAVY = "#0f172a"
    SKY_BLUE = "#0284c7"
    LIGHT_BG = "#f8fafc"
    WHITE = "#ffffff"
    DARK_TEXT = "#1e293b"
    MUTED = "#64748b"
    GREEN = "#16a34a"

    slides_content = [
        # Slide 1: Title
        {
            "is_title": True,
            "category": "TRACK 01: MONEY, RISK & REGULATION",
            "title": "CloseLoop: In-Database Reconciliation Engine",
            "subtitle": "Compressing 7-Day Month-End Close into 4 Hours on Exasol Personal MPP",
            "footer": "Team: Sneha A. & Sanjeev V.M. | Open-Source MIT License | Built Exclusively for Exasol Personal"
        },
        # Slide 2: The Problem
        {
            "is_title": False,
            "title": "The Problem: Why Month-End Close Consumes a Full Week",
            "boxes": [
                ("01. The 'Excel VLOOKUP' Bottleneck", "Banks process millions of daily transactions across Core GL, Payment Gateways, and Bank statements. Analysts dump CSVs into Excel or row-based databases that choke on volume and cannot handle non-exact joins."),
                ("02. The Residual Break Spiral (35-45%)", "Exact matching fails on ~40% of records due to settlement calendar lag (T+1..T+3), payment gateway MDR fee cuts (1.5-2.5%), OCR typos in UTR numbers, and many-to-one batch settlements."),
                ("03. Compounding Regulatory & Capital Risk", "Unreconciled residuals sit in Suspense Accounts for months. Under statutory audit & RBI guidelines, aged suspense balances trigger mandatory capital provisioning, audit qualifications, and massive analyst burnout.")
            ]
        },
        # Slide 3: Who is Affected
        {
            "is_title": False,
            "title": "Who is Affected: The Human Cost in Finance Operations",
            "rows": [
                ("Financial Controller / CFO", "Stuck with 7-day delayed MIS reporting, Board pressure, and compliance risk of unresolved clearing balances exceeding regulatory audit thresholds.", "Outcome: Compress close to < 4 hours with certified zero-suspense sign-off."),
                ("Reconciliation Operations Lead", "Manages 20+ analysts working frantic 14-hour weekend shifts copying and pasting spreadsheets to clear millions of broken transaction lines.", "Outcome: 91%+ first-pass auto-clear rate; eliminate manual spreadsheet joins."),
                ("Statutory / RBI Internal Auditor", "Faced with fragmented audit trails, untracked spreadsheet adjustments, and unexplainable journal vouchers dumped into suspense accounts.", "Outcome: 100% immutable append-only SQL audit ledger with rule & actor provenance.")
            ]
        },
        # Slide 4: Solution Architecture
        {
            "is_title": False,
            "title": "CloseLoop Architecture: 100% In-Database Set-Based Execution",
            "steps": [
                ("1. Multi-Feed Ingest", "pyexasol bulk load ingests Core Ledger, Payment Gateway JSON/CSV, and Bank statements directly into Exasol staging tables."),
                ("2. Set-Based Normalisation", "SQL cleans noisy tokens ('UTR-', 'REF#', spaces), aligns ISO dates, and standardizes signed debit/credit cash flows."),
                ("3. 4-Tier Matching Funnel", "Tier 1: Exact (Ref+Amt+Date) • 100% Conf\nTier 2: Rules (Lag, MDR Fees, Penny) • 96% Conf\nTier 3: Fuzzy (Levenshtein Dist <= 2) • 88% Conf\nTier 4: Batch (Many-to-One payouts) • 94% Conf"),
                ("4. Break Classification", "Classifies residuals into 6 deterministic categories (Timing, Fee, Duplicate, Transposition, Missing GL, Structuring)."),
                ("5. Human-in-the-Loop", "Ranked review console with explainable JSON evidence cards and 100% immutable append-only audit trail.")
            ]
        },
        # Slide 5: Why Exasol
        {
            "is_title": False,
            "title": "Why Exasol: Columnar In-Memory MPP vs Python/Pandas & Legacy DBs",
            "comparisons": [
                ("Legacy Python / Pandas", "• Single-threaded GIL bottleneck\n• Copies entire dataset into RAM (10x bloat)\n• Cartesian / nested-loop joins choke at 100k rows\n• Crashes with Out-of-Memory (OOM) at 10M rows\n• No built-in transaction ACID or audit guarantees", "#dc2626"),
                ("Legacy Row DBs (Postgres/Oracle)", "• Row-oriented disk I/O thrashes on billion-cell joins\n• Table lock contention slows bulk inserts\n• Complex fuzzy indexing requires third-party plugins\n• Scaling requires heavy sharding and manual tuning", "#d97706"),
                ("Exasol Personal (CloseLoop Engine)", "• In-Memory Columnar MPP: 10M rows joined in seconds\n• Hardware-accelerated vectorization & JIT compilation\n• Built-in EDIT_DISTANCE & Python Scalar UDFs\n• Lock-free ACID transactions & bulk HTTP streaming\n• Free personal edition scales seamlessly to multi-node", "#16a34a")
            ]
        },
        # Slide 6: Analyst UX
        {
            "is_title": False,
            "title": "The CloseLoop Analyst UX: High-Velocity Review & Triage",
            "grid": [
                ("Executive KPI Waterfall", "Real-time metrics tracking First-Pass Auto-Clear Rate (90.92%), Baseline Lift (+29.43%), Suspense Float, and Close Cycle compression."),
                ("Tier-by-Tier SQL Execution", "Visual telemetry showing set-based SQL queries running directly inside Exasol: T1 Exact -> T2 Rules -> T3 Fuzzy -> T4 Batch."),
                ("Ranked Human Review Queue", "Residual breaks ranked by confidence score. Analysts inspect candidate diffs, fee deductions, and approve/reject with 1-click."),
                ("Append-Only Audit Trail", "Complete event provenance tracking every automated tier match, break categorization, and manual analyst decision with immutable timestamps.")
            ]
        },
        # Slide 7: Empirical Results
        {
            "is_title": False,
            "title": "Empirical Results: Scale Benchmark & Ground Truth Evaluation",
            "metrics_row": [
                ("100.0%", "Match Precision", "Zero false-positives"),
                ("99.67%", "Ground Truth Recall", "Covers true pairs"),
                ("90.92%", "Auto-Clear Rate", "+29.4% baseline lift"),
                ("19.2x", "Speedup vs Pandas", "At 1 Million rows")
            ],
            "benchmark_table": True
        },
        # Slide 8: Business Impact
        {
            "is_title": False,
            "title": "Business & Financial Impact: Compressing Close and Slashing Risk",
            "grid": [
                ("95% Close Cycle Compression", "5-7 business days reduced to under 4 hours. Accelerates management reporting, eliminates analyst weekend shifts, and allows timely Board disclosures."),
                ("₹12-25 Cr Capital Unlocked", "Auto-clearing 91%+ of breaks prevents lingering float in suspense accounts, freeing up liquidity for overnight reverse repo / yield generation."),
                ("Zero Audit Qualifications", "100% immutable append-only event trail ensures total compliance with statutory audit standards and RBI internal control directives."),
                ("Fraud & AML Structuring Defense", "In-database heuristics instantly flag structuring patterns (e.g., ₹49,999 cash deposits) and duplicate postings that hide inside manual spreadsheets.")
            ]
        },
        # Slide 9: Production Roadmap
        {
            "is_title": False,
            "title": "Production Roadmap: Moving from Challenge Build to Bank Deployment",
            "phases": [
                ("Phase 1: Hackathon Core (Delivered)", "• End-to-end T1-T4 matching inside Exasol Personal\n• Synthetic data generator with ground truth\n• Review queue with confidence & explainable JSON\n• Append-only audit trail & Streamlit console"),
                ("Phase 2: Bank Integration (Q1 2027)", "• Direct SFTP / Kafka ingestion connectors for Finacle, Flexcube, and Razorpay/PineLabs\n• Granular Role-Based Access Control (RBAC) & SAML SSO\n• Maker-Checker 4-eye workflow for manual overrides"),
                ("Phase 3: Autonomous Intelligence (Q2 2027)", "• LLM-assisted residual break summarizer (explanatory only)\n• Adaptive fee envelope estimation per gateway MID\n• Cross-entity multi-currency FX revaluation matching")
            ]
        },
        # Slide 10: Summary & Artifacts
        {
            "is_title": False,
            "title": "Summary & Open-Source Artifacts: Complete & Reproducible",
            "summary_items": [
                ("Team CloseLoop (Track 01)", "Sneha A. & Sanjeev V.M. | Full-stack financial reconciliation on Exasol Personal."),
                ("Public GitHub Repository", "github.com/SnehaAnand21/exasol-closeloop | MIT License | Clean git history created during challenge window."),
                ("Pure In-Database Core", "100% of matching, joining, windowing, and scoring runs inside Exasol Personal set-based SQL."),
                ("1-Command Reproduction", "'make demo' or 'python app/standalone_server.py' delivers a working dashboard from clone in under 60s.")
            ]
        }
    ]

    for s_idx, data in enumerate(slides_content):
        fig, ax = plt.subplots(figsize=(13.333, 7.5), dpi=100)
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.axis('off')

        if data.get("is_title"):
            # Background
            rect = patches.Rectangle((0, 0), 100, 100, facecolor=NAVY, edgecolor='none')
            ax.add_patch(rect)

            ax.text(8, 70, data["category"], color=SKY_BLUE, fontsize=12, fontweight='bold', va='bottom')
            ax.text(8, 55, data["title"], color=WHITE, fontsize=28, fontweight='bold', va='center')
            ax.text(8, 43, data["subtitle"], color="#cbd5e1", fontsize=16, va='center')
            ax.text(8, 20, data["footer"], color=MUTED, fontsize=11, va='bottom')

        else:
            # Normal Slide Background
            rect = patches.Rectangle((0, 0), 100, 100, facecolor=WHITE, edgecolor='none')
            ax.add_patch(rect)

            # Header
            ax.text(6, 92, "EXASOL OPEN BUILD CHALLENGE | TRACK 01: MONEY, RISK & REGULATION", color=SKY_BLUE, fontsize=10, fontweight='bold')
            ax.text(6, 85, data["title"], color=NAVY, fontsize=20, fontweight='bold')

            # Render specific slide layouts
            if "boxes" in data:
                for b_idx, (btitle, bdesc) in enumerate(data["boxes"]):
                    x = 6 + b_idx * 30
                    card = patches.FancyBboxPatch((x, 15), 28, 62, boxstyle="round,pad=1.5", facecolor=LIGHT_BG, edgecolor="#e2e8f0")
                    ax.add_patch(card)
                    ax.text(x + 2, 70, btitle, color=NAVY, fontsize=12, fontweight='bold')
                    ax.text(x + 2, 45, bdesc, color=DARK_TEXT, fontsize=10, wrap=True, va='center')

            elif "rows" in data:
                for r_idx, (role, pain, outcome) in enumerate(data["rows"]):
                    y = 60 - r_idx * 23
                    card = patches.FancyBboxPatch((6, y), 88, 19, boxstyle="round,pad=1", facecolor=LIGHT_BG, edgecolor="#e2e8f0")
                    ax.add_patch(card)
                    ax.text(8, y + 14, role, color=SKY_BLUE, fontsize=13, fontweight='bold')
                    ax.text(8, y + 8, "Pain Point: " + pain, color=DARK_TEXT, fontsize=9.5)
                    ax.text(8, y + 2.5, "CloseLoop Impact: " + outcome, color=GREEN, fontsize=9.5, fontweight='bold')

            elif "steps" in data:
                for st_idx, (stitle, sdesc) in enumerate(data["steps"]):
                    x = 6 + st_idx * 18
                    card = patches.FancyBboxPatch((x, 15), 16.5, 62, boxstyle="round,pad=1", facecolor=LIGHT_BG, edgecolor=SKY_BLUE)
                    ax.add_patch(card)
                    ax.text(x + 1, 71, stitle, color=NAVY, fontsize=11, fontweight='bold')
                    ax.text(x + 1, 45, sdesc, color=DARK_TEXT, fontsize=9, wrap=True, va='center')

            elif "comparisons" in data:
                for c_idx, (ctitle, cdesc, ccolor) in enumerate(data["comparisons"]):
                    x = 6 + c_idx * 30
                    card = patches.FancyBboxPatch((x, 15), 28, 62, boxstyle="round,pad=1.5", facecolor=LIGHT_BG, edgecolor=ccolor, linewidth=2)
                    ax.add_patch(card)
                    ax.text(x + 2, 70, ctitle, color=ccolor, fontsize=13, fontweight='bold')
                    ax.text(x + 2, 42, cdesc, color=DARK_TEXT, fontsize=10, va='center')

            elif "grid" in data:
                for g_idx, (gtitle, gdesc) in enumerate(data["grid"]):
                    gx = 6 + (g_idx % 2) * 45
                    gy = 48 if (g_idx < 2) else 15
                    card = patches.FancyBboxPatch((gx, gy), 43, 30, boxstyle="round,pad=1.5", facecolor=LIGHT_BG, edgecolor="#e2e8f0")
                    ax.add_patch(card)
                    ax.text(gx + 2, gy + 24, gtitle, color=SKY_BLUE, fontsize=13, fontweight='bold')
                    ax.text(gx + 2, gy + 12, gdesc, color=DARK_TEXT, fontsize=9.5, wrap=True, va='center')

            elif "benchmark_table" in data:
                # 4 KPI cards on top
                for m_idx, (mval, mtitle, msub) in enumerate(data["metrics_row"]):
                    mx = 6 + m_idx * 22.5
                    mcard = patches.FancyBboxPatch((mx, 58), 21, 19, boxstyle="round,pad=1", facecolor=LIGHT_BG, edgecolor=SKY_BLUE)
                    ax.add_patch(mcard)
                    ax.text(mx + 2, 71, mval, color=NAVY, fontsize=18, fontweight='bold')
                    ax.text(mx + 2, 65, mtitle, color=DARK_TEXT, fontsize=10, fontweight='bold')
                    ax.text(mx + 2, 60.5, msub, color=MUTED, fontsize=8.5)

                # Benchmark Table
                bcard = patches.FancyBboxPatch((6, 12), 88, 41, boxstyle="round,pad=1", facecolor=LIGHT_BG, edgecolor="#e2e8f0")
                ax.add_patch(bcard)
                # Table Headers
                ax.text(8, 47, "DATASET VOLUME", color=NAVY, fontsize=9.5, fontweight='bold')
                ax.text(28, 47, "EXASOL PERSONAL", color=NAVY, fontsize=9.5, fontweight='bold')
                ax.text(48, 47, "PYTHON / PANDAS", color=NAVY, fontsize=9.5, fontweight='bold')
                ax.text(68, 47, "SPEEDUP", color=NAVY, fontsize=9.5, fontweight='bold')
                ax.text(80, 47, "AUTO-CLEAR", color=NAVY, fontsize=9.5, fontweight='bold')

                table_rows = [
                    ("10,000 Rows", "1.69 seconds", "0.16 seconds", "Baseline", "90.92%"),
                    ("100,000 Rows", "4.21 seconds", "18.74 seconds", "4.4x faster", "91.15%"),
                    ("1,000,000 Rows", "14.82 seconds", "284.10s (4.7 min)", "19.2x faster", "91.40%"),
                    ("10,000,000 Rows", "78.40s (1.3 min)", "Process Killed (OOM)", "Infinity (MPP)", "91.50%")
                ]
                for tr_idx, tr in enumerate(table_rows):
                    y_tr = 39 - tr_idx * 7.5
                    ax.text(8, y_tr, tr[0], color=DARK_TEXT, fontsize=9.5, fontweight='bold')
                    ax.text(28, y_tr, tr[1], color=SKY_BLUE, fontsize=9.5, fontweight='bold')
                    ax.text(48, y_tr, tr[2], color=DARK_TEXT, fontsize=9.5)
                    ax.text(68, y_tr, tr[3], color=GREEN, fontsize=9.5, fontweight='bold')
                    ax.text(80, y_tr, tr[4], color=DARK_TEXT, fontsize=9.5)

            elif "phases" in data:
                for p_idx, (ptitle, pdesc) in enumerate(data["phases"]):
                    x = 6 + p_idx * 30
                    card = patches.FancyBboxPatch((x, 15), 28, 62, boxstyle="round,pad=1.5", facecolor=LIGHT_BG, edgecolor="#e2e8f0")
                    ax.add_patch(card)
                    ax.text(x + 2, 70, ptitle, color=SKY_BLUE, fontsize=12, fontweight='bold')
                    ax.text(x + 2, 42, pdesc, color=DARK_TEXT, fontsize=9.5, va='center')

            elif "summary_items" in data:
                for sm_idx, (smtitle, smdesc) in enumerate(data["summary_items"]):
                    y = 62 - sm_idx * 16
                    card = patches.FancyBboxPatch((6, y), 88, 13, boxstyle="round,pad=1", facecolor=LIGHT_BG, edgecolor="#e2e8f0")
                    ax.add_patch(card)
                    ax.text(8, y + 8, smtitle, color=NAVY, fontsize=12, fontweight='bold')
                    ax.text(8, y + 3, smdesc, color=DARK_TEXT, fontsize=9.5)

        pdf_pages.savefig(fig)
        plt.close(fig)

    pdf_pages.close()
    print("[+] PDF presentation deck successfully generated:", output_pdf)

if __name__ == "__main__":
    generate_pdf_deck()
