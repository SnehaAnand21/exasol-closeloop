-- ============================================================================
-- CloseLoop: In-Database Reconciliation Engine for Exasol Personal
-- File: sql/09_views_and_kpis.sql
-- Description: Analytic views and KPI summaries for Streamlit dashboard and MIS.
-- ============================================================================

OPEN SCHEMA CLOSELOOP;

-- 1. Tier-by-tier match performance view
CREATE OR REPLACE VIEW v_tier_performance AS
SELECT
    match_tier,
    COUNT(*) AS match_count,
    SUM(match_amount) AS total_volume_reconciled,
    AVG(confidence) AS avg_confidence,
    SUM(variance_amount) AS total_variance_absorbed
FROM reconciliation_matches
GROUP BY match_tier;

-- 2. Executive reconciliation summary view
CREATE OR REPLACE VIEW v_reconciliation_summary AS
WITH base_counts AS (
    SELECT 
        (SELECT COUNT(*) FROM norm_ledger) AS total_ledger_records,
        (SELECT COUNT(*) FROM norm_bank) AS total_bank_records,
        (SELECT COUNT(*) FROM reconciliation_matches WHERE match_tier = 'TIER_1_EXACT') AS t1_count,
        (SELECT COUNT(*) FROM reconciliation_matches WHERE match_tier = 'TIER_2_RULES') AS t2_count,
        (SELECT COUNT(*) FROM reconciliation_matches WHERE match_tier = 'TIER_3_FUZZY') AS t3_count,
        (SELECT COUNT(*) FROM reconciliation_matches WHERE match_tier = 'TIER_4_BATCH') AS t4_count,
        (SELECT COUNT(*) FROM reconciliation_matches) AS total_matches,
        (SELECT COUNT(*) FROM reconciliation_breaks WHERE status = 'AUTO_RESOLVED') AS auto_resolved_breaks,
        (SELECT COUNT(*) FROM reconciliation_breaks WHERE status = 'PENDING_REVIEW') AS pending_breaks,
        (SELECT COUNT(*) FROM reconciliation_breaks) AS total_breaks
    FROM DUAL
)
SELECT
    total_ledger_records,
    total_bank_records,
    t1_count,
    t2_count,
    t3_count,
    t4_count,
    total_matches,
    auto_resolved_breaks,
    pending_breaks,
    total_breaks,
    ROUND((total_matches * 100.0) / NULLIF(total_ledger_records, 0), 2) AS match_rate_pct,
    ROUND(((t1_count) * 100.0) / NULLIF(total_ledger_records, 0), 2) AS exact_baseline_rate_pct,
    ROUND(((total_matches + auto_resolved_breaks) * 100.0) / NULLIF(total_ledger_records, 0), 2) AS total_auto_clear_rate_pct,
    ROUND((((total_matches + auto_resolved_breaks) - t1_count) * 100.0) / NULLIF(total_ledger_records, 0), 2) AS auto_clear_lift_pct
FROM base_counts;

-- 3. Break category breakdown
CREATE OR REPLACE VIEW v_break_breakdown AS
SELECT
    break_category,
    status,
    COUNT(*) AS break_count,
    SUM(amount) AS total_break_amount,
    AVG(confidence_score) AS avg_confidence,
    suggested_action
FROM reconciliation_breaks
GROUP BY break_category, status, suggested_action;

-- 4. Ground Truth Precision & Recall view
CREATE OR REPLACE VIEW v_ground_truth_evaluation AS
SELECT
    gt.true_relation,
    gt.expected_tier,
    COUNT(*) AS total_ground_truth_count,
    COUNT(CASE WHEN m.match_id IS NOT NULL THEN 1 END) AS engine_matched_count,
    COUNT(CASE WHEN b.break_id IS NOT NULL THEN 1 END) AS engine_break_count,
    ROUND((COUNT(CASE WHEN m.match_id IS NOT NULL THEN 1 END) * 100.0) / COUNT(*), 2) AS recall_pct
FROM ground_truth_labels gt
LEFT JOIN reconciliation_matches m 
    ON gt.ledger_id = m.ledger_item_id OR gt.bank_id = m.bank_item_id
LEFT JOIN reconciliation_breaks b 
    ON gt.ledger_id = b.item_id OR gt.bank_id = b.item_id
GROUP BY gt.true_relation, gt.expected_tier;
