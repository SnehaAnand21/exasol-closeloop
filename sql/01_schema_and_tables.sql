-- ============================================================================
-- CloseLoop: In-Database Reconciliation Engine for Exasol Personal
-- File: sql/01_schema_and_tables.sql
-- Description: DDL for staging tables, normalized entities, matches, breaks,
--              and append-only audit trail.
-- ============================================================================

-- Create dedicated schema
CREATE SCHEMA IF NOT EXISTS CLOSELOOP;
OPEN SCHEMA CLOSELOOP;

-- ----------------------------------------------------------------------------
-- 1. STAGING TABLE: Core Banking / General Ledger (GL)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE raw_core_ledger (
    raw_id          DECIMAL(18,0) IDENTITY PRIMARY KEY,
    ledger_id       VARCHAR(64),
    txn_date        VARCHAR(32),
    value_date      VARCHAR(32),
    account_no      VARCHAR(64),
    reference_no    VARCHAR(128),
    amount          VARCHAR(32),
    currency        VARCHAR(10),
    dr_cr           VARCHAR(10),
    description     VARCHAR(255),
    ingested_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 2. STAGING TABLE: Payment Gateway / Processor Feed (PG)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE raw_payment_gateway (
    raw_id          DECIMAL(18,0) IDENTITY PRIMARY KEY,
    pg_txn_id       VARCHAR(64),
    order_id        VARCHAR(64),
    gateway_ref     VARCHAR(128),
    auth_date       VARCHAR(32),
    settlement_date VARCHAR(32),
    gross_amount    VARCHAR(32),
    fee_amount      VARCHAR(32),
    net_amount      VARCHAR(32),
    status          VARCHAR(32),
    customer_ref    VARCHAR(128),
    batch_id        VARCHAR(64),
    ingested_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 3. STAGING TABLE: Bank Account Statement (Bank Feed)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE raw_bank_statement (
    raw_id          DECIMAL(18,0) IDENTITY PRIMARY KEY,
    bank_txn_id     VARCHAR(64),
    post_date       VARCHAR(32),
    value_date      VARCHAR(32),
    narration       VARCHAR(500),
    cheque_ref      VARCHAR(128),
    withdrawal_amt  VARCHAR(32),
    deposit_amt     VARCHAR(32),
    balance         VARCHAR(32),
    ingested_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 4. NORMALIZED WORKSPACE POOLS
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE norm_ledger (
    item_id         VARCHAR(64) PRIMARY KEY,
    source_system   VARCHAR(32) DEFAULT 'CORE_LEDGER',
    clean_ref       VARCHAR(128),
    raw_ref         VARCHAR(128),
    txn_date        DATE,
    value_date      DATE,
    amount          DECIMAL(18,2),
    currency        VARCHAR(10),
    direction       VARCHAR(4),     -- 'DR' or 'CR'
    account_no      VARCHAR(64),
    narration       VARCHAR(255),
    is_matched      BOOLEAN DEFAULT FALSE,
    match_id        VARCHAR(64),
    run_id          VARCHAR(64)
);

CREATE OR REPLACE TABLE norm_gateway (
    item_id         VARCHAR(64) PRIMARY KEY,
    source_system   VARCHAR(32) DEFAULT 'PAYMENT_GATEWAY',
    clean_ref       VARCHAR(128),
    raw_ref         VARCHAR(128),
    auth_date       DATE,
    settlement_date DATE,
    gross_amount    DECIMAL(18,2),
    fee_amount      DECIMAL(18,2),
    net_amount      DECIMAL(18,2),
    status          VARCHAR(32),
    batch_id        VARCHAR(64),
    is_matched      BOOLEAN DEFAULT FALSE,
    match_id        VARCHAR(64),
    run_id          VARCHAR(64)
);

CREATE OR REPLACE TABLE norm_bank (
    item_id         VARCHAR(64) PRIMARY KEY,
    source_system   VARCHAR(32) DEFAULT 'BANK_STATEMENT',
    clean_ref       VARCHAR(128),
    raw_ref         VARCHAR(128),
    post_date       DATE,
    value_date      DATE,
    amount          DECIMAL(18,2),  -- Positive for deposits, negative for withdrawals
    direction       VARCHAR(4),     -- 'CR' or 'DR'
    narration       VARCHAR(500),
    is_matched      BOOLEAN DEFAULT FALSE,
    match_id        VARCHAR(64),
    run_id          VARCHAR(64)
);

-- ----------------------------------------------------------------------------
-- 5. MATCH RESULTS TABLE (Set-based matching output)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE reconciliation_matches (
    match_id        VARCHAR(64) PRIMARY KEY,
    run_id          VARCHAR(64),
    match_tier      VARCHAR(16),    -- 'TIER_1_EXACT', 'TIER_2_RULES', 'TIER_3_FUZZY', 'TIER_4_BATCH'
    ledger_item_id  VARCHAR(64),
    bank_item_id    VARCHAR(64),
    gateway_item_id VARCHAR(64),
    match_amount    DECIMAL(18,2),
    variance_amount DECIMAL(18,2) DEFAULT 0.00,
    confidence      DECIMAL(5,4),   -- 0.0000 to 1.0000
    rule_signature  VARCHAR(128),
    explanation     VARCHAR(500),
    matched_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 6. BREAKS / EXCEPTIONS TABLE (Ranked Review Queue)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE reconciliation_breaks (
    break_id            VARCHAR(64) PRIMARY KEY,
    run_id              VARCHAR(64),
    source_system       VARCHAR(32),
    item_id             VARCHAR(64),
    ref_number          VARCHAR(128),
    txn_date            DATE,
    amount              DECIMAL(18,2),
    break_category      VARCHAR(64), -- 'TIMING_LAG', 'FEE_DISCREPANCY', 'DUPLICATE_ENTRY', 'WRONG_AMOUNT', 'MISSING_LEDGER_ENTRY', 'SUSPECTED_FRAUD_PATTERN'
    confidence_score    DECIMAL(5,4),
    suggested_action    VARCHAR(128),
    status              VARCHAR(32) DEFAULT 'PENDING_REVIEW', -- 'AUTO_RESOLVED', 'PENDING_REVIEW', 'APPROVED', 'REJECTED'
    reviewer            VARCHAR(64),
    reviewed_at         TIMESTAMP,
    evidence_payload    VARCHAR(2000), -- JSON breakdown of candidate diffs
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 7. APPEND-ONLY AUDIT LOG (Regulatory & Audit Compliance)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE reconciliation_audit_log (
    audit_id        DECIMAL(18,0) IDENTITY PRIMARY KEY,
    event_id        VARCHAR(64),
    run_id          VARCHAR(64),
    action_type     VARCHAR(64), -- 'RUN_STARTED', 'TIER_MATCH', 'BREAK_CLASSIFIED', 'MANUAL_APPROVAL', 'MANUAL_REJECTION', 'RUN_COMPLETED'
    target_entity   VARCHAR(32), -- 'MATCH', 'BREAK', 'RUN'
    entity_id       VARCHAR(64),
    rule_applied    VARCHAR(128),
    confidence      DECIMAL(5,4),
    actor           VARCHAR(64), -- 'SYSTEM_CLOSELOOP', 'USER_ANALYST', etc.
    details_json    VARCHAR(2000),
    logged_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 8. GROUND TRUTH TABLE (For Synthetic Evaluation, Precision & Recall)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE ground_truth_labels (
    txn_uuid            VARCHAR(64) PRIMARY KEY,
    ledger_id           VARCHAR(64),
    gateway_id          VARCHAR(64),
    bank_id             VARCHAR(64),
    true_relation       VARCHAR(32), -- 'EXACT_MATCH', 'FEE_VARIATION', 'TIMING_LAG', 'TYPO_REF', 'DUPLICATE', 'MISSING_GL', 'BATCH_SETTLEMENT'
    expected_tier       VARCHAR(32), -- 'TIER_1', 'TIER_2', 'TIER_3', 'TIER_4', 'BREAK'
    expected_break_type VARCHAR(64),
    injected_noise      VARCHAR(255)
);
