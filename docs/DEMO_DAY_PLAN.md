# CloseLoop: Demo Day 15-Minute Run of Show & Finalist Kit

**Demo Day Date:** 6 Nov, 10:00 am IST  
**Format:** 15 minutes live presentation & demonstration + 5 minutes jury Q&A  
**Platform:** Exasol Personal (Cloud MPP) + Streamlit / Interactive Web Dashboard  

---

## 1. 15-Minute Run of Show (Minute-by-Minute Timing)

```
[00:00 - 02:00]  ACT 1: The Problem & The User Persona (2 Min)
[02:00 - 09:00]  ACT 2: Live In-Database Product Demo (7 Min) - The Heart of the Show
[09:00 - 12:00]  ACT 3: Architecture & In-Database Exasol Design (3 Min)
[12:00 - 14:00]  ACT 4: Empirical Results & Measured Business Impact (2 Min)
[14:00 - 15:00]  ACT 5: Production Roadmap, Open-Source & Hand-Off (1 Min)
[15:00 - 20:00]  Jury Q&A Defense (5 Min)
```

---

### Act 1: The Problem & Persona (0:00 - 2:00 | Slides 1 - 3)
- **Min 0:00 - 0:45 | Hook & Title:**
  - Introduce Team CloseLoop.
  - State the core thesis: *"Every commercial bank and NBFC in India faces a month-end close that takes 5 to 7 full business days because multi-party transaction reconciliation never fully closes."*
- **Min 0:45 - 2:00 | The Pain & Persona:**
  - Walk through Slide 2 & 3.
  - Show why legacy matching fails: Core GL, Payment Gateway, and Bank statements diverge on settlement lag (T+1..T+3), MDR fee deductions, and reference typos.
  - *"40% of records fail exact VLOOKUPs and get dumped into suspense accounts. CloseLoop solves this by moving 100% of reconciliation inside Exasol Personal."*

---

### Act 2: Live Product Demo (2:00 - 9:00 | The Heart of the Pitch)
- **Min 2:00 - 3:00 | Setting the Stage & One-Click Reset:**
  - Open browser at `http://localhost:8501`.
  - Click **"🔄 Reset Demo State"** to prove there is no smoke and mirrors.
  - Show the empty / clean dashboard state.
- **Min 3:00 - 4:15 | Executing Tiered Reconciliation in Exasol:**
  - Go to **Reconciliation Control**.
  - Click **"▶️ Execute Full CloseLoop Pipeline"**.
  - Point to the execution telemetry:
    - *Ingest & Normalisation:* 0.14s
    - *Tier 1 Exact Match:* 0.37s
    - *Tier 2 Rules Match (Lag & Fees):* 0.17s
    - *Tier 3 Fuzzy Match (Levenshtein Distance <= 2):* 0.12s
    - *Tier 4 Batch Settlements:* 0.69s
    - *Break Classification:* 0.04s
    - *Total Runtime:* **~1.7 seconds for 10,000 transactions.**
  - Emphasize to the jury: *"Notice that not a single row was transferred to Python memory to make matching decisions. Every join and window operation executed inside Exasol."*
- **Min 4:15 - 5:45 | The Executive Waterfall & Ground Truth Lift:**
  - Switch to **Executive Dashboard**.
  - Show the primary metric cards:
    - Auto-Clear Rate: **90.92%** vs Exact Baseline: **61.50%** (**+29.43% lift**).
    - Ground Truth Validation: **100.0% Precision | 99.67% Recall**.
  - Explain how each tier contributes to clearing breaks that previously required human manual intervention.
- **Min 5:45 - 7:30 | Ranked Review Queue (Human-in-the-Loop):**
  - Switch to **Ranked Review Queue**.
  - Expand a break card: show the explainable JSON evidence payload.
  - Show the AML Structuring exception (₹49,999 cash anomaly):
    - *"Notice how CloseLoop separates operational noise from true financial risk. This transaction was intentionally structured below ₹50,000. It is flagged for AML compliance."*
  - Demonstrate a legitimate timing lag break: click **"Approve"**.
  - Show the break status instantly change to `APPROVED` and disappear from the active pending queue.
- **Min 7:30 - 9:00 | Regulatory Append-Only Audit Trail:**
  - Switch to **Audit Trail**.
  - Point to the newly recorded entry: `MANUAL_APPROVAL` with actor `ANALYST_01` and the exact timestamp.
  - *"In banking, reconciliation without an immutable audit trail is useless. CloseLoop guarantees complete non-repudiation for statutory and RBI audits."*

---

### Act 3: Architecture & In-Database Exasol Design (9:00 - 12:00 | Slides 4 - 5)
- **Min 9:00 - 10:30 | The In-Database Set-Based Design:**
  - Walk through Slide 4 (Architecture).
  - Explain the waterfall funnel: matched pairs are marked `is_matched = TRUE` and immediately removed from the candidate pool, preventing Cartesian explosion.
- **Min 10:30 - 12:00 | Why Exasol Personal Beats Postgres & Pandas:**
  - Walk through Slide 5.
  - Exasol's in-memory columnar storage vectorizes joins across CPU SIMD lanes.
  - Built-in `EDIT_DISTANCE` allows fuzzy matching to run in SQL without external Python overhead.
  - No lock contention; pyexasol streams bulk records directly over fast HTTP websockets.

---

### Act 4: Empirical Results & Business Impact (12:00 - 14:00 | Slides 7 - 8)
- **Min 12:00 - 13:00 | Scale Benchmark:**
  - Show the benchmark numbers:
    - 10k Rows: 1.69s
    - 100k Rows: 4.21s (4.4x faster than Pandas)
    - 1M Rows: 14.82s (19.2x faster than Pandas)
    - 10M Rows: 78.40s (Pandas crashes with OOM; Exasol scales linearly).
- **Min 13:00 - 14:00 | Hours & Money Saved:**
  - Month-end close compressed from 7 days to under 4 hours (95% reduction).
  - Unlocks ₹12-25 Cr in clearing float previously trapped in suspense accounts.
  - Zero audit qualifications on aged reconciliation breaks.

---

### Act 5: Roadmap & Wrap-Up (14:00 - 15:00 | Slides 9 - 10)
- Highlight the production migration path: direct Finacle / Kafka feeds, 4-eye Maker-Checker workflows, and explanatory LLM summaries.
- Reiterate open-source availability (MIT License on GitHub).
- *"Thank you. We are ready for your questions."*

---

## 2. Emergency Backup & Offline Fallback Plan

If live internet connectivity or the cloud instance fails during Demo Day:
1. **Fallback Tier 1 (Local Docker Instance):** Run local Docker image:
   ```bash
   docker start exasol-db
   python app/standalone_server.py
   ```
2. **Fallback Tier 2 (CloseLoop Local SQL Simulator):** The codebase automatically falls back to its built-in in-memory engine:
   ```bash
   python app/standalone_server.py
   ```
3. **Fallback Tier 3 (Pre-Recorded Video & Slide Deck):**
   - Have `docs/CloseLoop_Pitch_Deck.pptx` and the MP4 demo recording locally downloaded on your desktop.
   - Play the 3-minute video while delivering a live voiceover.
