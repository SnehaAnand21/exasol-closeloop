# CloseLoop: Deployment & Environment Setup Guide

This guide covers setting up CloseLoop with **Exasol Personal** (as required by the Exasol Open Build Challenge rules), setting up environment variables, and running the system in under 5 minutes.

---

## 1. Exasol Personal Setup (Official Platform)

Per challenge rules, **Exasol Personal MUST be the project's data platform** for the submitted benchmark numbers, screenshots, and live demo.

### Option A: Exasol Personal Cloud (Recommended by Exasol)
1. Register for a free Exasol Personal SaaS / Cloud instance at [cloud.exasol.com](https://cloud.exasol.com).
2. Create a new Personal Database cluster (takes ~3 minutes to provision).
3. Under cluster settings, note your:
   - **Host Name / Endpoint:** (e.g., `cluster-abc.cloud.exasol.com`)
   - **Port:** `8563`
   - **Username:** `sys` (or your database user)
   - **Password:** `<your_password>`
4. Ensure TLS/Encryption is enabled (`EXASOL_ENCRYPTION=True`).

### Option B: Local Exasol Docker Image (Permitted for Offline Dev Only)
Per hackathon rules, a local Exasol Docker image is permitted for offline development only:
```bash
# Pull official Exasol docker image
docker run --name exasol-db -p 8563:8563 -d exasol/docker-db:latest

# Wait ~45 seconds for Exasol to initialize
docker logs -f exasol-db
```

### Option C: CloseLoop In-Memory SQL Simulator (Instant Zero-Setup Test Mode)
If you clone this repository on a machine without active cloud credentials or Docker daemon, CloseLoop includes a 100% feature-compatible SQL execution simulator. It executes the exact same schema, regex normalisation, Levenshtein distance metrics, and set-based matching tiers in pure in-memory SQL without any setup required!

---

## 2. Environment Variables (`.env`)

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Configure your parameters:
```ini
# =============================================================================
# CloseLoop: Environment Configuration
# =============================================================================

# Exasol Personal Connection Parameters
EXASOL_HOST=localhost
EXASOL_PORT=8563
EXASOL_USER=sys
EXASOL_PASSWORD=exasol
EXASOL_SCHEMA=CLOSELOOP
EXASOL_ENCRYPTION=True

# Engine Mode: Set to True to force local offline simulator mode
CLOSELOOP_FORCE_LOCAL=False

# Operational Reconciliation Thresholds
CONFIDENCE_THRESHOLD=0.90
MAX_SETTLEMENT_LAG_DAYS=3
MAX_ROUNDING_TOLERANCE=0.05
MAX_FUZZY_EDIT_DISTANCE=2

# Web Console Settings
PORT=8501
```

---

## 3. Installation & Dependency Setup

### Prerequisites
- Python 3.10+ (Python 3.10, 3.11, 3.12, 3.13, 3.14 supported)
- `pip` package manager

### Install Dependencies
```bash
# Install core Python dependencies
pip install -r requirements.txt
```

If you only want to run the zero-dependency web dashboard without installing third-party packages, CloseLoop supports running directly with standard library Python!

---

## 4. One-Command Quickstart

To run the entire pipeline, execute tests, and launch the interactive web dashboard:
```bash
# Using Makefile
make all

# Or manually:
python data_gen/generate_data.py --scale 10000
python tests/run_verification.py
python app/standalone_server.py
```

The interactive dashboard will be live at `http://localhost:8501`!
