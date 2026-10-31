-- ============================================================================
-- CloseLoop: In-Database Reconciliation Engine for Exasol Personal
-- File: sql/02_normalise_and_stage.sql
-- Description: Normalise ingested staging tables inside Exasol using set-based SQL.
--              Strips noise tokens (UTR:, TXN-, REF#, /) and casts dates & amounts.
-- ============================================================================

OPEN SCHEMA CLOSELOOP;

-- Clear previous normalized working set for the given run or refresh
DELETE FROM norm_ledger;
DELETE FROM norm_gateway;
DELETE FROM norm_bank;

-- 1. Normalise Core Ledger
INSERT INTO norm_ledger (
    item_id, source_system, clean_ref, raw_ref, txn_date, value_date,
    amount, currency, direction, account_no, narration, is_matched, match_id, run_id
)
SELECT
    ledger_id AS item_id,
    'CORE_LEDGER' AS source_system,
    UPPER(REGEXP_REPLACE(REGEXP_REPLACE(UPPER(TRIM(reference_no)), '^(REF#|TXN[-:]?|UTR[-:]?|INV[-:/]?|CHQ[-:]?|PG[-:]?)', ''), '[^a-zA-Z0-9]', '')) AS clean_ref,
    reference_no AS raw_ref,
    CAST(txn_date AS DATE) AS txn_date,
    CAST(COALESCE(NULLIF(value_date, ''), txn_date) AS DATE) AS value_date,
    CAST(amount AS DECIMAL(18,2)) AS amount,
    COALESCE(currency, 'INR') AS currency,
    UPPER(TRIM(dr_cr)) AS direction,
    account_no,
    description AS narration,
    FALSE AS is_matched,
    NULL AS match_id,
    'RUN_LATEST' AS run_id
FROM raw_core_ledger;

-- 2. Normalise Payment Gateway
INSERT INTO norm_gateway (
    item_id, source_system, clean_ref, raw_ref, auth_date, settlement_date,
    gross_amount, fee_amount, net_amount, status, batch_id, is_matched, match_id, run_id
)
SELECT
    pg_txn_id AS item_id,
    'PAYMENT_GATEWAY' AS source_system,
    UPPER(REGEXP_REPLACE(REGEXP_REPLACE(UPPER(TRIM(gateway_ref)), '^(REF#|TXN[-:]?|UTR[-:]?|INV[-:/]?|CHQ[-:]?|PG[-:]?)', ''), '[^a-zA-Z0-9]', '')) AS clean_ref,
    gateway_ref AS raw_ref,
    CAST(auth_date AS DATE) AS auth_date,
    CAST(COALESCE(NULLIF(settlement_date, ''), auth_date) AS DATE) AS settlement_date,
    CAST(gross_amount AS DECIMAL(18,2)) AS gross_amount,
    CAST(COALESCE(NULLIF(fee_amount, ''), '0.00') AS DECIMAL(18,2)) AS fee_amount,
    CAST(COALESCE(NULLIF(net_amount, ''), gross_amount) AS DECIMAL(18,2)) AS net_amount,
    UPPER(TRIM(status)) AS status,
    batch_id,
    FALSE AS is_matched,
    NULL AS match_id,
    'RUN_LATEST' AS run_id
FROM raw_payment_gateway;

-- 3. Normalise Bank Statement
INSERT INTO norm_bank (
    item_id, source_system, clean_ref, raw_ref, post_date, value_date,
    amount, direction, narration, is_matched, match_id, run_id
)
SELECT
    bank_txn_id AS item_id,
    'BANK_STATEMENT' AS source_system,
    UPPER(REGEXP_REPLACE(REGEXP_REPLACE(UPPER(TRIM(cheque_ref)), '^(REF#|TXN[-:]?|UTR[-:]?|INV[-:/]?|CHQ[-:]?|PG[-:]?)', ''), '[^a-zA-Z0-9]', '')) AS clean_ref,
    cheque_ref AS raw_ref,
    CAST(post_date AS DATE) AS post_date,
    CAST(COALESCE(NULLIF(value_date, ''), post_date) AS DATE) AS value_date,
    CASE 
        WHEN deposit_amt IS NOT NULL AND CAST(deposit_amt AS DECIMAL(18,2)) > 0 
            THEN CAST(deposit_amt AS DECIMAL(18,2))
        WHEN withdrawal_amt IS NOT NULL AND CAST(withdrawal_amt AS DECIMAL(18,2)) > 0 
            THEN -CAST(withdrawal_amt AS DECIMAL(18,2))
        ELSE 0.00
    END AS amount,
    CASE 
        WHEN deposit_amt IS NOT NULL AND CAST(deposit_amt AS DECIMAL(18,2)) > 0 THEN 'CR'
        ELSE 'DR'
    END AS direction,
    narration,
    FALSE AS is_matched,
    NULL AS match_id,
    'RUN_LATEST' AS run_id
FROM raw_bank_statement;
