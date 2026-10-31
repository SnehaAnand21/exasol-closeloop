-- ============================================================================
-- CloseLoop: In-Database Reconciliation Engine for Exasol Personal
-- File: sql/reset_engine.sql
-- Description: Idempotent teardown and reset of working tables and matches.
-- ============================================================================

OPEN SCHEMA CLOSELOOP;

TRUNCATE TABLE raw_core_ledger;
TRUNCATE TABLE raw_payment_gateway;
TRUNCATE TABLE raw_bank_statement;
TRUNCATE TABLE norm_ledger;
TRUNCATE TABLE norm_gateway;
TRUNCATE TABLE norm_bank;
TRUNCATE TABLE reconciliation_matches;
TRUNCATE TABLE reconciliation_breaks;
TRUNCATE TABLE ground_truth_labels;

-- Note: Audit log is append-only by design. During complete dev reset:
TRUNCATE TABLE reconciliation_audit_log;

INSERT INTO reconciliation_audit_log (
    event_id, run_id, action_type, target_entity, entity_id,
    rule_applied, confidence, actor, details_json, logged_at
) VALUES (
    'AUD_INIT_RESET',
    'INIT',
    'RUN_STARTED',
    'RUN',
    'RESET_ALL',
    'SYSTEM_RESET',
    1.0000,
    'SYSTEM_CLOSELOOP',
    '{"message": "CloseLoop schema cleared and reset to pristine state"}',
    CURRENT_TIMESTAMP
);
