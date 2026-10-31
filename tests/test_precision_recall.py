"""
CloseLoop: Unit Tests - Precision, Recall, and Baseline Lift
============================================================
Asserts that CloseLoop meets strict accuracy criteria:
  - Precision >= 98.0%
  - Recall >= 95.0%
  - Auto-Clear Rate Lift >= 25.0%
"""

import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.pipeline import ReconciliationPipeline
from src.metrics import ReconciliationMetrics
from src.exasol_engine import ExasolEngine

class TestPrecisionRecall(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = ExasolEngine(force_local=True)
        cls.pipeline = ReconciliationPipeline(cls.engine)
        cls.pipeline.execute_full_pipeline()
        cls.metrics = ReconciliationMetrics(cls.engine)
        cls.kpis = cls.metrics.calculate_summary_kpis()
        cls.gt = cls.metrics.evaluate_ground_truth()

    def test_precision_threshold(self):
        self.assertGreaterEqual(self.gt["match_precision"], 98.0, "Match precision must be at least 98%")

    def test_recall_threshold(self):
        self.assertGreaterEqual(self.gt["match_recall"], 95.0, "Match recall must be at least 95%")

    def test_autoclear_lift(self):
        self.assertGreaterEqual(self.kpis["lift_pct"], 25.0, "Auto-clear lift over baseline must exceed 25%")

if __name__ == "__main__":
    unittest.main()
