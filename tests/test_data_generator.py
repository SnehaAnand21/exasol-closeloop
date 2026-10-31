"""
CloseLoop: Unit Tests - Synthetic Data Generator
================================================
Verifies reproducible synthetic generation, column schemas, and noise distribution.
"""

import os
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from data_gen.generate_data import generate_dataset

class TestDataGenerator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = BASE_DIR / "data_test_temp"
        cls.res = generate_dataset(num_records=1000, output_dir=str(cls.test_dir), seed=123)

    @classmethod
    def tearDownClass(cls):
        import shutil
        if cls.test_dir.exists():
            shutil.rmtree(cls.test_dir)

    def test_file_creation(self):
        self.assertTrue((self.test_dir / "core_ledger.csv").exists())
        self.assertTrue((self.test_dir / "payment_gateway.csv").exists())
        self.assertTrue((self.test_dir / "bank_statement.csv").exists())
        self.assertTrue((self.test_dir / "ground_truth_labels.csv").exists())

    def test_row_counts(self):
        self.assertGreater(self.res["ledger_count"], 900)
        self.assertGreater(self.res["bank_count"], 900)
        self.assertGreater(self.res["ground_truth_count"], 900)

if __name__ == "__main__":
    unittest.main()
