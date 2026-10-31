# CloseLoop: Step-by-Step Reproduction Guide

This guide provides exact commands and **expected terminal outputs** so evaluators and hackathon judges can verify CloseLoop from clone to running console in under 2 minutes.

---

## Step 1: Clone and Inspect Directory Structure

```bash
git clone https://github.com/exasol-closeloop/closeloop.git
cd closeloop
ls -la
```

**Expected Output:**
```
.env.example
Makefile
docker-compose.yml
requirements.txt
LICENSE
README.md
app/
data_gen/
docs/
sql/
src/
tests/
```

---

## Step 2: Generate Synthetic Feeds with Ground Truth

Generate 10,000 realistic multi-party transactions:
```bash
python data_gen/generate_data.py --scale 10000 --output data
```

**Expected Terminal Output:**
```
[*] Generating 10000 transaction records into 'data' (Seed: 42)...
[+] Successfully generated:
    - Core Ledger:       9,818 rows -> data/core_ledger.csv
    - Payment Gateway:   7,218 rows -> data/payment_gateway.csv
    - Bank Statement:    9,243 rows -> data/bank_statement.csv
    - Ground Truth:      9,902 labels -> data/ground_truth_labels.csv
```

---

## Step 3: Run Full In-Database Reconciliation Pipeline

Execute the end-to-end multi-tier matching and evaluation:
```bash
python tests/run_verification.py
```

**Expected Terminal Output:**
```
=======================================================
 CloseLoop: Starting Reconciliation Run: RUN_...
 Engine: Exasol Personal (or CloseLoop In-Memory Simulator)
=======================================================
[*] Ingesting raw feeds from data...
[+] Bulk loaded 9,818 rows into raw_core_ledger
[+] Bulk loaded 7,218 rows into raw_payment_gateway
[+] Bulk loaded 9,243 rows into raw_bank_statement
[+] Bulk loaded 9,902 rows into ground_truth_labels
[*] Normalising references, dates, and amounts...
[+] Normalisation completed in 0.143s
[*] Running Tier 1 (Exact Match: Ref + Amount + Date)...
[+] Tier 1 matched 6,038 records in 0.376s
[*] Running Tier 2 (Rules Match: Lag T+1..T+3, MDR Fees, Rounding)...
[+] Tier 2 matched 1,820 records in 0.171s
[*] Running Tier 3 (Fuzzy Match: Levenshtein Distance <= 2 on clean_ref)...
[+] Tier 3 matched 948 records in 0.127s
[*] Running Tier 4 (Many-to-One Batch Settlements)...
[+] Tier 4 matched 121 settlement batches in 0.697s
[*] Classifying residual breaks and exceptions...
[+] Break classification completed (739 breaks) in 0.042s
=======================================================
[+] CloseLoop Pipeline Finished in 1.729s
=======================================================

--- EXECUTIVE SUMMARY KPIS ---
Total Ledger Records:     9,818
Total Bank Records:       9,243
Tier 1 Exact Matches:     6,038
Tier 2 Rules Matches:     1,820
Tier 3 Fuzzy Matches:     948
Tier 4 Batch Matches:     121
Total Matches:            8,927
Total Residual Breaks:    739
Exact Baseline Rate:      61.5%
CloseLoop Auto-Clear:     90.92%
Auto-Clear Rate Lift:     +29.43%

--- GROUND TRUTH EVALUATION ---
Match Precision:          100.0%
Match Recall:             99.67%
Match F1 Score:           99.83%

Tier-by-Tier Recall:
  - BATCH_SETTLEMENT (TIER_4): 562/593 (94.77%)
  - EXACT_MATCH (TIER_1): 6038/6038 (100.0%)
  - FEE_VARIATION (TIER_2): 587/587 (100.0%)
  - ROUNDING_TOLERANCE (TIER_2): 636/636 (100.0%)
  - SETTLEMENT_LAG_T1 (TIER_2): 199/199 (100.0%)
  - SETTLEMENT_LAG_T2 (TIER_2): 212/212 (100.0%)
  - SETTLEMENT_LAG_T3 (TIER_2): 186/186 (100.0%)
  - TYPO_REF (TIER_3): 948/948 (100.0%)

Break Classification Accuracy:
  - DUPLICATE_ENTRY: 109/109 (100.0%)
  - MISSING_LEDGER_ENTRY: 102/102 (100.0%)
  - SUSPECTED_FRAUD_PATTERN: 91/91 (100.0%)
  - TIMING_LAG: 109/109 (100.0%)
  - WRONG_AMOUNT: 83/92 (90.22%)
```

---

## Step 4: Run the Complete Master Test Suite

Verify all 15 unit and integration test assertions:
```bash
python tests/run_all_tests.py
```

**Expected Terminal Output:**
```
=======================================================
 Running CloseLoop Master Test Suite
=======================================================

test_audit_entries_exist (test_audit_trail.TestAuditTrail) ... ok
test_manual_approval_audit (test_audit_trail.TestAuditTrail) ... ok
test_pipeline_lifecycle_events (test_audit_trail.TestAuditTrail) ... ok
test_break_categories_present (test_break_classifier.TestBreakClassifier) ... ok
test_evidence_payload_json (test_break_classifier.TestBreakClassifier) ... ok
test_file_creation (test_data_generator.TestDataGenerator) ... ok
test_row_counts (test_data_generator.TestDataGenerator) ... ok
test_repeated_runs_deterministic (test_idempotency.TestIdempotency) ... ok
test_autoclear_lift (test_precision_recall.TestPrecisionRecall) ... ok
test_precision_threshold (test_precision_recall.TestPrecisionRecall) ... ok
test_recall_threshold (test_precision_recall.TestPrecisionRecall) ... ok
test_tier_1_exact_matching (test_tiered_matching.TestTieredMatching) ... ok
test_tier_2_rules_matching (test_tiered_matching.TestTieredMatching) ... ok
test_tier_3_fuzzy_matching (test_tiered_matching.TestTieredMatching) ... ok
test_tier_4_batch_settlement (test_tiered_matching.TestTieredMatching) ... ok

----------------------------------------------------------------------
Ran 15 tests in 10.920s

OK

=======================================================
 Tests Run: 15
 Errors:    0
 Failures:  0
 Status:    ALL PASSED [PASS]
=======================================================
```

---

## Step 5: Launch the Interactive Web Dashboard

To launch the zero-dependency interactive web dashboard:
```bash
python app/standalone_server.py
```
Or if Streamlit is installed:
```bash
streamlit run app/app.py
```

Open your browser to:
👉 `http://localhost:8501`

**Interactive Actions to Test in the Browser:**
1. **Executive Dashboard:** Inspect the 4 KPI cards and ground truth lift statistics.
2. **Review Queue:** Scroll down to exceptions. Expand any break card. Click `Approve` or `Reject`. Notice the status updates immediately.
3. **Audit Trail:** Check the audit table; see your manual approval recorded with actor `ANALYST_01` and an immutable timestamp.
4. **Trigger Live Pipeline:** Click `▶️ Run Full Pipeline` in the sidebar and watch the database reconcile live.
5. **Reset Demo State:** Click `🔄 Reset State` in the sidebar to reset the database to pristine initial state.

---

## Step 6: Run Scale Benchmark (Exasol vs Pandas)

```bash
python src/benchmark.py --scale 10000
```
This runs synthetic generation, CloseLoop in-database execution, and Python baseline comparison, printing real measured timings.
