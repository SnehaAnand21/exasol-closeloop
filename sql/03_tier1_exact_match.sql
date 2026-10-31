-- ============================================================================
-- CloseLoop: In-Database Reconciliation Engine for Exasol Personal
-- File: sql/03_tier1_exact_match.sql
-- Description: Tier 1 Exact Match (Ref + Amount + Date).
--              Zero variance, 100% confidence. Matched rows removed from pool.
-- ============================================================================

OPEN SCHEMA CLOSELOOP;

-- Create temporary candidate table for Tier 1 matches
CREATE OR REPLACE TEMPORARY TABLE t1_candidates AS
SELECT
    'M1_' || l.item_id || '_' || b.item_id AS match_id,
    l.run_id,
    'TIER_1_EXACT' AS match_tier,
    l.item_id AS ledger_item_id,
    b.item_id AS bank_item_id,
    g.item_id AS gateway_item_id,
    l.amount AS match_amount,
    CAST(0.00 AS DECIMAL(18,2)) AS variance_amount,
    CAST(1.0000 AS DECIMAL(5,4)) AS confidence,
    'EXACT_REF_AMT_DATE' AS rule_signature,
    'Direct three-way exact match on reference, amount, and transaction date' AS explanation
FROM norm_ledger l
INNER JOIN norm_bank b
    ON l.clean_ref = b.clean_ref
   AND l.amount = b.amount
   AND l.txn_date = b.post_date
   AND l.is_matched = FALSE
   AND b.is_matched = FALSE
   AND LENGTH(l.clean_ref) >= 6
LEFT JOIN norm_gateway g
    ON l.clean_ref = g.clean_ref
   AND l.amount = g.gross_amount
   AND g.is_matched = FALSE;

-- Ensure 1-to-1 uniqueness: pick first match if duplicates exist
CREATE OR REPLACE TEMPORARY TABLE t1_unique_matches AS
SELECT *
FROM (
    SELECT 
        c.*,
        ROW_NUMBER() OVER (PARTITION BY ledger_item_id ORDER BY bank_item_id) AS rn_l,
        ROW_NUMBER() OVER (PARTITION BY bank_item_id ORDER BY ledger_item_id) AS rn_b
    FROM t1_candidates c
)
WHERE rn_l = 1 AND rn_b = 1;

-- Insert into persistent matches table
INSERT INTO reconciliation_matches (
    match_id, run_id, match_tier, ledger_item_id, bank_item_id,
    gateway_item_id, match_amount, variance_amount, confidence,
    rule_signature, explanation, matched_at
)
SELECT 
    match_id, run_id, match_tier, ledger_item_id, bank_item_id,
    gateway_item_id, match_amount, variance_amount, confidence,
    rule_signature, explanation, CURRENT_TIMESTAMP
FROM t1_unique_matches;

-- Mark ledger items as matched
MERGE INTO norm_ledger l
USING t1_unique_matches m
ON (l.item_id = m.ledger_item_id)
WHEN MATCHED THEN UPDATE SET 
    l.is_matched = TRUE,
    l.match_id = m.match_id;

-- Mark bank items as matched
MERGE INTO norm_bank b
USING t1_unique_matches m
ON (b.item_id = m.bank_item_id)
WHEN MATCHED THEN UPDATE SET 
    b.is_matched = TRUE,
    b.match_id = m.match_id;

-- Mark gateway items as matched where present
MERGE INTO norm_gateway g
USING (SELECT gateway_item_id, match_id FROM t1_unique_matches WHERE gateway_item_id IS NOT NULL) m
ON (g.item_id = m.gateway_item_id)
WHEN MATCHED THEN UPDATE SET 
    g.is_matched = TRUE,
    g.match_id = m.match_id;

-- Audit trail entry for Tier 1
INSERT INTO reconciliation_audit_log (
    event_id, run_id, action_type, target_entity, entity_id,
    rule_applied, confidence, actor, details_json, logged_at
)
SELECT
    'AUD_T1_' || match_id,
    run_id,
    'TIER_MATCH',
    'MATCH',
    match_id,
    'TIER_1_EXACT',
    1.0000,
    'SYSTEM_CLOSELOOP',
    '{"tier": "T1", "rule": "EXACT_REF_AMT_DATE", "ledger_id": "' || ledger_item_id || '", "bank_id": "' || bank_item_id || '"}',
    CURRENT_TIMESTAMP
FROM t1_unique_matches;
