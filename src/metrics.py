"""
CloseLoop: Precision, Recall, and Ground Truth Evaluation Metrics
================================================================
Measures reconciliation engine accuracy, auto-clear rate lift over
an exact-match baseline, and precision/recall across break categories.
"""

from src.exasol_engine import ExasolEngine

class ReconciliationMetrics:
    def __init__(self, engine: ExasolEngine):
        self.engine = engine

    def calculate_summary_kpis(self):
        """Calculates primary executive KPIs: match rates, baseline, and lift."""
        total_ledger = self.engine.fetch_one("SELECT COUNT(*) AS cnt FROM norm_ledger")["cnt"]
        total_bank = self.engine.fetch_one("SELECT COUNT(*) AS cnt FROM norm_bank")["cnt"]

        # Match counts per tier
        tier_counts = self.engine.fetch_all("""
        SELECT match_tier, COUNT(*) AS cnt, SUM(match_amount) AS total_vol
        FROM reconciliation_matches
        GROUP BY match_tier;
        """)
        tiers = {r["match_tier"]: r["cnt"] for r in tier_counts}
        t1_count = tiers.get("TIER_1_EXACT", 0)
        t2_count = tiers.get("TIER_2_RULES", 0)
        t3_count = tiers.get("TIER_3_FUZZY", 0)
        t4_count = tiers.get("TIER_4_BATCH", 0)
        total_matched = sum(tiers.values())

        # Breaks count
        break_counts = self.engine.fetch_all("""
        SELECT break_category, status, COUNT(*) AS cnt
        FROM reconciliation_breaks
        GROUP BY break_category, status;
        """)
        total_breaks = sum(r["cnt"] for r in break_counts)
        auto_resolved_breaks = sum(r["cnt"] for r in break_counts if r["status"] == "AUTO_RESOLVED")
        pending_review_breaks = sum(r["cnt"] for r in break_counts if r["status"] == "PENDING_REVIEW")

        # Baseline vs Lift calculations
        exact_baseline_pct = (t1_count / total_ledger * 100.0) if total_ledger else 0.0
        total_autocleared = total_matched + auto_resolved_breaks
        autoclear_rate_pct = (total_autocleared / total_ledger * 100.0) if total_ledger else 0.0
        lift_pct = autoclear_rate_pct - exact_baseline_pct

        return {
            "total_ledger": total_ledger,
            "total_bank": total_bank,
            "t1_exact_count": t1_count,
            "t2_rules_count": t2_count,
            "t3_fuzzy_count": t3_count,
            "t4_batch_count": t4_count,
            "total_matched": total_matched,
            "total_breaks": total_breaks,
            "auto_resolved_breaks": auto_resolved_breaks,
            "pending_review_breaks": pending_review_breaks,
            "exact_baseline_pct": round(exact_baseline_pct, 2),
            "autoclear_rate_pct": round(autoclear_rate_pct, 2),
            "lift_pct": round(lift_pct, 2)
        }

    def evaluate_ground_truth(self):
        """
        Compares matched transactions and classified breaks against
        the ground_truth_labels table.
        """
        gt_total = self.engine.fetch_one("SELECT COUNT(*) AS cnt FROM ground_truth_labels")["cnt"]
        if not gt_total:
            return {"status": "No ground truth table populated."}

        # 1. Matching evaluation
        # Ground truth matches expected vs actually matched via norm_ledger status
        gt_eval = self.engine.fetch_all("""
        SELECT 
            gt.true_relation,
            gt.expected_tier,
            COUNT(*) AS total_gt,
            COUNT(nl.match_id) AS correct_matches
        FROM ground_truth_labels gt
        LEFT JOIN norm_ledger nl 
            ON gt.ledger_id = nl.item_id AND nl.is_matched = 1
        WHERE gt.expected_tier != 'BREAK'
        GROUP BY gt.true_relation, gt.expected_tier;
        """)

        # Precision & Recall on matches
        tp_matches = sum(r["correct_matches"] for r in gt_eval)
        total_gt_matches = sum(r["total_gt"] for r in gt_eval)
        total_engine_matches = self.engine.fetch_one("SELECT COUNT(*) AS cnt FROM norm_ledger WHERE is_matched = 1")["cnt"]

        match_precision = min(100.0, (tp_matches / total_engine_matches * 100.0)) if total_engine_matches else 100.0
        match_recall = min(100.0, (tp_matches / total_gt_matches * 100.0)) if total_gt_matches else 0.0
        match_f1 = (2 * match_precision * match_recall / (match_precision + match_recall)) if (match_precision + match_recall) else 0.0

        # 2. Break classification evaluation
        break_eval = self.engine.fetch_all("""
        SELECT 
            gt.expected_break_type,
            COUNT(*) AS total_expected,
            COUNT(b.break_id) AS correctly_classified
        FROM ground_truth_labels gt
        LEFT JOIN reconciliation_breaks b 
            ON (gt.ledger_id = b.item_id OR gt.bank_id = b.item_id)
           AND gt.expected_break_type = b.break_category
        WHERE gt.expected_tier = 'BREAK'
        GROUP BY gt.expected_break_type;
        """)

        return {
            "ground_truth_records": gt_total,
            "match_precision": round(match_precision, 2),
            "match_recall": round(match_recall, 2),
            "match_f1": round(match_f1, 2),
            "tier_breakdown": gt_eval,
            "break_classification_breakdown": break_eval
        }
