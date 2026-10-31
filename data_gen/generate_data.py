#!/usr/bin/env python3
"""
CloseLoop: Synthetic Financial Reconciliation Data Generator
=============================================================
Generates 3 realistic synthetic feeds:
  1. Core Ledger (CSV)
  2. Payment Gateway (JSON or CSV)
  3. Bank Statement (CSV)
Plus an exact Ground-Truth Table (CSV) with deterministic break types and noise injection.

No proprietary data, no real PII. Fully reproducible with seeded PRNG.
"""

import os
import sys
import csv
import json
import random
import argparse
from datetime import datetime, timedelta

def generate_reference(prefix, num, noise_type=None):
    """Generates realistic transaction references with noise options."""
    base_ref = f"{prefix}{num:08d}"
    if noise_type == "prefix_noise":
        var = random.choice(["REF#", "TXN:", "UTR-", "INV/", "CHQ:"])
        return f"{var}{base_ref}"
    elif noise_type == "case_space":
        return f" {base_ref.lower()} "
    elif noise_type == "typo":
        # mutate one character (e.g., '8' -> 'B', '0' -> 'O', '1' -> 'I')
        chars = list(base_ref)
        idx = random.randint(len(prefix), len(chars) - 1)
        sub_map = {'0': 'O', '1': 'I', '8': 'B', '5': 'S', '2': 'Z'}
        chars[idx] = sub_map.get(chars[idx], 'X')
        return "".join(chars)
    elif noise_type == "extra_char":
        return f"{base_ref}X"
    return base_ref

def generate_dataset(num_records=10000, output_dir="data", seed=42):
    """
    Generates synthetic datasets with realistic break profiles and ground truth labels.
    """
    random.seed(seed)
    os.makedirs(output_dir, exist_ok=True)

    base_date = datetime(2026, 10, 1)
    
    # Target proportions
    # 60% Tier 1 (Exact)
    # 18% Tier 2 (Lag, MDR Fee, Rounding)
    # 10% Tier 3 (Fuzzy reference typo / OCR error)
    # 6% Tier 4 (Many-to-one batch settlements)
    # 6% Residual Breaks (Timing, Dup, Wrong Amt, Missing GL, Fraud Pattern)

    ledger_rows = []
    gateway_rows = []
    bank_rows = []
    ground_truth = []

    running_bank_balance = 50000000.00
    batch_counter = 1000

    print(f"[*] Generating {num_records} transaction records into '{output_dir}' (Seed: {seed})...")

    # Keep track of batch accumulators for Tier 4
    batch_payouts = {}

    for i in range(1, num_records + 1):
        txn_uuid = f"UUID_{i:09d}"
        roll = random.random()
        
        # Base transaction attributes
        day_offset = random.randint(0, 29)
        txn_date = base_date + timedelta(days=day_offset)
        amount = round(random.uniform(100.0, 75000.0), 2)
        account_no = f"ACC_{random.randint(100001, 100500)}"
        clean_ref_base = f"UTR{i:08d}"

        # ---------------------------------------------------------------------
        # SCENARIO 1: TIER 1 EXACT MATCH (~60%)
        # ---------------------------------------------------------------------
        if roll < 0.60:
            ledger_ref = generate_reference("UTR", i, noise_type=random.choice(["prefix_noise", "case_space", None]))
            bank_ref = generate_reference("UTR", i, noise_type="prefix_noise" if "UTR-" not in ledger_ref else None)
            
            # Core Ledger
            ledger_id = f"GL_{i:08d}"
            ledger_rows.append({
                "ledger_id": ledger_id,
                "txn_date": txn_date.strftime("%Y-%m-%d"),
                "value_date": txn_date.strftime("%Y-%m-%d"),
                "account_no": account_no,
                "reference_no": ledger_ref,
                "amount": f"{amount:.2f}",
                "currency": "INR",
                "dr_cr": "CR",
                "description": f"Customer Payment Ref {ledger_ref}"
            })

            # Payment Gateway
            pg_id = f"PG_{i:08d}"
            fee = round(amount * 0.015, 2)
            gateway_rows.append({
                "pg_txn_id": pg_id,
                "order_id": f"ORD_{i:08d}",
                "gateway_ref": ledger_ref,
                "auth_date": txn_date.strftime("%Y-%m-%d"),
                "settlement_date": txn_date.strftime("%Y-%m-%d"),
                "gross_amount": f"{amount:.2f}",
                "fee_amount": f"{fee:.2f}",
                "net_amount": f"{(amount - fee):.2f}",
                "status": "CAPTURED",
                "customer_ref": f"CUST_{random.randint(1000, 9999)}",
                "batch_id": f"BATCH_{day_offset:03d}"
            })

            # Bank Statement
            bank_id = f"BNK_{i:08d}"
            running_bank_balance += amount
            bank_rows.append({
                "bank_txn_id": bank_id,
                "post_date": txn_date.strftime("%Y-%m-%d"),
                "value_date": txn_date.strftime("%Y-%m-%d"),
                "narration": f"NEFT CR-{bank_ref}-SETTLEMENT",
                "cheque_ref": bank_ref,
                "withdrawal_amt": "",
                "deposit_amt": f"{amount:.2f}",
                "balance": f"{running_bank_balance:.2f}"
            })

            ground_truth.append({
                "txn_uuid": txn_uuid,
                "ledger_id": ledger_id,
                "gateway_id": pg_id,
                "bank_id": bank_id,
                "true_relation": "EXACT_MATCH",
                "expected_tier": "TIER_1",
                "expected_break_type": "NONE",
                "injected_noise": "Prefix/Whitespace normalisation only"
            })

        # ---------------------------------------------------------------------
        # SCENARIO 2: TIER 2 RULES - SETTLEMENT LAG & FEES (~18%)
        # ---------------------------------------------------------------------
        elif roll < 0.78:
            sub_type = random.choice(["LAG", "FEE", "ROUNDING"])
            ledger_id = f"GL_{i:08d}"
            bank_id = f"BNK_{i:08d}"
            pg_id = f"PG_{i:08d}"
            ref = generate_reference("UTR", i)

            if sub_type == "LAG":
                lag_days = random.randint(1, 3)
                settle_date = txn_date + timedelta(days=lag_days)
                ledger_rows.append({
                    "ledger_id": ledger_id,
                    "txn_date": txn_date.strftime("%Y-%m-%d"),
                    "value_date": txn_date.strftime("%Y-%m-%d"),
                    "account_no": account_no,
                    "reference_no": ref,
                    "amount": f"{amount:.2f}",
                    "currency": "INR",
                    "dr_cr": "CR",
                    "description": f"Merchant Payout Lag T+{lag_days}"
                })
                running_bank_balance += amount
                bank_rows.append({
                    "bank_txn_id": bank_id,
                    "post_date": settle_date.strftime("%Y-%m-%d"),
                    "value_date": settle_date.strftime("%Y-%m-%d"),
                    "narration": f"RTGS INFLOW {ref} VALUE {settle_date.strftime('%Y-%m-%d')}",
                    "cheque_ref": ref,
                    "withdrawal_amt": "",
                    "deposit_amt": f"{amount:.2f}",
                    "balance": f"{running_bank_balance:.2f}"
                })
                ground_truth.append({
                    "txn_uuid": txn_uuid,
                    "ledger_id": ledger_id,
                    "gateway_id": "",
                    "bank_id": bank_id,
                    "true_relation": f"SETTLEMENT_LAG_T{lag_days}",
                    "expected_tier": "TIER_2",
                    "expected_break_type": "NONE",
                    "injected_noise": f"T+{lag_days} settlement calendar lag"
                })

            elif sub_type == "FEE":
                fee_rate = random.uniform(0.015, 0.025)
                fee = round(amount * fee_rate, 2)
                net = round(amount - fee, 2)
                settle_date = txn_date + timedelta(days=1)
                
                ledger_rows.append({
                    "ledger_id": ledger_id,
                    "txn_date": txn_date.strftime("%Y-%m-%d"),
                    "value_date": txn_date.strftime("%Y-%m-%d"),
                    "account_no": account_no,
                    "reference_no": ref,
                    "amount": f"{amount:.2f}",
                    "currency": "INR",
                    "dr_cr": "CR",
                    "description": "Gross Sale Entry"
                })
                gateway_rows.append({
                    "pg_txn_id": pg_id,
                    "order_id": f"ORD_{i:08d}",
                    "gateway_ref": ref,
                    "auth_date": txn_date.strftime("%Y-%m-%d"),
                    "settlement_date": settle_date.strftime("%Y-%m-%d"),
                    "gross_amount": f"{amount:.2f}",
                    "fee_amount": f"{fee:.2f}",
                    "net_amount": f"{net:.2f}",
                    "status": "SETTLED",
                    "customer_ref": f"CUST_{i}",
                    "batch_id": f"BATCH_{day_offset:03d}"
                })
                running_bank_balance += net
                bank_rows.append({
                    "bank_txn_id": bank_id,
                    "post_date": settle_date.strftime("%Y-%m-%d"),
                    "value_date": settle_date.strftime("%Y-%m-%d"),
                    "narration": f"PG SETTLEMENT NET {ref}",
                    "cheque_ref": ref,
                    "withdrawal_amt": "",
                    "deposit_amt": f"{net:.2f}",
                    "balance": f"{running_bank_balance:.2f}"
                })
                ground_truth.append({
                    "txn_uuid": txn_uuid,
                    "ledger_id": ledger_id,
                    "gateway_id": pg_id,
                    "bank_id": bank_id,
                    "true_relation": "FEE_VARIATION",
                    "expected_tier": "TIER_2",
                    "expected_break_type": "NONE",
                    "injected_noise": f"MDR Fee deduction of {fee:.2f} INR"
                })

            else: # ROUNDING
                delta = random.choice([-0.02, -0.01, 0.01, 0.02])
                bank_amount = round(amount + delta, 2)
                ledger_rows.append({
                    "ledger_id": ledger_id,
                    "txn_date": txn_date.strftime("%Y-%m-%d"),
                    "value_date": txn_date.strftime("%Y-%m-%d"),
                    "account_no": account_no,
                    "reference_no": ref,
                    "amount": f"{amount:.2f}",
                    "currency": "INR",
                    "dr_cr": "CR",
                    "description": "Invoice Receipt"
                })
                running_bank_balance += bank_amount
                bank_rows.append({
                    "bank_txn_id": bank_id,
                    "post_date": txn_date.strftime("%Y-%m-%d"),
                    "value_date": txn_date.strftime("%Y-%m-%d"),
                    "narration": f"IMPS INFLOW {ref}",
                    "cheque_ref": ref,
                    "withdrawal_amt": "",
                    "deposit_amt": f"{bank_amount:.2f}",
                    "balance": f"{running_bank_balance:.2f}"
                })
                ground_truth.append({
                    "txn_uuid": txn_uuid,
                    "ledger_id": ledger_id,
                    "gateway_id": "",
                    "bank_id": bank_id,
                    "true_relation": "ROUNDING_TOLERANCE",
                    "expected_tier": "TIER_2",
                    "expected_break_type": "NONE",
                    "injected_noise": f"Penny rounding delta {delta:.2f}"
                })

        # ---------------------------------------------------------------------
        # SCENARIO 3: TIER 3 FUZZY MATCH (~10%)
        # ---------------------------------------------------------------------
        elif roll < 0.88:
            ledger_id = f"GL_{i:08d}"
            bank_id = f"BNK_{i:08d}"
            clean_ref = f"UTR{i:08d}"
            # Mutate bank reference with single OCR or typo error
            bank_ref = generate_reference("UTR", i, noise_type="typo")
            lag_days = random.randint(0, 2)
            settle_date = txn_date + timedelta(days=lag_days)

            ledger_rows.append({
                "ledger_id": ledger_id,
                "txn_date": txn_date.strftime("%Y-%m-%d"),
                "value_date": txn_date.strftime("%Y-%m-%d"),
                "account_no": account_no,
                "reference_no": clean_ref,
                "amount": f"{amount:.2f}",
                "currency": "INR",
                "dr_cr": "CR",
                "description": "Direct Client Remittance"
            })
            running_bank_balance += amount
            bank_rows.append({
                "bank_txn_id": bank_id,
                "post_date": settle_date.strftime("%Y-%m-%d"),
                "value_date": settle_date.strftime("%Y-%m-%d"),
                "narration": f"CLEARING {bank_ref}",
                "cheque_ref": bank_ref,
                "withdrawal_amt": "",
                "deposit_amt": f"{amount:.2f}",
                "balance": f"{running_bank_balance:.2f}"
            })
            ground_truth.append({
                "txn_uuid": txn_uuid,
                "ledger_id": ledger_id,
                "gateway_id": "",
                "bank_id": bank_id,
                "true_relation": "TYPO_REF",
                "expected_tier": "TIER_3",
                "expected_break_type": "NONE",
                "injected_noise": f"Typo in bank reference: {clean_ref} -> {bank_ref}"
            })

        # ---------------------------------------------------------------------
        # SCENARIO 4: TIER 4 MANY-TO-ONE BATCH SETTLEMENTS (~6%)
        # ---------------------------------------------------------------------
        elif roll < 0.94:
            batch_id = f"BSETTLE_{batch_counter}"
            batch_counter += (1 if random.random() < 0.25 else 0) # cluster ~4 txns per batch
            ledger_id = f"GL_{i:08d}"
            pg_id = f"PG_{i:08d}"
            ref = f"ORD{i:08d}"
            fee = round(amount * 0.018, 2)
            net = round(amount - fee, 2)

            ledger_rows.append({
                "ledger_id": ledger_id,
                "txn_date": txn_date.strftime("%Y-%m-%d"),
                "value_date": txn_date.strftime("%Y-%m-%d"),
                "account_no": account_no,
                "reference_no": ref,
                "amount": f"{amount:.2f}",
                "currency": "INR",
                "dr_cr": "CR",
                "description": f"Merchant Batch Item {batch_id}"
            })
            gateway_rows.append({
                "pg_txn_id": pg_id,
                "order_id": ref,
                "gateway_ref": ref,
                "auth_date": txn_date.strftime("%Y-%m-%d"),
                "settlement_date": (txn_date + timedelta(days=1)).strftime("%Y-%m-%d"),
                "gross_amount": f"{amount:.2f}",
                "fee_amount": f"{fee:.2f}",
                "net_amount": f"{net:.2f}",
                "status": "SETTLED",
                "customer_ref": f"CUST_{i}",
                "batch_id": batch_id
            })

            if batch_id not in batch_payouts:
                batch_payouts[batch_id] = {
                    "total_net": 0.0,
                    "date": txn_date + timedelta(days=1),
                    "items": []
                }
            batch_payouts[batch_id]["total_net"] += net
            batch_payouts[batch_id]["items"].append((ledger_id, pg_id))

            ground_truth.append({
                "txn_uuid": txn_uuid,
                "ledger_id": ledger_id,
                "gateway_id": pg_id,
                "bank_id": f"BNK_BATCH_{batch_id}",
                "true_relation": "BATCH_SETTLEMENT",
                "expected_tier": "TIER_4",
                "expected_break_type": "NONE",
                "injected_noise": f"Aggregated under daily batch payout {batch_id}"
            })

        # ---------------------------------------------------------------------
        # SCENARIO 5: TRUE BREAKS & EXCEPTIONS (~6%)
        # ---------------------------------------------------------------------
        else:
            break_choice = random.choice([
                "TIMING_LAG", "FEE_DISCREPANCY", "DUPLICATE_ENTRY", 
                "WRONG_AMOUNT", "MISSING_LEDGER_ENTRY", "SUSPECTED_FRAUD_PATTERN"
            ])
            ref = generate_reference("UTR", i)

            if break_choice == "TIMING_LAG":
                # Transaction on day 29/30 with no bank entry yet
                cutoff_date = base_date + timedelta(days=29)
                ledger_id = f"GL_{i:08d}"
                ledger_rows.append({
                    "ledger_id": ledger_id,
                    "txn_date": cutoff_date.strftime("%Y-%m-%d"),
                    "value_date": cutoff_date.strftime("%Y-%m-%d"),
                    "account_no": account_no,
                    "reference_no": ref,
                    "amount": f"{amount:.2f}",
                    "currency": "INR",
                    "dr_cr": "CR",
                    "description": "Late month-end cutoff posting"
                })
                ground_truth.append({
                    "txn_uuid": txn_uuid,
                    "ledger_id": ledger_id,
                    "gateway_id": "",
                    "bank_id": "",
                    "true_relation": "BREAK",
                    "expected_tier": "BREAK",
                    "expected_break_type": "TIMING_LAG",
                    "injected_noise": "Cutoff lag: bank settlement pending in next fiscal month"
                })

            elif break_choice == "DUPLICATE_ENTRY":
                # Double booking in core GL
                ledger_id_1 = f"GL_{i:08d}A"
                ledger_id_2 = f"GL_{i:08d}B"
                for lid in [ledger_id_1, ledger_id_2]:
                    ledger_rows.append({
                        "ledger_id": lid,
                        "txn_date": txn_date.strftime("%Y-%m-%d"),
                        "value_date": txn_date.strftime("%Y-%m-%d"),
                        "account_no": account_no,
                        "reference_no": ref,
                        "amount": f"{amount:.2f}",
                        "currency": "INR",
                        "dr_cr": "CR",
                        "description": "Duplicate GL journal entry"
                    })
                ground_truth.append({
                    "txn_uuid": txn_uuid,
                    "ledger_id": ledger_id_2,
                    "gateway_id": "",
                    "bank_id": "",
                    "true_relation": "BREAK",
                    "expected_tier": "BREAK",
                    "expected_break_type": "DUPLICATE_ENTRY",
                    "injected_noise": "Duplicate GL journal entry created by upstream retry"
                })

            elif break_choice == "WRONG_AMOUNT":
                # Major amount discrepancy / digit transposition
                ledger_id = f"GL_{i:08d}"
                bank_id = f"BNK_{i:08d}"
                wrong_amount = round(amount * 1.5, 2)
                ledger_rows.append({
                    "ledger_id": ledger_id,
                    "txn_date": txn_date.strftime("%Y-%m-%d"),
                    "value_date": txn_date.strftime("%Y-%m-%d"),
                    "account_no": account_no,
                    "reference_no": ref,
                    "amount": f"{amount:.2f}",
                    "currency": "INR",
                    "dr_cr": "CR",
                    "description": "Vendor Payment"
                })
                running_bank_balance += wrong_amount
                bank_rows.append({
                    "bank_txn_id": bank_id,
                    "post_date": txn_date.strftime("%Y-%m-%d"),
                    "value_date": txn_date.strftime("%Y-%m-%d"),
                    "narration": f"NEFT DR {ref}",
                    "cheque_ref": ref,
                    "withdrawal_amt": "",
                    "deposit_amt": f"{wrong_amount:.2f}",
                    "balance": f"{running_bank_balance:.2f}"
                })
                ground_truth.append({
                    "txn_uuid": txn_uuid,
                    "ledger_id": ledger_id,
                    "gateway_id": "",
                    "bank_id": bank_id,
                    "true_relation": "BREAK",
                    "expected_tier": "BREAK",
                    "expected_break_type": "WRONG_AMOUNT",
                    "injected_noise": f"Amount mismatch: GL {amount} vs Bank {wrong_amount}"
                })

            elif break_choice == "MISSING_LEDGER_ENTRY":
                # Direct bank charge or interest credit
                bank_id = f"BNK_{i:08d}"
                running_bank_balance -= 850.00
                bank_rows.append({
                    "bank_txn_id": bank_id,
                    "post_date": txn_date.strftime("%Y-%m-%d"),
                    "value_date": txn_date.strftime("%Y-%m-%d"),
                    "narration": "BANK CHARGE / CONSOLIDATED AMC FEES",
                    "cheque_ref": f"CHG{i:06d}",
                    "withdrawal_amt": "850.00",
                    "deposit_amt": "",
                    "balance": f"{running_bank_balance:.2f}"
                })
                ground_truth.append({
                    "txn_uuid": txn_uuid,
                    "ledger_id": "",
                    "gateway_id": "",
                    "bank_id": bank_id,
                    "true_relation": "BREAK",
                    "expected_tier": "BREAK",
                    "expected_break_type": "MISSING_LEDGER_ENTRY",
                    "injected_noise": "Direct bank charge unbooked in GL"
                })

            elif break_choice == "SUSPECTED_FRAUD_PATTERN":
                # Round amount just below 50,000 threshold
                bank_id = f"BNK_{i:08d}"
                fraud_amount = 49999.00
                running_bank_balance += fraud_amount
                bank_rows.append({
                    "bank_txn_id": bank_id,
                    "post_date": txn_date.strftime("%Y-%m-%d"),
                    "value_date": txn_date.strftime("%Y-%m-%d"),
                    "narration": f"CASH / SUSPECT STRUCTURING REF {ref}",
                    "cheque_ref": ref,
                    "withdrawal_amt": "",
                    "deposit_amt": f"{fraud_amount:.2f}",
                    "balance": f"{running_bank_balance:.2f}"
                })
                ground_truth.append({
                    "txn_uuid": txn_uuid,
                    "ledger_id": "",
                    "gateway_id": "",
                    "bank_id": bank_id,
                    "true_relation": "BREAK",
                    "expected_tier": "BREAK",
                    "expected_break_type": "SUSPECTED_FRAUD_PATTERN",
                    "injected_noise": "Threshold structuring pattern ₹49,999 without supporting voucher"
                })

    # Materialize aggregate bank deposit rows for Tier 4 batch settlements
    for b_id, b_data in batch_payouts.items():
        total_payout = round(b_data["total_net"], 2)
        running_bank_balance += total_payout
        bank_rows.append({
            "bank_txn_id": f"BNK_BATCH_{b_id}",
            "post_date": b_data["date"].strftime("%Y-%m-%d"),
            "value_date": b_data["date"].strftime("%Y-%m-%d"),
            "narration": f"LUMP SUM PAYMENT GATEWAY BATCH PAYOUT {b_id}",
            "cheque_ref": b_id,
            "withdrawal_amt": "",
            "deposit_amt": f"{total_payout:.2f}",
            "balance": f"{running_bank_balance:.2f}"
        })

    # -------------------------------------------------------------------------
    # WRITE DATA TO DISK
    # -------------------------------------------------------------------------
    # 1. Core Ledger CSV
    gl_path = os.path.join(output_dir, "core_ledger.csv")
    with open(gl_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "ledger_id", "txn_date", "value_date", "account_no",
            "reference_no", "amount", "currency", "dr_cr", "description"
        ])
        writer.writeheader()
        writer.writerows(ledger_rows)

    # 2. Payment Gateway CSV & JSON
    pg_csv_path = os.path.join(output_dir, "payment_gateway.csv")
    with open(pg_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "pg_txn_id", "order_id", "gateway_ref", "auth_date",
            "settlement_date", "gross_amount", "fee_amount", "net_amount",
            "status", "customer_ref", "batch_id"
        ])
        writer.writeheader()
        writer.writerows(gateway_rows)

    pg_json_path = os.path.join(output_dir, "payment_gateway.json")
    with open(pg_json_path, "w", encoding="utf-8") as f:
        json.dump(gateway_rows[:1000], f, indent=2) # sample json slice

    # 3. Bank Statement CSV
    bnk_path = os.path.join(output_dir, "bank_statement.csv")
    with open(bnk_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "bank_txn_id", "post_date", "value_date", "narration",
            "cheque_ref", "withdrawal_amt", "deposit_amt", "balance"
        ])
        writer.writeheader()
        writer.writerows(bank_rows)

    # 4. Ground Truth Labels CSV
    gt_path = os.path.join(output_dir, "ground_truth_labels.csv")
    with open(gt_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "txn_uuid", "ledger_id", "gateway_id", "bank_id",
            "true_relation", "expected_tier", "expected_break_type", "injected_noise"
        ])
        writer.writeheader()
        writer.writerows(ground_truth)

    print(f"[+] Successfully generated:")
    print(f"    - Core Ledger:       {len(ledger_rows):,} rows -> {gl_path}")
    print(f"    - Payment Gateway:   {len(gateway_rows):,} rows -> {pg_csv_path}")
    print(f"    - Bank Statement:    {len(bank_rows):,} rows -> {bnk_path}")
    print(f"    - Ground Truth:      {len(ground_truth):,} labels -> {gt_path}")

    return {
        "ledger_count": len(ledger_rows),
        "gateway_count": len(gateway_rows),
        "bank_count": len(bank_rows),
        "ground_truth_count": len(ground_truth)
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CloseLoop Synthetic Data Generator")
    parser.add_argument("--scale", type=int, default=10000, help="Number of baseline transactions")
    parser.add_argument("--output", type=str, default="data", help="Output directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()

    generate_dataset(num_records=args.scale, output_dir=args.output, seed=args.seed)
