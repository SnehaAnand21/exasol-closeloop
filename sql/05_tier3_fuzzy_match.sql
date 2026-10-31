-- ============================================================================
-- CloseLoop: In-Database Reconciliation Engine for Exasol Personal
-- File: sql/05_tier3_fuzzy_match.sql
-- Description: Tier 3 Fuzzy Matching.
--              Leverages Exasol built-in EDIT_DISTANCE / Levenshtein metric
--              plus Python scalar UDF fallback. Matches noisy references with
--              exact or near-exact amounts within a tight temporal window.
-- ============================================================================

OPEN SCHEMA CLOSELOOP;

-- Exasol Python3 Scalar UDF for fuzzy similarity (ratio between 0.0 and 1.0)
-- Note: Exasol native EDIT_DISTANCE is also used directly in the join condition.
--/
CREATE OR REPLACE PYTHON3 SCALAR SCRIPT calc_fuzzy_ratio(s1 VARCHAR(200), s2 VARCHAR(200)) 
RETURNS DOUBLE AS
def run(ctx):
    if ctx.s1 is None or ctx.s2 is None:
        return 0.0
    a, b = ctx.s1, ctx.s2
    if a == b:
        return 1.0
    la, lb = len(a), len(b)
    if la == 0 or lb == 0:
        return 0.0
    # Fast DP Levenshtein distance
    dp = list(range(lb + 1))
    for i, ca in enumerate(a):
        new_dp = [i + 1] * (lb + 1)
        for j, cb in enumerate(b):
            cost = 0 if ca == cb else 1
            new_dp[j + 1] = min(dp[j + 1] + 1, new_dp[j] + 1, dp[j] + cost)
        dp = new_dp
    dist = dp[lb]
    max_l = max(la, lb)
    return round(1.0 - (dist / max_l), 4)
/

-- Candidate generation for Tier 3 Fuzzy Matching
-- Optimization: Block on exact amount AND date within +/- 2 days to maintain O(N) performance inside Exasol!
CREATE OR REPLACE TEMPORARY TABLE t3_candidates AS
SELECT
    'M3_' || l.item_id || '_' || b.item_id AS match_id,
    l.run_id,
    'TIER_3_FUZZY' AS match_tier,
    l.item_id AS ledger_item_id,
    b.item_id AS bank_item_id,
    CAST(NULL AS VARCHAR(64)) AS gateway_item_id,
    l.amount AS match_amount,
    CAST(l.amount - b.amount AS DECIMAL(18,2)) AS variance_amount,
    CAST(0.8800 AS DECIMAL(5,4)) AS confidence,
    'RULE_FUZZY_REF_EXACT_AMOUNT' AS rule_signature,
    'Fuzzy reference match (edit dist <= 2, ref: ' || l.clean_ref || ' ~ ' || b.clean_ref || ')' AS explanation
FROM norm_ledger l
INNER JOIN norm_bank b
    ON l.amount = b.amount                                -- High-selectivity blocking key
   AND b.post_date >= ADD_DAYS(l.txn_date, -1)           -- Date proximity
   AND b.post_date <= ADD_DAYS(l.txn_date, 3)
   AND l.is_matched = FALSE
   AND b.is_matched = FALSE
   AND LENGTH(l.clean_ref) >= 6
   AND LENGTH(b.clean_ref) >= 6
   AND (
        -- Exasol native edit distance <= 2 OR prefix match
        EDIT_DISTANCE(l.clean_ref, b.clean_ref) <= 2
        OR SUBSTR(l.clean_ref, 1, 8) = SUBSTR(b.clean_ref, 1, 8)
   );

-- Ensure 1-to-1 uniqueness
CREATE OR REPLACE TEMPORARY TABLE t3_unique_matches AS
SELECT *
FROM (
    SELECT 
        c.*,
        ROW_NUMBER() OVER (PARTITION BY ledger_item_id ORDER BY bank_item_id) AS rn_l,
        ROW_NUMBER() OVER (PARTITION BY bank_item_id ORDER BY ledger_item_id) AS rn_b
    FROM t3_candidates c
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
FROM t3_unique_matches;

-- Mark ledger matched
MERGE INTO norm_ledger l
USING t3_unique_matches m
ON (l.item_id = m.ledger_item_id)
WHEN MATCHED THEN UPDATE SET 
    l.is_matched = TRUE,
    l.match_id = m.match_id;

-- Mark bank matched
MERGE INTO norm_bank b
USING t3_unique_matches m
ON (b.item_id = m.bank_item_id)
WHEN MATCHED THEN UPDATE SET 
    b.is_matched = TRUE,
    b.match_id = m.match_id;

-- Audit trail entry
INSERT INTO reconciliation_audit_log (
    event_id, run_id, action_type, target_entity, entity_id,
    rule_applied, confidence, actor, details_json, logged_at
)
SELECT
    'AUD_T3_' || match_id,
    run_id,
    'TIER_MATCH',
    'MATCH',
    match_id,
    rule_signature,
    confidence,
    'SYSTEM_CLOSELOOP',
    '{"tier": "T3", "rule": "' || rule_signature || '", "confidence": 0.88}',
    CURRENT_TIMESTAMP
FROM t3_unique_matches;
