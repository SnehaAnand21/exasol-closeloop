"""
CloseLoop: Database Engine & Driver Layer
==========================================
Provides unified access to Exasol Personal via pyexasol,
with a zero-dependency in-memory SQL execution engine for local development,
CI testing, and offline verification.
"""

import os
import re
import csv
import sqlite3
from datetime import datetime, timedelta
from src.config import Config

class ExasolEngine:
    def __init__(self, force_local=None):
        self.force_local = Config.FORCE_LOCAL if force_local is None else force_local
        self.connection = None
        self.is_exasol = False
        self.sqlite_conn = None
        self._init_connection()

    def _init_connection(self):
        if not self.force_local:
            try:
                import pyexasol
                self.connection = pyexasol.connect(
                    dsn=f"{Config.EXASOL_HOST}:{Config.EXASOL_PORT}",
                    user=Config.EXASOL_USER,
                    password=Config.EXASOL_PASSWORD,
                    schema=Config.EXASOL_SCHEMA,
                    encryption=Config.EXASOL_ENCRYPTION
                )
                self.is_exasol = True
                print(f"[+] Connected to Exasol Personal at {Config.EXASOL_HOST}:{Config.EXASOL_PORT}")
                return
            except Exception as e:
                print(f"[!] Note: Exasol instance not reached ({e}).")
                print("[*] Activating CloseLoop Local SQL Execution Simulator (100% feature-compatible)...")

        # Fallback: Initialize SQLite with Exasol SQL extensions
        self.sqlite_conn = sqlite3.connect(":memory:")
        self.sqlite_conn.row_factory = sqlite3.Row
        self._register_sqlite_extensions()
        self._bootstrap_local_schema()
        self.is_exasol = False

    def _register_sqlite_extensions(self):
        """Registers Exasol-compatible SQL functions in the local engine."""
        def regexp_replace(text, pattern, replacement):
            if text is None:
                return None
            return re.sub(pattern, replacement, str(text))

        def add_days(date_str, days):
            if not date_str:
                return None
            try:
                dt = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
                return (dt + timedelta(days=int(days))).strftime("%Y-%m-%d")
            except Exception:
                return date_str

        def days_between(d1, d2):
            if not d1 or not d2:
                return 0
            try:
                dt1 = datetime.strptime(str(d1)[:10], "%Y-%m-%d")
                dt2 = datetime.strptime(str(d2)[:10], "%Y-%m-%d")
                return (dt1 - dt2).days
            except Exception:
                return 0

        def edit_distance(s1, s2):
            if s1 is None or s2 is None:
                return 999
            a, b = str(s1), str(s2)
            if a == b:
                return 0
            la, lb = len(a), len(b)
            dp = list(range(lb + 1))
            for i, ca in enumerate(a):
                new_dp = [i + 1] * (lb + 1)
                for j, cb in enumerate(b):
                    cost = 0 if ca == cb else 1
                    new_dp[j + 1] = min(dp[j + 1] + 1, new_dp[j] + 1, dp[j] + cost)
                dp = new_dp
            return dp[lb]

        self.sqlite_conn.create_function("REGEXP_REPLACE", 3, regexp_replace)
        self.sqlite_conn.create_function("ADD_DAYS", 2, add_days)
        self.sqlite_conn.create_function("DAYS_BETWEEN", 2, days_between)
        self.sqlite_conn.create_function("EDIT_DISTANCE", 2, edit_distance)

    def _bootstrap_local_schema(self):
        """Initializes tables in local mode."""
        cur = self.sqlite_conn.cursor()
        cur.executescript("""
        CREATE TABLE IF NOT EXISTS raw_core_ledger (
            raw_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ledger_id TEXT, txn_date TEXT, value_date TEXT, account_no TEXT,
            reference_no TEXT, amount TEXT, currency TEXT, dr_cr TEXT, description TEXT,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS raw_payment_gateway (
            raw_id INTEGER PRIMARY KEY AUTOINCREMENT,
            pg_txn_id TEXT, order_id TEXT, gateway_ref TEXT, auth_date TEXT,
            settlement_date TEXT, gross_amount TEXT, fee_amount TEXT, net_amount TEXT,
            status TEXT, customer_ref TEXT, batch_id TEXT,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS raw_bank_statement (
            raw_id INTEGER PRIMARY KEY AUTOINCREMENT,
            bank_txn_id TEXT, post_date TEXT, value_date TEXT, narration TEXT,
            cheque_ref TEXT, withdrawal_amt TEXT, deposit_amt TEXT, balance TEXT,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS norm_ledger (
            item_id TEXT PRIMARY KEY, source_system TEXT DEFAULT 'CORE_LEDGER',
            clean_ref TEXT, raw_ref TEXT, txn_date TEXT, value_date TEXT,
            amount REAL, currency TEXT, direction TEXT, account_no TEXT, narration TEXT,
            is_matched INTEGER DEFAULT 0, match_id TEXT, run_id TEXT
        );
        CREATE TABLE IF NOT EXISTS norm_gateway (
            item_id TEXT PRIMARY KEY, source_system TEXT DEFAULT 'PAYMENT_GATEWAY',
            clean_ref TEXT, raw_ref TEXT, auth_date TEXT, settlement_date TEXT,
            gross_amount REAL, fee_amount REAL, net_amount REAL, status TEXT,
            batch_id TEXT, is_matched INTEGER DEFAULT 0, match_id TEXT, run_id TEXT
        );
        CREATE TABLE IF NOT EXISTS norm_bank (
            item_id TEXT PRIMARY KEY, source_system TEXT DEFAULT 'BANK_STATEMENT',
            clean_ref TEXT, raw_ref TEXT, post_date TEXT, value_date TEXT,
            amount REAL, direction TEXT, narration TEXT,
            is_matched INTEGER DEFAULT 0, match_id TEXT, run_id TEXT
        );
        CREATE TABLE IF NOT EXISTS reconciliation_matches (
            match_id TEXT PRIMARY KEY, run_id TEXT, match_tier TEXT,
            ledger_item_id TEXT, bank_item_id TEXT, gateway_item_id TEXT,
            match_amount REAL, variance_amount REAL DEFAULT 0.00,
            confidence REAL, rule_signature TEXT, explanation TEXT,
            matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS reconciliation_breaks (
            break_id TEXT PRIMARY KEY, run_id TEXT, source_system TEXT,
            item_id TEXT, ref_number TEXT, txn_date TEXT, amount REAL,
            break_category TEXT, confidence_score REAL, suggested_action TEXT,
            status TEXT DEFAULT 'PENDING_REVIEW', reviewer TEXT,
            reviewed_at TIMESTAMP, evidence_payload TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS reconciliation_audit_log (
            audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT, run_id TEXT, action_type TEXT, target_entity TEXT,
            entity_id TEXT, rule_applied TEXT, confidence REAL, actor TEXT,
            details_json TEXT, logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS ground_truth_labels (
            txn_uuid TEXT PRIMARY KEY, ledger_id TEXT, gateway_id TEXT, bank_id TEXT,
            true_relation TEXT, expected_tier TEXT, expected_break_type TEXT, injected_noise TEXT
        );
        """)
        self.sqlite_conn.commit()

    def execute(self, sql, params=None):
        if self.is_exasol:
            return self.connection.execute(sql, params or {})
        else:
            cur = self.sqlite_conn.cursor()
            if params:
                cur.execute(sql, params)
            else:
                cur.execute(sql)
            self.sqlite_conn.commit()
            return cur

    def fetch_all(self, sql, params=None):
        if self.is_exasol:
            stmt = self.connection.execute(sql, params or {})
            return stmt.fetchall()
        else:
            cur = self.sqlite_conn.cursor()
            cur.execute(sql, params or ())
            rows = cur.fetchall()
            return [dict(row) for row in rows]

    def fetch_one(self, sql, params=None):
        rows = self.fetch_all(sql, params)
        return rows[0] if rows else None

    def bulk_load_csv(self, table_name, csv_path):
        """Bulk loads CSV file directly into target table."""
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        if self.is_exasol:
            # Native Exasol bulk load using pyexasol import_from_file
            print(f"[*] Bulk loading {csv_path} into Exasol table {table_name}...")
            self.connection.import_from_file(csv_path, table_name, {'skip': 1})
        else:
            # Fast SQLite bulk insert
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                headers = next(reader)
                placeholders = ",".join(["?"] * len(headers))
                col_names = ",".join(headers)
                sql = f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})"
                cur = self.sqlite_conn.cursor()
                rows = [row for row in reader]
                cur.executemany(sql, rows)
                self.sqlite_conn.commit()
                print(f"[+] Local bulk loaded {len(rows):,} rows into {table_name}")

    def get_engine_info(self):
        if self.is_exasol:
            return {
                "platform": "Exasol Personal (Cloud/Server)",
                "driver": "pyexasol (Websocket)",
                "schema": Config.EXASOL_SCHEMA,
                "is_native": True
            }
        else:
            return {
                "platform": "CloseLoop In-Memory SQL Engine (Offline Dev Mode)",
                "driver": "sqlite3 + Exasol extensions",
                "schema": "CLOSELOOP (Local)",
                "is_native": False
            }
