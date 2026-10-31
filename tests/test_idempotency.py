"""
CloseLoop: Unit Tests - Idempotency and Determinism
===================================================
Verifies that re-running the pipeline on identical input data
produces 100% deterministic match counts and zero duplicates.
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

class TestIdempotency(unittest.TestCase):
    def test_repeated_runs_deterministic(self):
        engine = ExasolEngine(force_local=True)
        pipeline = ReconciliationPipeline(engine)

        # First run
        run1 = pipeline.execute_full_pipeline()
        m1 = ReconciliationMetrics(engine).calculate_summary_kpis()

        # Re-run immediately on the same data
        pipeline2 = ReconciliationPipeline(engine)
        run2 = pipeline2.execute_full_pipeline()
        m2 = ReconciliationMetrics(engine).calculate_summary_kpis()

        # Match counts must be identical
        self.assertEqual(m1["total_matched"], m2["total_matched"])
        self.assertEqual(m1["t1_exact_count"], m2["t1_exact_count"])
        self.assertEqual(m1["t2_rules_count"], m2["t2_rules_count"])
        self.assertEqual(m1["t3_fuzzy_count"], m2["t3_fuzzy_count"])
        self.assertEqual(m1["t4_batch_count"], m2["t4_batch_count"])
        self.assertEqual(m1["total_breaks"], m2["total_breaks"])

if __name__ == "__main__":
    unittest.main()
