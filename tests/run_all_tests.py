"""
CloseLoop: Master Test Suite Runner
==================================
Executes all unit and integration test suites:
  - test_data_generator.py
  - test_tiered_matching.py
  - test_precision_recall.py
  - test_break_classifier.py
  - test_audit_trail.py
  - test_idempotency.py
"""

import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

def main():
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=str(BASE_DIR / "tests"), pattern="test_*.py")

    runner = unittest.TextTestRunner(verbosity=2)
    print("\n=======================================================")
    print(" Running CloseLoop Master Test Suite")
    print("=======================================================\n")
    result = runner.run(suite)

    print("\n=======================================================")
    print(f" Tests Run: {result.testsRun}")
    print(f" Errors:    {len(result.errors)}")
    print(f" Failures:  {len(result.failures)}")
    print(f" Status:    {'ALL PASSED [PASS]' if result.wasSuccessful() else 'FAILED [FAIL]'}")
    print("=======================================================\n")

    sys.exit(0 if result.wasSuccessful() else 1)

if __name__ == "__main__":
    main()
