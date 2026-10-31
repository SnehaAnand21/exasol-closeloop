"""
CloseLoop: Unit Tests - Exception Classification & Explanations
==============================================================
Verifies that residual breaks are accurately categorized with
actionable guidance and confidence scores.
"""

import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.pipeline import ReconciliationPipeline
from src.exasol_engine import ExasolEngine

class TestBreakClassifier(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = ExasolEngine(force_local=True)
        cls.pipeline = ReconciliationPipeline(cls.engine)
        cls.pipeline.execute_full_pipeline()

    def test_break_categories_present(self):
        categories = self.engine.fetch_all("SELECT DISTINCT break_category FROM reconciliation_breaks;")
        cat_set = {c["break_category"] for c in categories}
        expected = {"DUPLICATE_ENTRY", "TIMING_LAG", "WRONG_AMOUNT", "MISSING_LEDGER_ENTRY", "SUSPECTED_FRAUD_PATTERN"}
        for exp in expected:
            self.assertIn(exp, cat_set, f"Expected break category {exp} not generated")

    def test_evidence_payload_json(self):
        sample_breaks = self.engine.fetch_all("SELECT evidence_payload FROM reconciliation_breaks LIMIT 10;")
        import json
        for b in sample_breaks:
            payload = json.loads(b["evidence_payload"])
            self.assertIn("reason", payload)

if __name__ == "__main__":
    unittest.main()
