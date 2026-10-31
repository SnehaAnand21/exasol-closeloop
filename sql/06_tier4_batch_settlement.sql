-- ============================================================================
-- CloseLoop: In-Database Reconciliation Engine for Exasol Personal
-- File: sql/06_tier4_batch_settlement.sql
-- Description: Tier 4 Many-to-One Batch Settlements.
--              Matches aggregated batches of gateway/ledger entries to a single
--              lump-sum bank statement credit/deposit.
-- ============================================================================

OPEN SCHEMA CLOSELOOP;

-- Aggregate unmatched gateway items by batch_id
CREATE OR REPLACE TEMPORARY TABLE batch_aggregates AS
SELECT
    batch_id,
    COUNT(*) AS item_count,
    SUM(net_amount) AS total_net_amount,
    SUM(gross_amount) AS total_gross_amount,
    MIN(settlement_date) AS min_settlement_date,
    MAX(settlement_date) AS max_settlement_date
FROM norm_gateway
WHERE is_matched = FALSE
  AND batch_id IS NOT NULL
  AND batch_id != ''
GROUP BY batch_id
HAVING COUNT(*) > 1;

-- Match aggregate batch totals against single bank deposits
CREATE OR REPLACE TEMPORARY TABLE t4_batch_matches AS
SELECT
    'M4_BATCH_' || ba.batch_id || '_' || b.item_id AS match_id,
    'RUN_LATEST' AS run_id,
    'TIER_4_BATCH' AS match_tier,
    ba.batch_id,
    b.item_id AS bank_item_id,
    ba.item_count,
    ba.total_net_amount AS match_amount,
    CAST(0.00 AS DECIMAL(18,2)) AS variance_amount,
    CAST(0.9400 AS DECIMAL(5,4)) AS confidence,
    'RULE_MANY_TO_ONE_BATCH' AS rule_signature,
    'Many-to-one batch settlement: ' || CAST(ba.item_count AS VARCHAR(10)) || ' gateway txns matched to bank lump sum' AS explanation
FROM batch_aggregates ba
INNER JOIN norm_bank b
    ON b.is_matched = FALSE
   AND b.amount = ba.total_net_amount
   AND b.post_date >= ba.min_settlement_date
   AND b.post_date <= ADD_DAYS(ba.max_settlement_date, 2)
   AND (
        b.clean_ref LIKE '%' || ba.batch_id || '%' 
        OR b.narration LIKE '%' || ba.batch_id || '%'
        OR 1=1 -- Amount match on distinct batch total within temporal window
   );

-- Filter unique bank items
CREATE OR REPLACE TEMPORARY TABLE t4_unique_batch_matches AS
SELECT *
FROM (
    SELECT 
        m.*,
        ROW_NUMBER() OVER (PARTITION BY bank_item_id ORDER BY confidence DESC) AS rn_b
    FROM t4_batch_matches m
)
WHERE rn_b = 1;

-- Insert batch matches into reconciliation_matches
INSERT INTO reconciliation_matches (
    match_id, run_id, match_tier, ledger_item_id, bank_item_id,
    gateway_item_id, match_amount, variance_amount, confidence,
    rule_signature, explanation, matched_at
)
SELECT 
    match_id, run_id, match_tier, 'BATCH_' || batch_id AS ledger_item_id, bank_item_id,
    batch_id AS gateway_item_id, match_amount, variance_amount, confidence,
    rule_signature, explanation, CURRENT_TIMESTAMP
FROM t4_unique_batch_matches;

-- Mark bank item as matched
MERGE INTO norm_bank b
USING t4_unique_batch_matches m
ON (b.item_id = m.bank_item_id)
WHEN MATCHED THEN UPDATE SET 
    b.is_matched = TRUE,
    b.match_id = m.match_id;

-- Mark constituent gateway items as matched
MERGE INTO norm_gateway g
USING t4_unique_batch_matches m
ON (g.batch_id = m.batch_id)
WHEN MATCHED THEN UPDATE SET 
    g.is_matched = TRUE,
    g.match_id = m.match_id;

-- Mark corresponding ledger items matching batch gateway references
MERGE INTO norm_ledger l
USING (
    SELECT g.clean_ref, m.match_id 
    FROM norm_gateway g 
    INNER JOIN t4_unique_batch_matches m ON g.batch_id = m.batch_id
) gm
ON (l.clean_ref = gm.clean_ref)
WHEN MATCHED THEN UPDATE SET 
    l.is_matched = TRUE,
    l.match_id = gm.match_id;

-- Audit trail entry
INSERT INTO reconciliation_audit_log (
    event_id, run_id, action_type, target_entity, entity_id,
    rule_applied, confidence, actor, details_json, logged_at
)
SELECT
    'AUD_T4_' || match_id,
    run_id,
    'TIER_MATCH',
    'MATCH',
    match_id,
    rule_signature,
    confidence,
    'SYSTEM_CLOSELOOP',
    '{"tier": "T4", "batch_id": "' || batch_id || '", "item_count": ' || CAST(item_count AS VARCHAR(10)) || '}',
    CURRENT_TIMESTAMP
FROM t4_unique_batch_matches;
