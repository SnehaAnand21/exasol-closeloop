"""
CloseLoop: Unit Tests - Tiered In-Database Matching
===================================================
Verifies T1 Exact, T2 Rules, T3 Fuzzy, and T4 Batch matching correctness.
"""

import os
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.pipeline import ReconciliationPipeline
from src.metrics import ReconciliationMetrics
from src.exasol_engine import ExasolEngine

class TestTieredMatching(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = ExasolEngine(force_local=True)
        cls.pipeline = ReconciliationPipeline(cls.engine)
        cls.pipeline.execute_full_pipeline()
        cls.metrics = ReconciliationMetrics(cls.engine)

    def test_tier_1_exact_matching(self):
        t1_matches = self.engine.fetch_all("SELECT * FROM reconciliation_matches WHERE match_tier = 'TIER_1_EXACT';")
        self.assertGreater(len(t1_matches), 1000)
        # All T1 matches must have zero variance and confidence 1.0
        for m in t1_matches[:50]:
            self.assertEqual(float(m["variance_amount"]), 0.0)
            self.assertEqual(float(m["confidence"]), 1.0000)

    def test_tier_2_rules_matching(self):
        t2_matches = self.engine.fetch_all("SELECT * FROM reconciliation_matches WHERE match_tier = 'TIER_2_RULES';")
        self.assertGreater(len(t2_matches), 500)
        for m in t2_matches[:50]:
            self.assertIn(m["rule_signature"], ["RULE_SETTLEMENT_LAG_T_PLUS_N", "RULE_MDR_FEE_DEDUCTION", "RULE_ROUNDING_TOLERANCE"])
            self.assertGreaterEqual(float(m["confidence"]), 0.92)

    def test_tier_3_fuzzy_matching(self):
        t3_matches = self.engine.fetch_all("SELECT * FROM reconciliation_matches WHERE match_tier = 'TIER_3_FUZZY';")
        self.assertGreater(len(t3_matches), 200)
        for m in t3_matches[:50]:
            self.assertGreaterEqual(float(m["confidence"]), 0.85)

    def test_tier_4_batch_settlement(self):
        t4_matches = self.engine.fetch_all("SELECT * FROM reconciliation_matches WHERE match_tier = 'TIER_4_BATCH';")
        self.assertGreater(len(t4_matches), 10)
        for m in t4_matches[:10]:
            self.assertIn("M4_BATCH", m["match_id"])
            self.assertGreater(float(m["match_amount"]), 0.0)

if __name__ == "__main__":
    unittest.main()
