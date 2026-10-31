"""
CloseLoop: Core Reconciliation Pipeline Orchestrator
===================================================
Executes tiered matching and break classification entirely inside Exasol SQL.
Python acts as a thin orchestration and telemetry layer.
"""

import os
import time
from datetime import datetime
from src.exasol_engine import ExasolEngine
from src.config import Config, DATA_DIR, SQL_DIR

class ReconciliationPipeline:
    def __init__(self, engine=None):
        self.engine = engine or ExasolEngine()
        self.run_id = f"RUN_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def load_raw_data(self, data_dir=None):
        """Step 1: Ingest 3 sources plus ground truth into staging tables."""
        d_dir = data_dir or DATA_DIR
        print(f"[*] Ingesting raw feeds from {d_dir}...")
        
        gl_csv = os.path.join(d_dir, "core_ledger.csv")
        pg_csv = os.path.join(d_dir, "payment_gateway.csv")
        bnk_csv = os.path.join(d_dir, "bank_statement.csv")
        gt_csv = os.path.join(d_dir, "ground_truth_labels.csv")

        # Clear staging and active run state
        self.engine.execute("DELETE FROM raw_core_ledger;")
        self.engine.execute("DELETE FROM raw_payment_gateway;")
        self.engine.execute("DELETE FROM raw_bank_statement;")
        self.engine.execute("DELETE FROM reconciliation_matches;")
        self.engine.execute("DELETE FROM reconciliation_breaks;")
        if os.path.exists(gt_csv):
            self.engine.execute("DELETE FROM ground_truth_labels;")

        self.engine.bulk_load_csv("raw_core_ledger", gl_csv)
        self.engine.bulk_load_csv("raw_payment_gateway", pg_csv)
        self.engine.bulk_load_csv("raw_bank_statement", bnk_csv)
        if os.path.exists(gt_csv):
            self.engine.bulk_load_csv("ground_truth_labels", gt_csv)

        # Log pipeline start in audit log
        self.engine.execute(
            "INSERT INTO reconciliation_audit_log (event_id, run_id, action_type, target_entity, entity_id, rule_applied, confidence, actor, details_json) "
            "VALUES (?, ?, 'RUN_STARTED', 'PIPELINE', ?, 'INGEST_FEEDS', 1.0, 'SYSTEM_CLOSELOOP', ?)",
            [f"AUD_START_{self.run_id}", self.run_id, self.run_id, '{"status": "Feeds loaded successfully"}']
        )

    def normalise_data(self):
        """Step 2: Normalise references, dates, and amounts using set-based SQL."""
        print("[*] Normalising references, dates, and amounts...")
        t0 = time.time()
        self.engine.execute("DELETE FROM norm_ledger;")
        self.engine.execute("DELETE FROM norm_gateway;")
        self.engine.execute("DELETE FROM norm_bank;")

        # Normalise Ledger
        self.engine.execute("""
        INSERT INTO norm_ledger (
            item_id, source_system, clean_ref, raw_ref, txn_date, value_date,
            amount, currency, direction, account_no, narration, is_matched, match_id, run_id
        )
        SELECT
            ledger_id, 'CORE_LEDGER',
            UPPER(REGEXP_REPLACE(REGEXP_REPLACE(UPPER(TRIM(reference_no)), '^(REF#?|TXN[:\\-]?|UTR[:\\-]?|INV[:\\-/]?|CHQ[:\\-]?|PG[:\\-]?|[#:\\-/ ])+', ''), '^(REF#?|TXN[:\\-]?|UTR[:\\-]?|INV[:\\-/]?|CHQ[:\\-]?|PG[:\\-]?|[#:\\-/ ])+', '')),
            reference_no,
            txn_date,
            COALESCE(NULLIF(value_date, ''), txn_date),
            CAST(amount AS REAL),
            COALESCE(currency, 'INR'),
            UPPER(TRIM(dr_cr)),
            account_no, description, 0, NULL, ?
        FROM raw_core_ledger;
        """, [self.run_id])

        # Normalise Gateway
        self.engine.execute("""
        INSERT INTO norm_gateway (
            item_id, source_system, clean_ref, raw_ref, auth_date, settlement_date,
            gross_amount, fee_amount, net_amount, status, batch_id, is_matched, match_id, run_id
        )
        SELECT
            pg_txn_id, 'PAYMENT_GATEWAY',
            UPPER(REGEXP_REPLACE(REGEXP_REPLACE(UPPER(TRIM(gateway_ref)), '^(REF#?|TXN[:\\-]?|UTR[:\\-]?|INV[:\\-/]?|CHQ[:\\-]?|PG[:\\-]?|[#:\\-/ ])+', ''), '^(REF#?|TXN[:\\-]?|UTR[:\\-]?|INV[:\\-/]?|CHQ[:\\-]?|PG[:\\-]?|[#:\\-/ ])+', '')),
            gateway_ref,
            auth_date,
            COALESCE(NULLIF(settlement_date, ''), auth_date),
            CAST(gross_amount AS REAL),
            CAST(COALESCE(NULLIF(fee_amount, ''), '0.00') AS REAL),
            CAST(COALESCE(NULLIF(net_amount, ''), gross_amount) AS REAL),
            UPPER(TRIM(status)),
            batch_id, 0, NULL, ?
        FROM raw_payment_gateway;
        """, [self.run_id])

        # Normalise Bank Statement
        self.engine.execute("""
        INSERT INTO norm_bank (
            item_id, source_system, clean_ref, raw_ref, post_date, value_date,
            amount, direction, narration, is_matched, match_id, run_id
        )
        SELECT
            bank_txn_id, 'BANK_STATEMENT',
            UPPER(REGEXP_REPLACE(REGEXP_REPLACE(UPPER(TRIM(cheque_ref)), '^(REF#?|TXN[:\\-]?|UTR[:\\-]?|INV[:\\-/]?|CHQ[:\\-]?|PG[:\\-]?|[#:\\-/ ])+', ''), '^(REF#?|TXN[:\\-]?|UTR[:\\-]?|INV[:\\-/]?|CHQ[:\\-]?|PG[:\\-]?|[#:\\-/ ])+', '')),
            cheque_ref,
            post_date,
            COALESCE(NULLIF(value_date, ''), post_date),
            CASE 
                WHEN deposit_amt IS NOT NULL AND TRIM(deposit_amt) != '' AND CAST(deposit_amt AS REAL) > 0 
                    THEN CAST(deposit_amt AS REAL)
                WHEN withdrawal_amt IS NOT NULL AND TRIM(withdrawal_amt) != '' AND CAST(withdrawal_amt AS REAL) > 0 
                    THEN -CAST(withdrawal_amt AS REAL)
                ELSE 0.00
            END,
            CASE 
                WHEN deposit_amt IS NOT NULL AND TRIM(deposit_amt) != '' AND CAST(deposit_amt AS REAL) > 0 THEN 'CR'
                ELSE 'DR'
            END,
            narration, 0, NULL, ?
        FROM raw_bank_statement;
        """, [self.run_id])

        duration = time.time() - t0
        print(f"[+] Normalisation completed in {duration:.3f}s")
        return duration

    def run_tier_1_exact(self):
        """Step 3: Tier 1 Exact Match (Ref + Amount + Date)."""
        print("[*] Running Tier 1 (Exact Match: Ref + Amount + Date)...")
        t0 = time.time()

        # Find candidates
        candidates = self.engine.fetch_all("""
        SELECT 
            'M1_' || l.item_id || '_' || b.item_id AS match_id,
            l.item_id AS ledger_item_id,
            b.item_id AS bank_item_id,
            g.item_id AS gateway_item_id,
            l.amount AS match_amount
        FROM norm_ledger l
        INNER JOIN norm_bank b
            ON l.clean_ref = b.clean_ref
           AND l.amount = b.amount
           AND l.txn_date = b.post_date
           AND l.is_matched = 0
           AND b.is_matched = 0
           AND LENGTH(l.clean_ref) >= 6
        LEFT JOIN norm_gateway g
            ON l.clean_ref = g.clean_ref
           AND l.amount = g.gross_amount
           AND g.is_matched = 0;
        """)

        # Filter 1-to-1 unique matches
        seen_ledger, seen_bank = set(), set()
        matched = []
        for c in candidates:
            lid = c["ledger_item_id"]
            bid = c["bank_item_id"]
            if lid not in seen_ledger and bid not in seen_bank:
                seen_ledger.add(lid)
                seen_bank.add(bid)
                matched.append(c)

        for m in matched:
            mid = m["match_id"]
            lid = m["ledger_item_id"]
            bid = m["bank_item_id"]
            gid = m["gateway_item_id"]
            amt = m["match_amount"]

            self.engine.execute("""
            INSERT INTO reconciliation_matches (
                match_id, run_id, match_tier, ledger_item_id, bank_item_id,
                gateway_item_id, match_amount, variance_amount, confidence,
                rule_signature, explanation
            ) VALUES (?, ?, 'TIER_1_EXACT', ?, ?, ?, ?, 0.00, 1.0000, 'EXACT_REF_AMT_DATE', 'Exact match on reference, amount, and date')
            """, [mid, self.run_id, lid, bid, gid, amt])

            self.engine.execute("UPDATE norm_ledger SET is_matched = 1, match_id = ? WHERE item_id = ?", [mid, lid])
            self.engine.execute("UPDATE norm_bank SET is_matched = 1, match_id = ? WHERE item_id = ?", [mid, bid])
            if gid:
                self.engine.execute("UPDATE norm_gateway SET is_matched = 1, match_id = ? WHERE item_id = ?", [mid, gid])

            # Audit
            self.engine.execute("""
            INSERT INTO reconciliation_audit_log (event_id, run_id, action_type, target_entity, entity_id, rule_applied, confidence, actor, details_json)
            VALUES (?, ?, 'TIER_MATCH', 'MATCH', ?, 'TIER_1_EXACT', 1.0000, 'SYSTEM_CLOSELOOP', ?)
            """, [f"AUD_{mid}", self.run_id, mid, f'{{"tier": "T1", "ledger_id": "{lid}", "bank_id": "{bid}"}}'])

        duration = time.time() - t0
        print(f"[+] Tier 1 matched {len(matched):,} records in {duration:.3f}s")
        return {"matched_count": len(matched), "duration": duration}

    def run_tier_2_rules(self):
        """Step 4: Tier 2 Rules Match (Settlement Lag T+1..T+3, Fees, Rounding <= 0.05)."""
        print("[*] Running Tier 2 (Rules Match: Lag T+1..T+3, MDR Fees, Rounding)...")
        t0 = time.time()

        candidates = self.engine.fetch_all("""
        SELECT
            'M2_' || l.item_id || '_' || b.item_id AS match_id,
            l.item_id AS ledger_item_id,
            b.item_id AS bank_item_id,
            g.item_id AS gateway_item_id,
            l.amount AS ledger_amount,
            b.amount AS bank_amount,
            g.fee_amount AS fee_amount,
            l.txn_date,
            b.post_date
        FROM norm_ledger l
        INNER JOIN norm_bank b
            ON l.clean_ref = b.clean_ref
           AND l.is_matched = 0
           AND b.is_matched = 0
           AND LENGTH(l.clean_ref) >= 6
        LEFT JOIN norm_gateway g
            ON l.clean_ref = g.clean_ref
           AND g.is_matched = 0
        WHERE 
            -- Rule 2A: Settlement lag T+1 to T+3 with exact amount
            (b.post_date >= l.txn_date AND b.post_date <= ADD_DAYS(l.txn_date, 3) AND l.amount = b.amount)
            OR
            -- Rule 2B: Fee deduction
            (g.item_id IS NOT NULL AND (b.amount = g.net_amount OR ABS(b.amount - (l.amount - g.fee_amount)) < 0.01))
            OR
            -- Rule 2C: Penny rounding tolerance <= 0.05
            (ABS(l.amount - b.amount) <= 0.05 AND b.post_date >= l.txn_date AND b.post_date <= ADD_DAYS(l.txn_date, 2));
        """)

        seen_ledger, seen_bank = set(), set()
        matched = []
        for c in candidates:
            lid = c["ledger_item_id"]
            bid = c["bank_item_id"]
            if lid not in seen_ledger and bid not in seen_bank:
                seen_ledger.add(lid)
                seen_bank.add(bid)

                lamt = float(c["ledger_amount"])
                bamt = float(c["bank_amount"])
                variance = round(lamt - bamt, 2)

                if c["fee_amount"] and abs(bamt - (lamt - float(c["fee_amount"]))) < 0.01:
                    sig = "RULE_MDR_FEE_DEDUCTION"
                    conf = 0.9600
                    exp = f"MDR fee variance accounted for: {c['fee_amount']} INR"
                elif abs(lamt - bamt) <= 0.05 and lamt != bamt:
                    sig = "RULE_ROUNDING_TOLERANCE"
                    conf = 0.9500
                    exp = f"Rounding difference resolved: {variance} INR"
                else:
                    sig = "RULE_SETTLEMENT_LAG_T_PLUS_N"
                    conf = 0.9800
                    exp = f"Settlement lag resolved (T+{c['post_date']})"

                matched.append({
                    "match_id": c["match_id"],
                    "ledger_item_id": lid,
                    "bank_item_id": bid,
                    "gateway_item_id": c["gateway_item_id"],
                    "match_amount": lamt,
                    "variance_amount": variance,
                    "confidence": conf,
                    "rule_signature": sig,
                    "explanation": exp
                })

        for m in matched:
            self.engine.execute("""
            INSERT INTO reconciliation_matches (
                match_id, run_id, match_tier, ledger_item_id, bank_item_id,
                gateway_item_id, match_amount, variance_amount, confidence,
                rule_signature, explanation
            ) VALUES (?, ?, 'TIER_2_RULES', ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                m["match_id"], self.run_id, m["ledger_item_id"], m["bank_item_id"],
                m["gateway_item_id"], m["match_amount"], m["variance_amount"],
                m["confidence"], m["rule_signature"], m["explanation"]
            ])
            self.engine.execute("UPDATE norm_ledger SET is_matched = 1, match_id = ? WHERE item_id = ?", [m["match_id"], m["ledger_item_id"]])
            self.engine.execute("UPDATE norm_bank SET is_matched = 1, match_id = ? WHERE item_id = ?", [m["match_id"], m["bank_item_id"]])
            if m["gateway_item_id"]:
                self.engine.execute("UPDATE norm_gateway SET is_matched = 1, match_id = ? WHERE item_id = ?", [m["match_id"], m["gateway_item_id"]])

            self.engine.execute("""
            INSERT INTO reconciliation_audit_log (event_id, run_id, action_type, target_entity, entity_id, rule_applied, confidence, actor, details_json)
            VALUES (?, ?, 'TIER_MATCH', 'MATCH', ?, ?, ?, 'SYSTEM_CLOSELOOP', ?)
            """, [f"AUD_{m['match_id']}", self.run_id, m["match_id"], m["rule_signature"], m["confidence"], f'{{"tier": "T2", "variance": {m["variance_amount"]}}}'])

        duration = time.time() - t0
        print(f"[+] Tier 2 matched {len(matched):,} records in {duration:.3f}s")
        return {"matched_count": len(matched), "duration": duration}

    def run_tier_3_fuzzy(self):
        """Step 5: Tier 3 Fuzzy Match (Levenshtein Edit Distance <= 2 + Amount Proximity)."""
        print("[*] Running Tier 3 (Fuzzy Match: Levenshtein Distance <= 2 on clean_ref)...")
        t0 = time.time()

        candidates = self.engine.fetch_all("""
        SELECT
            'M3_' || l.item_id || '_' || b.item_id AS match_id,
            l.item_id AS ledger_item_id,
            b.item_id AS bank_item_id,
            l.amount AS match_amount,
            l.clean_ref AS ledger_ref,
            b.clean_ref AS bank_ref,
            EDIT_DISTANCE(l.clean_ref, b.clean_ref) AS edit_dist
        FROM norm_ledger l
        INNER JOIN norm_bank b
            ON l.amount = b.amount
           AND b.post_date >= ADD_DAYS(l.txn_date, -1)
           AND b.post_date <= ADD_DAYS(l.txn_date, 3)
           AND l.is_matched = 0
           AND b.is_matched = 0
           AND LENGTH(l.clean_ref) >= 6
           AND LENGTH(b.clean_ref) >= 6
        WHERE EDIT_DISTANCE(l.clean_ref, b.clean_ref) <= 2;
        """)

        seen_ledger, seen_bank = set(), set()
        matched = []
        for c in candidates:
            lid = c["ledger_item_id"]
            bid = c["bank_item_id"]
            if lid not in seen_ledger and bid not in seen_bank:
                seen_ledger.add(lid)
                seen_bank.add(bid)
                dist = int(c["edit_dist"])
                conf = 0.9000 if dist == 1 else 0.8600
                matched.append({
                    "match_id": c["match_id"],
                    "ledger_item_id": lid,
                    "bank_item_id": bid,
                    "match_amount": c["match_amount"],
                    "confidence": conf,
                    "explanation": f"Fuzzy reference match (Edit distance {dist}: {c['ledger_ref']} ~ {c['bank_ref']})"
                })

        for m in matched:
            self.engine.execute("""
            INSERT INTO reconciliation_matches (
                match_id, run_id, match_tier, ledger_item_id, bank_item_id,
                gateway_item_id, match_amount, variance_amount, confidence,
                rule_signature, explanation
            ) VALUES (?, ?, 'TIER_3_FUZZY', ?, ?, NULL, ?, 0.00, ?, 'RULE_FUZZY_REF_EXACT_AMOUNT', ?)
            """, [
                m["match_id"], self.run_id, m["ledger_item_id"], m["bank_item_id"],
                m["match_amount"], m["confidence"], m["explanation"]
            ])
            self.engine.execute("UPDATE norm_ledger SET is_matched = 1, match_id = ? WHERE item_id = ?", [m["match_id"], m["ledger_item_id"]])
            self.engine.execute("UPDATE norm_bank SET is_matched = 1, match_id = ? WHERE item_id = ?", [m["match_id"], m["bank_item_id"]])

            self.engine.execute("""
            INSERT INTO reconciliation_audit_log (event_id, run_id, action_type, target_entity, entity_id, rule_applied, confidence, actor, details_json)
            VALUES (?, ?, 'TIER_MATCH', 'MATCH', ?, 'TIER_3_FUZZY', ?, 'SYSTEM_CLOSELOOP', ?)
            """, [f"AUD_{m['match_id']}", self.run_id, m["match_id"], m["confidence"], f'{{"tier": "T3", "confidence": {m["confidence"]}}}'])

        duration = time.time() - t0
        print(f"[+] Tier 3 matched {len(matched):,} records in {duration:.3f}s")
        return {"matched_count": len(matched), "duration": duration}

    def run_tier_4_batch(self):
        """Step 6: Tier 4 Batch Settlements (Many-to-One aggregations)."""
        print("[*] Running Tier 4 (Many-to-One Batch Settlements)...")
        t0 = time.time()

        # Group unmatched gateway items by batch_id
        batches = self.engine.fetch_all("""
        SELECT 
            batch_id,
            COUNT(*) AS item_count,
            ROUND(SUM(net_amount), 2) AS total_net,
            MIN(settlement_date) AS min_date,
            MAX(settlement_date) AS max_date
        FROM norm_gateway
        WHERE is_matched = 0 AND batch_id IS NOT NULL AND batch_id != ''
        GROUP BY batch_id
        HAVING COUNT(*) > 1;
        """)

        matched_count = 0
        for b in batches:
            bid = b["batch_id"]
            tot = float(b["total_net"])
            
            # Find bank deposit matching this exact batch sum
            bank_cand = self.engine.fetch_one("""
            SELECT item_id, amount, post_date FROM norm_bank
            WHERE is_matched = 0 AND ABS(amount - ?) < 0.01
              AND post_date >= ? AND post_date <= ADD_DAYS(?, 2);
            """, [tot, b["min_date"], b["max_date"]])

            if bank_cand:
                mid = f"M4_BATCH_{bid}_{bank_cand['item_id']}"
                self.engine.execute("""
                INSERT INTO reconciliation_matches (
                    match_id, run_id, match_tier, ledger_item_id, bank_item_id,
                    gateway_item_id, match_amount, variance_amount, confidence,
                    rule_signature, explanation
                ) VALUES (?, ?, 'TIER_4_BATCH', ?, ?, ?, ?, 0.00, 0.9400, 'RULE_MANY_TO_ONE_BATCH', ?)
                """, [
                    mid, self.run_id, f"BATCH_{bid}", bank_cand["item_id"],
                    bid, tot, f"Many-to-one batch payout: {b['item_count']} txns aggregated"
                ])
                self.engine.execute("UPDATE norm_bank SET is_matched = 1, match_id = ? WHERE item_id = ?", [mid, bank_cand["item_id"]])
                self.engine.execute("UPDATE norm_gateway SET is_matched = 1, match_id = ? WHERE batch_id = ?", [mid, bid])
                self.engine.execute("""
                UPDATE norm_ledger SET is_matched = 1, match_id = ?
                WHERE clean_ref IN (SELECT clean_ref FROM norm_gateway WHERE batch_id = ?);
                """, [mid, bid])

                matched_count += 1

        duration = time.time() - t0
        print(f"[+] Tier 4 matched {matched_count:,} settlement batches in {duration:.3f}s")
        return {"matched_count": matched_count, "duration": duration}

    def classify_breaks(self):
        """Step 7: Classify remaining breaks into structured categories with evidence strings."""
        print("[*] Classifying residual breaks and exceptions...")
        t0 = time.time()
        self.engine.execute("DELETE FROM reconciliation_breaks WHERE run_id = ?", [self.run_id])

        # 1. Duplicate entries in Ledger
        duplicates = self.engine.fetch_all("""
        SELECT l.item_id, l.raw_ref, l.txn_date, l.amount, dup.cnt
        FROM norm_ledger l
        INNER JOIN (
            SELECT clean_ref, amount, COUNT(*) as cnt
            FROM norm_ledger
            WHERE clean_ref IS NOT NULL AND clean_ref != ''
            GROUP BY clean_ref, amount HAVING COUNT(*) > 1
        ) dup ON l.clean_ref = dup.clean_ref AND l.amount = dup.amount
        WHERE l.is_matched = 0;
        """)
        for d in duplicates:
            bid = f"BRK_DUP_{d['item_id']}"
            ev = f'{{"reason": "Duplicate posting detected in GL", "occurrences": {d["cnt"]}, "amount": {d["amount"]}}}'
            self.engine.execute("""
            INSERT INTO reconciliation_breaks (
                break_id, run_id, source_system, item_id, ref_number, txn_date,
                amount, break_category, confidence_score, suggested_action, status, evidence_payload
            ) VALUES (?, ?, 'CORE_LEDGER', ?, ?, ?, ?, 'DUPLICATE_ENTRY', 0.9200, 'FLAG_REVERSAL_REQUIRED', 'PENDING_REVIEW', ?);
            """, [bid, self.run_id, d["item_id"], d["raw_ref"], d["txn_date"], d["amount"], ev])

        # 2. Timing Lags (Late month-end cutoff)
        timing = self.engine.fetch_all("""
        SELECT item_id, raw_ref, txn_date, amount
        FROM norm_ledger
        WHERE is_matched = 0
          AND item_id NOT IN (SELECT item_id FROM reconciliation_breaks WHERE run_id = ?)
          AND txn_date >= (SELECT ADD_DAYS(MAX(txn_date), -3) FROM norm_ledger);
        """, [self.run_id])
        for t in timing:
            bid = f"BRK_TIMING_{t['item_id']}"
            ev = f'{{"reason": "Late-cycle settlement cutoff", "txn_date": "{t["txn_date"]}", "cutoff_window_days": 3}}'
            self.engine.execute("""
            INSERT INTO reconciliation_breaks (
                break_id, run_id, source_system, item_id, ref_number, txn_date,
                amount, break_category, confidence_score, suggested_action, status, evidence_payload
            ) VALUES (?, ?, 'CORE_LEDGER', ?, ?, ?, ?, 'TIMING_LAG', 0.8900, 'HOLD_FOR_NEXT_CYCLE', 'PENDING_REVIEW', ?);
            """, [bid, self.run_id, t["item_id"], t["raw_ref"], t["txn_date"], t["amount"], ev])

        # 3. Wrong Amount / Transposition
        wrong_amt = self.engine.fetch_all("""
        SELECT l.item_id, l.raw_ref, l.txn_date, l.amount AS l_amt, b.amount AS b_amt
        FROM norm_ledger l
        INNER JOIN norm_bank b ON l.clean_ref = b.clean_ref
        WHERE l.is_matched = 0 AND b.is_matched = 0
          AND l.item_id NOT IN (SELECT item_id FROM reconciliation_breaks WHERE run_id = ?);
        """, [self.run_id])
        for w in wrong_amt:
            bid = f"BRK_WRONG_AMT_{w['item_id']}"
            ev = f'{{"reason": "Reference matched but amount discrepancy", "gl_amount": {w["l_amt"]}, "bank_amount": {w["b_amt"]}}}'
            self.engine.execute("""
            INSERT INTO reconciliation_breaks (
                break_id, run_id, source_system, item_id, ref_number, txn_date,
                amount, break_category, confidence_score, suggested_action, status, evidence_payload
            ) VALUES (?, ?, 'CORE_LEDGER', ?, ?, ?, ?, 'WRONG_AMOUNT', 0.8500, 'REQUEST_SOURCE_CORRECTION', 'PENDING_REVIEW', ?);
            """, [bid, self.run_id, w["item_id"], w["raw_ref"], w["txn_date"], w["l_amt"], ev])

        # 4. Suspected Fraud / Structuring Pattern in Bank
        frauds = self.engine.fetch_all("""
        SELECT item_id, raw_ref, post_date, amount
        FROM norm_bank
        WHERE is_matched = 0 AND amount IN (49999.00, 49950.00, 99990.00)
          AND item_id NOT IN (SELECT item_id FROM reconciliation_breaks WHERE run_id = ?);
        """, [self.run_id])
        for f in frauds:
            bid = f"BRK_AML_{f['item_id']}"
            ev = f'{{"reason": "Structuring pattern: amount just below 50,000 reporting threshold", "amount": {f["amount"]}}}'
            self.engine.execute("""
            INSERT INTO reconciliation_breaks (
                break_id, run_id, source_system, item_id, ref_number, txn_date,
                amount, break_category, confidence_score, suggested_action, status, evidence_payload
            ) VALUES (?, ?, 'BANK_STATEMENT', ?, ?, ?, ?, 'SUSPECTED_FRAUD_PATTERN', 0.9500, 'ESCALATE_AML_COMPLIANCE', 'PENDING_REVIEW', ?);
            """, [bid, self.run_id, f["item_id"], f["raw_ref"], f["post_date"], f["amount"], ev])

        # 5. Missing Ledger Entry (Bank charge/interest)
        missing_gl = self.engine.fetch_all("""
        SELECT item_id, raw_ref, post_date, amount, narration
        FROM norm_bank
        WHERE is_matched = 0
          AND item_id NOT IN (SELECT item_id FROM reconciliation_breaks WHERE run_id = ?);
        """, [self.run_id])
        for m in missing_gl:
            bid = f"BRK_MISSING_GL_{m['item_id']}"
            clean_narration = m["narration"].replace('"', '')
            ev = f'{{"reason": "Direct bank charge unbooked in GL", "narration": "{clean_narration}", "amount": {m["amount"]}}}'
            self.engine.execute("""
            INSERT INTO reconciliation_breaks (
                break_id, run_id, source_system, item_id, ref_number, txn_date,
                amount, break_category, confidence_score, suggested_action, status, evidence_payload
            ) VALUES (?, ?, 'BANK_STATEMENT', ?, ?, ?, ?, 'MISSING_LEDGER_ENTRY', 0.8200, 'CREATE_BANK_ADJUSTMENT_VOUCHER', 'PENDING_REVIEW', ?);
            """, [bid, self.run_id, m["item_id"], m["raw_ref"], m["post_date"], m["amount"], ev])

        # Record classified breaks into audit trail
        classified_breaks = self.engine.fetch_all("SELECT break_id, break_category, confidence_score, evidence_payload FROM reconciliation_breaks WHERE run_id = ?", [self.run_id])
        for cb in classified_breaks:
            self.engine.execute("""
            INSERT INTO reconciliation_audit_log (event_id, run_id, action_type, target_entity, entity_id, rule_applied, confidence, actor, details_json)
            VALUES (?, ?, 'BREAK_CLASSIFIED', 'BREAK', ?, ?, ?, 'SYSTEM_CLOSELOOP', ?)
            """, [f"AUD_BRK_{cb['break_id']}", self.run_id, cb["break_id"], cb["break_category"], cb["confidence_score"], cb["evidence_payload"]])

        duration = time.time() - t0
        print(f"[+] Break classification completed ({len(classified_breaks):,} breaks) in {duration:.3f}s")
        return {"breaks_count": len(classified_breaks), "duration": duration}

    def execute_full_pipeline(self, data_dir=None):
        """Runs the entire end-to-end CloseLoop pipeline idempotently."""
        t_total_0 = time.time()
        print(f"\n=======================================================")
        print(f" CloseLoop: Starting Reconciliation Run: {self.run_id}")
        print(f" Engine: {self.engine.get_engine_info()['platform']}")
        print(f"=======================================================")

        self.load_raw_data(data_dir)
        norm_time = self.normalise_data()
        t1_res = self.run_tier_1_exact()
        t2_res = self.run_tier_2_rules()
        t3_res = self.run_tier_3_fuzzy()
        t4_res = self.run_tier_4_batch()
        break_res = self.classify_breaks()

        total_time = time.time() - t_total_0

        # Mark run completed in audit log
        self.engine.execute("""
        INSERT INTO reconciliation_audit_log (event_id, run_id, action_type, target_entity, entity_id, rule_applied, confidence, actor, details_json)
        VALUES (?, ?, 'RUN_COMPLETED', 'PIPELINE', ?, 'FULL_PIPELINE_SUCCESS', 1.0, 'SYSTEM_CLOSELOOP', ?)
        """, [f"AUD_END_{self.run_id}", self.run_id, self.run_id, f'{{"total_duration_sec": {total_time:.3f}}}'])

        print(f"=======================================================")
        print(f"[+] CloseLoop Pipeline Finished in {total_time:.3f}s")
        print(f"=======================================================\n")

        return {
            "run_id": self.run_id,
            "total_time": total_time,
            "t1": t1_res,
            "t2": t2_res,
            "t3": t3_res,
            "t4": t4_res,
            "breaks": break_res
        }
