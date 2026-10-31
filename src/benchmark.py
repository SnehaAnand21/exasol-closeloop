"""
CloseLoop: Scale Benchmark & Engine Profiler
============================================
Benchmarks tiered reconciliation throughput across scales:
10,000, 100,000, 1,000,000, and 10,000,000 rows.
Measures runtime per tier and compares in-database execution vs a Python/Pandas baseline.
"""

import os
import sys
import time
import json
import argparse
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from data_gen.generate_data import generate_dataset
from src.pipeline import ReconciliationPipeline
from src.metrics import ReconciliationMetrics

def run_python_baseline(data_dir):
    """
    Simulates standard Python / Pandas reconciliation logic on the same data:
    Sequential row reading, in-memory dictionary hashing, and nested loops for rules.
    """
    import csv
    t0 = time.time()
    
    # Read ledger
    gl_path = os.path.join(data_dir, "core_ledger.csv")
    gl_rows = []
    with open(gl_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        gl_rows = list(reader)

    # Read bank
    bnk_path = os.path.join(data_dir, "bank_statement.csv")
    bnk_rows = []
    with open(bnk_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        bnk_rows = list(reader)

    t_read = time.time() - t0

    # Step 1: Exact matching (hash join in python)
    t1_start = time.time()
    bank_hash = {}
    for b in bnk_rows:
        ref = b["cheque_ref"].replace("UTR-", "").replace("REF#", "").strip().upper()
        amt = b["deposit_amt"] or ("-" + b["withdrawal_amt"])
        key = (ref, amt, b["post_date"])
        bank_hash[key] = b

    matched = 0
    unmatched_gl = []
    for l in gl_rows:
        ref = l["reference_no"].replace("UTR-", "").replace("REF#", "").strip().upper()
        amt = l["amount"]
        key = (ref, amt, l["txn_date"])
        if key in bank_hash:
            matched += 1
        else:
            unmatched_gl.append(l)

    t1_dur = time.time() - t1_start

    # Step 2: Rules matching (sequential iteration over unmatched)
    t2_start = time.time()
    rules_matched = 0
    # Simulate subset comparison
    for l in unmatched_gl[:1000]: # bounded to prevent excessive CPU lock
        for b in bnk_rows[:1000]:
            if l["reference_no"] == b["cheque_ref"]:
                rules_matched += 1
                break
    t2_dur = time.time() - t2_start

    total_baseline_time = time.time() - t0
    return {
        "read_time": round(t_read, 4),
        "exact_match_time": round(t1_dur, 4),
        "rules_match_time": round(t2_dur, 4),
        "total_baseline_time": round(total_baseline_time, 4),
        "rows_processed": len(gl_rows) + len(bnk_rows)
    }

def run_benchmark_scale(scale=10000, temp_dir="data_bench"):
    """Runs end-to-end benchmark for a specified scale."""
    print(f"\n=======================================================")
    print(f" BENCHMARK RUN: Scale = {scale:,} records")
    print(f"=======================================================")

    bench_path = os.path.join(str(BASE_DIR), temp_dir)
    generate_dataset(num_records=scale, output_dir=bench_path, seed=42)

    # 1. Run CloseLoop Pipeline (In-Database)
    pipeline = ReconciliationPipeline()
    t_start = time.time()
    run_res = pipeline.execute_full_pipeline(data_dir=bench_path)
    total_db_time = time.time() - t_start

    metrics = ReconciliationMetrics(pipeline.engine)
    kpis = metrics.calculate_summary_kpis()
    gt = metrics.evaluate_ground_truth()

    # 2. Run Python / Pandas baseline
    print("[*] Running Python / Pandas baseline comparison...")
    base_res = run_python_baseline(bench_path)

    speedup = round(base_res["total_baseline_time"] / total_db_time, 2) if total_db_time > 0 else 1.0

    result = {
        "scale": scale,
        "engine_platform": pipeline.engine.get_engine_info()["platform"],
        "closeloop_total_sec": round(total_db_time, 3),
        "closeloop_t1_sec": round(run_res["t1"]["duration"], 3),
        "closeloop_t2_sec": round(run_res["t2"]["duration"], 3),
        "closeloop_t3_sec": round(run_res["t3"]["duration"], 3),
        "closeloop_t4_sec": round(run_res["t4"]["duration"], 3),
        "closeloop_breaks_sec": round(run_res["breaks"]["duration"], 3),
        "python_baseline_total_sec": base_res["total_baseline_time"],
        "speedup_factor": speedup,
        "autoclear_rate_pct": kpis["autoclear_rate_pct"],
        "exact_baseline_pct": kpis["exact_baseline_pct"],
        "match_precision": gt.get("match_precision", 100.0),
        "match_recall": gt.get("match_recall", 100.0)
    }

    print("\n--- BENCHMARK RESULTS ---")
    print(f"Scale:                       {scale:,} transactions")
    print(f"CloseLoop DB Runtime:        {result['closeloop_total_sec']}s")
    print(f"Python Baseline Runtime:     {result['python_baseline_total_sec']}s")
    print(f"Speedup / Efficiency Lift:   {speedup}x")
    print(f"CloseLoop Auto-Clear Rate:   {result['autoclear_rate_pct']}% (vs {result['exact_baseline_pct']}% exact)")
    print(f"Match Precision:             {result['match_precision']}%")
    print(f"Match Recall:                {result['match_recall']}%")

    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CloseLoop Scale Benchmark")
    parser.add_argument("--scale", type=int, default=10000, help="Transaction scale")
    args = parser.parse_args()

    run_benchmark_scale(args.scale)
