-- ============================================================================
-- CloseLoop: In-Database Reconciliation Engine for Exasol Personal
-- File: sql/08_audit_trail.sql
-- Description: Regulatory Audit Trail and Reviewer Actions.
--              Maintains an immutable append-only event ledger for all matching,
--              break classification, and manual human reviewer approvals/rejections.
-- ============================================================================

OPEN SCHEMA CLOSELOOP;

-- Stored procedure to record human reviewer decisions
--/
CREATE OR REPLACE SCRIPT record_reviewer_decision(
    p_break_id VARCHAR(64),
    p_action VARCHAR(32),    -- 'APPROVED' or 'REJECTED'
    p_reviewer VARCHAR(64),
    p_notes VARCHAR(1000)
) AS
    -- Update break status
    EXECUTE_UPDATE([[
        UPDATE reconciliation_breaks
        SET status = :act,
            reviewer = :rev,
            reviewed_at = CURRENT_TIMESTAMP
        WHERE break_id = :bid
    ]], {act=p_action, rev=p_reviewer, bid=p_break_id});

    -- Append to audit ledger
    EXECUTE_UPDATE([[
        INSERT INTO reconciliation_audit_log (
            event_id, run_id, action_type, target_entity, entity_id,
            rule_applied, confidence, actor, details_json, logged_at
        ) VALUES (
            'AUD_MAN_' || :bid,
            'RUN_LATEST',
            CASE WHEN :act = 'APPROVED' THEN 'MANUAL_APPROVAL' ELSE 'MANUAL_REJECTION' END,
            'BREAK',
            :bid,
            'HUMAN_REVIEWER_DECISION',
            1.0000,
            :rev,
            '{"decision": "' || :act || '", "notes": "' || :notes || '"}',
            CURRENT_TIMESTAMP
        )
    ]], {act=p_action, rev=p_reviewer, bid=p_break_id, notes=p_notes});
/
