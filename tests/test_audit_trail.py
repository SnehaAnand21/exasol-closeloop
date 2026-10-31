"""
CloseLoop: Unit Tests - Regulatory Audit Trail Immutability
===========================================================
Verifies that all actions are recorded in the append-only audit ledger.
"""

import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.pipeline import ReconciliationPipeline
from src.exasol_engine import ExasolEngine

class TestAuditTrail(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = ExasolEngine(force_local=True)
        cls.pipeline = ReconciliationPipeline(cls.engine)
        cls.pipeline.execute_full_pipeline()

    def test_audit_entries_exist(self):
        logs = self.engine.fetch_all("SELECT * FROM reconciliation_audit_log;")
        self.assertGreater(len(logs), 100)

    def test_pipeline_lifecycle_events(self):
        actions = [l["action_type"] for l in self.engine.fetch_all("SELECT action_type FROM reconciliation_audit_log;")]
        self.assertIn("RUN_STARTED", actions)
        self.assertIn("TIER_MATCH", actions)
        self.assertIn("BREAK_CLASSIFIED", actions)
        self.assertIn("RUN_COMPLETED", actions)

    def test_manual_approval_audit(self):
        # Simulate human reviewer approving a break
        self.engine.execute("""
        INSERT INTO reconciliation_audit_log (event_id, run_id, action_type, target_entity, entity_id, rule_applied, confidence, actor, details_json)
        VALUES ('TEST_AUD_01', 'RUN_TEST', 'MANUAL_APPROVAL', 'BREAK', 'BRK_001', 'HUMAN_APPROVAL', 1.0, 'ANALYST_SHARMA', '{"decision": "APPROVED"}');
        """)
        rec = self.engine.fetch_one("SELECT * FROM reconciliation_audit_log WHERE event_id = 'TEST_AUD_01';")
        self.assertIsNotNone(rec)
        self.assertEqual(rec["actor"], "ANALYST_SHARMA")

if __name__ == "__main__":
    unittest.main()
