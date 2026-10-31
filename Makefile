# CloseLoop: Developer and Evaluator Makefile

.PHONY: all setup data run test benchmark demo deck clean

# Default target: generate data, run verification, and launch app
all: data test demo

# Generate 10k synthetic multi-party transaction dataset with ground truth
data:
	python data_gen/generate_data.py --scale 10000 --output data

# Run full in-database reconciliation pipeline and print KPI report
run:
	python tests/run_verification.py

# Run master unit and integration test suite
test:
	python tests/run_all_tests.py

# Run scale benchmark (Exasol vs Pandas)
benchmark:
	python src/benchmark.py --scale 10000

# Launch interactive web dashboard (Zero-dependency or Streamlit)
demo:
	python app/standalone_server.py

# Build PowerPoint Pitch Deck (.pptx)
deck:
	python docs/generate_pitch_deck.py

# Clean generated data and temporary files
clean:
	rm -rf data data_bench data_test_temp __pycache__ src/__pycache__ tests/__pycache__ app/__pycache__
