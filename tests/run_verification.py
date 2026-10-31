"""
CloseLoop: Verification and Evaluation Runner
============================================
Runs the full pipeline, prints executive KPIs, and checks precision/recall.
"""

import sys
import os
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import json
from src.pipeline import ReconciliationPipeline
from src.metrics import ReconciliationMetrics

def main():
    pipeline = ReconciliationPipeline()
    res = pipeline.execute_full_pipeline()
    metrics = ReconciliationMetrics(pipeline.engine)
    kpis = metrics.calculate_summary_kpis()
    gt = metrics.evaluate_ground_truth()

    print("\n--- EXECUTIVE SUMMARY KPIS ---")
    print(f"Total Ledger Records:     {kpis['total_ledger']:,}")
    print(f"Total Bank Records:       {kpis['total_bank']:,}")
    print(f"Tier 1 Exact Matches:     {kpis['t1_exact_count']:,}")
    print(f"Tier 2 Rules Matches:     {kpis['t2_rules_count']:,}")
    print(f"Tier 3 Fuzzy Matches:     {kpis['t3_fuzzy_count']:,}")
    print(f"Tier 4 Batch Matches:     {kpis['t4_batch_count']:,}")
    print(f"Total Matches:            {kpis['total_matched']:,}")
    print(f"Total Residual Breaks:    {kpis['total_breaks']:,}")
    print(f"Exact Baseline Rate:      {kpis['exact_baseline_pct']}%")
    print(f"CloseLoop Auto-Clear:     {kpis['autoclear_rate_pct']}%")
    print(f"Auto-Clear Rate Lift:     +{kpis['lift_pct']}%")

    print("\n--- GROUND TRUTH EVALUATION ---")
    print(f"Match Precision:          {gt['match_precision']}%")
    print(f"Match Recall:             {gt['match_recall']}%")
    print(f"Match F1 Score:           {gt['match_f1']}%")
    
    print("\nTier-by-Tier Recall:")
    for t in gt['tier_breakdown']:
        pct = round(t['correct_matches'] / t['total_gt'] * 100.0, 2) if t['total_gt'] else 0
        print(f"  - {t['true_relation']} ({t['expected_tier']}): {t['correct_matches']}/{t['total_gt']} ({pct}%)")

    print("\nBreak Classification Accuracy:")
    for b in gt['break_classification_breakdown']:
        pct = round(b['correctly_classified'] / b['total_expected'] * 100.0, 2) if b['total_expected'] else 0
        print(f"  - {b['expected_break_type']}: {b['correctly_classified']}/{b['total_expected']} ({pct}%)")

if __name__ == "__main__":
    main()
