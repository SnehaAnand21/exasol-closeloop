"""
CloseLoop: Configuration and Environment Settings
=================================================
Loads database credentials and operational thresholds.
Supports Exasol Personal Cloud, Exasol Docker (local), or Local Simulation Mode.
"""

import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SQL_DIR = BASE_DIR / "sql"
DOCS_DIR = BASE_DIR / "docs"

# Attempt to load .env file if present
env_file = BASE_DIR / ".env"
if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

class Config:
    # Exasol Personal / Cloud / Docker connection parameters
    EXASOL_HOST = os.getenv("EXASOL_HOST", "localhost")
    EXASOL_PORT = int(os.getenv("EXASOL_PORT", "8563"))
    EXASOL_USER = os.getenv("EXASOL_USER", "sys")
    EXASOL_PASSWORD = os.getenv("EXASOL_PASSWORD", "exasol")
    EXASOL_SCHEMA = os.getenv("EXASOL_SCHEMA", "CLOSELOOP")
    EXASOL_ENCRYPTION = os.getenv("EXASOL_ENCRYPTION", "True").lower() in ("true", "1", "yes")

    # Engine execution mode: 'EXASOL' or 'LOCAL_FALLBACK'
    # Automatically falls back to local simulation if pyexasol is not installed or host is unreachable
    FORCE_LOCAL = os.getenv("CLOSELOOP_FORCE_LOCAL", "False").lower() in ("true", "1", "yes")

    # Reconciliation Thresholds
    CONFIDENCE_AUTO_RESOLVE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.90"))
    MAX_SETTLEMENT_LAG_DAYS = int(os.getenv("MAX_SETTLEMENT_LAG_DAYS", "3"))
    MAX_ROUNDING_TOLERANCE = float(os.getenv("MAX_ROUNDING_TOLERANCE", "0.05"))
    MAX_FUZZY_EDIT_DISTANCE = int(os.getenv("MAX_FUZZY_EDIT_DISTANCE", "2"))
