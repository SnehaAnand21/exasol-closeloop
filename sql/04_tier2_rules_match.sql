-- ============================================================================
-- CloseLoop: In-Database Reconciliation Engine for Exasol Personal
-- File: sql/04_tier2_rules_match.sql
-- Description: Tier 2 Rules-Based Match.
--              Evaluates T+1..T+3 settlement lag, payment gateway fee deduction,
--              and penny rounding tolerances. High confidence (95%-98%).
-- ============================================================================

OPEN SCHEMA CLOSELOOP;

-- Candidate table for Tier 2 matches
CREATE OR REPLACE TEMPORARY TABLE t2_candidates AS
SELECT
    'M2_' || l.item_id || '_' || b.item_id AS match_id,
    l.run_id,
    'TIER_2_RULES' AS match_tier,
    l.item_id AS ledger_item_id,
    b.item_id AS bank_item_id,
    g.item_id AS gateway_item_id,
    l.amount AS match_amount,
    CAST(l.amount - b.amount AS DECIMAL(18,2)) AS variance_amount,
    CASE 
        -- Rule 2A: Settlement lag (T+1 to T+3 days) with identical amount
        WHEN b.post_date >= l.txn_date AND b.post_date <= ADD_DAYS(l.txn_date, 3) 
             AND l.amount = b.amount THEN CAST(0.9800 AS DECIMAL(5,4))
             
        -- Rule 2B: Known gateway fee deduction (bank amount equals net payout)
        WHEN g.item_id IS NOT NULL 
             AND (b.amount = g.net_amount OR b.amount = (l.amount - g.fee_amount))
             AND b.post_date >= l.txn_date AND b.post_date <= ADD_DAYS(l.txn_date, 4) THEN CAST(0.9600 AS DECIMAL(5,4))
             
        -- Rule 2C: Minor rounding tolerance (diff <= 0.05 INR)
        WHEN ABS(l.amount - b.amount) <= 0.05 
             AND b.post_date >= l.txn_date AND b.post_date <= ADD_DAYS(l.txn_date, 2) THEN CAST(0.9500 AS DECIMAL(5,4))
             
        ELSE CAST(0.9200 AS DECIMAL(5,4))
    END AS confidence,
    CASE 
        WHEN b.post_date > l.txn_date AND l.amount = b.amount THEN 'RULE_SETTLEMENT_LAG_T_PLUS_N'
        WHEN g.item_id IS NOT NULL AND (b.amount = g.net_amount OR b.amount = (l.amount - g.fee_amount)) THEN 'RULE_MDR_FEE_DEDUCTION'
        WHEN ABS(l.amount - b.amount) <= 0.05 THEN 'RULE_ROUNDING_TOLERANCE'
        ELSE 'RULE_COMPOSITE_RULES'
    END AS rule_signature,
    CASE 
        WHEN b.post_date > l.txn_date AND l.amount = b.amount 
            THEN 'Settlement lag cleared: ' || CAST(DAYS_BETWEEN(b.post_date, l.txn_date) AS VARCHAR(10)) || ' days lag'
        WHEN g.item_id IS NOT NULL AND (b.amount = g.net_amount OR b.amount = (l.amount - g.fee_amount))
            THEN 'Reconciled gross to net: PG fee of ' || CAST(g.fee_amount AS VARCHAR(20)) || ' INR accounted for'
        WHEN ABS(l.amount - b.amount) <= 0.05 
            THEN 'Penny rounding variance resolved: delta = ' || CAST(l.amount - b.amount AS VARCHAR(20))
        ELSE 'Rule based resolution'
    END AS explanation
FROM norm_ledger l
INNER JOIN norm_bank b
    ON l.clean_ref = b.clean_ref
   AND l.is_matched = FALSE
   AND b.is_matched = FALSE
   AND LENGTH(l.clean_ref) >= 6
   AND (
        -- Condition 1: Settlement lag T+1 to T+3 with exact amount
        (b.post_date >= l.txn_date AND b.post_date <= ADD_DAYS(l.txn_date, 3) AND l.amount = b.amount)
        OR
        -- Condition 2: Penny rounding tolerance <= 0.05
        (ABS(l.amount - b.amount) <= 0.05 AND b.post_date >= l.txn_date AND b.post_date <= ADD_DAYS(l.txn_date, 2))
   )
LEFT JOIN norm_gateway g
    ON l.clean_ref = g.clean_ref
   AND g.is_matched = FALSE;

-- Ensure 1-to-1 uniqueness
CREATE OR REPLACE TEMPORARY TABLE t2_unique_matches AS
SELECT *
FROM (
    SELECT 
        c.*,
        ROW_NUMBER() OVER (PARTITION BY ledger_item_id ORDER BY confidence DESC, bank_item_id) AS rn_l,
        ROW_NUMBER() OVER (PARTITION BY bank_item_id ORDER BY confidence DESC, ledger_item_id) AS rn_b
    FROM t2_candidates c
)
WHERE rn_l = 1 AND rn_b = 1;

-- Insert matches
INSERT INTO reconciliation_matches (
    match_id, run_id, match_tier, ledger_item_id, bank_item_id,
    gateway_item_id, match_amount, variance_amount, confidence,
    rule_signature, explanation, matched_at
)
SELECT 
    match_id, run_id, match_tier, ledger_item_id, bank_item_id,
    gateway_item_id, match_amount, variance_amount, confidence,
    rule_signature, explanation, CURRENT_TIMESTAMP
FROM t2_unique_matches;

-- Mark ledger matched
MERGE INTO norm_ledger l
USING t2_unique_matches m
ON (l.item_id = m.ledger_item_id)
WHEN MATCHED THEN UPDATE SET 
    l.is_matched = TRUE,
    l.match_id = m.match_id;

-- Mark bank matched
MERGE INTO norm_bank b
USING t2_unique_matches m
ON (b.item_id = m.bank_item_id)
WHEN MATCHED THEN UPDATE SET 
    b.is_matched = TRUE,
    b.match_id = m.match_id;

-- Mark gateway matched
MERGE INTO norm_gateway g
USING (SELECT gateway_item_id, match_id FROM t2_unique_matches WHERE gateway_item_id IS NOT NULL) m
ON (g.item_id = m.gateway_item_id)
WHEN MATCHED THEN UPDATE SET 
    g.is_matched = TRUE,
    g.match_id = m.match_id;

-- Audit trail entry
INSERT INTO reconciliation_audit_log (
    event_id, run_id, action_type, target_entity, entity_id,
    rule_applied, confidence, actor, details_json, logged_at
)
SELECT
    'AUD_T2_' || match_id,
    run_id,
    'TIER_MATCH',
    'MATCH',
    match_id,
    rule_signature,
    confidence,
    'SYSTEM_CLOSELOOP',
    '{"tier": "T2", "rule": "' || rule_signature || '", "variance": ' || CAST(variance_amount AS VARCHAR(20)) || '}',
    CURRENT_TIMESTAMP
FROM t2_unique_matches;
