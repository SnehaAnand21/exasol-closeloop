# Contributing to CloseLoop

Thank you for your interest in contributing to CloseLoop!

## Open-Source Principles
- **License:** MIT License. All contributions are licensed under the MIT License.
- **Scope:** CloseLoop is an in-database reconciliation engine built for the **Exasol Open Build Challenge** (India), Track 01: Money, Risk & Regulation.
- **In-Database Execution:** All matching, windowing, and transformation logic MUST run inside Exasol SQL. Python must remain a thin orchestration and telemetry layer.
- **Synthetic Data Only:** Under no circumstances should proprietary, employer, or real PII data be added to this repository. All tests must rely on seeded synthetic data generators (`data_gen/generate_data.py`).

## Pull Request Guidelines
1. Fork the repo and create a feature branch (`git checkout -b feature/my-feature`).
2. Ensure all unit and integration tests pass: `python tests/run_all_tests.py`.
3. Verify that re-running the pipeline produces deterministic, idempotent results.
4. Keep commit messages concise, descriptive, and clean.
5. Open a Pull Request referencing the relevant issue.
