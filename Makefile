# Makefile for Apache Jira Scraper ETL Pipeline
# This file provides convenient commands for common operations

# Default Python interpreter
PYTHON = python

# Default configuration file
CONFIG = config.json

# Default project (if not specified)
PROJECT = 

# Define phony targets (targets that don't represent files)
.PHONY: all extract transform clean clean-all clean-project setup help test test-transformer test-extract

# Default target: run the full pipeline
all:
	$(PYTHON) main.py

# Run only the extraction phase
extract:
	$(PYTHON) main.py --extract

# Run only the transformation phase
transform:
	$(PYTHON) main.py --transform

# Clean checkpoint files and run the pipeline from scratch
clean:
	$(PYTHON) main.py --clean

# Clean checkpoint files for a specific project
# Usage: make clean-project PROJECT=HADOOP
clean-project:
	@if [ -z "$(PROJECT)" ]; then \
		echo "Error: PROJECT is not set. Usage: make clean-project PROJECT=HADOOP"; \
		exit 1; \
	fi
	$(PYTHON) main.py --clean --project $(PROJECT)

# Clean all data directories (raw, processed, checkpoints)
clean-all:
	@echo "Cleaning all data directories..."
	rm -rf data/raw/* data/processed/* data/checkpoints/*
	@echo "Done."

# Run the pipeline for a specific project
# Usage: make project PROJECT=HADOOP
project:
	@if [ -z "$(PROJECT)" ]; then \
		echo "Error: PROJECT is not set. Usage: make project PROJECT=HADOOP"; \
		exit 1; \
	fi
	$(PYTHON) main.py --project $(PROJECT)

# Run the worker process with default settings (6 hours)
worker:
	$(PYTHON) worker.py

# Run the worker process every hour
worker-hourly:
	$(PYTHON) worker.py --interval 1

# Run the worker process with a custom interval
# Usage: make worker-interval INTERVAL=12
worker-interval:
	@if [ -z "$(INTERVAL)" ]; then \
		echo "Error: INTERVAL is not set. Usage: make worker-interval INTERVAL=12"; \
		exit 1; \
	fi
	$(PYTHON) worker.py --interval $(INTERVAL)

# Run the worker as a background process (Linux/macOS)
worker-background:
	nohup $(PYTHON) worker.py --interval 1 > /dev/null 2>&1 &
	@echo "Worker started in background with 1-hour interval. Use 'ps aux | grep worker.py' to check."

# Set up the project environment
setup:
	@echo "Setting up project environment..."
	@if [ -f "setup.sh" ]; then \
		chmod +x setup.sh && ./setup.sh; \
	elif [ -f "setup.bat" ]; then \
		setup.bat; \
	else \
		$(PYTHON) setup.py; \
	fi

# Run all unit tests
test:
	$(PYTHON) -m unittest discover -s tests

# Run transformer unit tests
test-transformer:
	$(PYTHON) -m unittest tests/test_transformer.py

# Run extract unit tests
test-extract:
	$(PYTHON) -m unittest tests/test_extract.py

# Display help information
help:
	@echo "Apache Jira Scraper ETL Pipeline"
	@echo ""
	@echo "Available targets:"
	@echo "  make              Run the full pipeline (extraction + transformation)"
	@echo "  make extract      Run only the extraction phase"
	@echo "  make transform    Run only the transformation phase"
	@echo "  make clean        Clean checkpoint files and run the pipeline from scratch"
	@echo "  make clean-project PROJECT=HADOOP  Clean checkpoint files for a specific project"
	@echo "  make clean-all    Clean all data directories (raw, processed, checkpoints)"
	@echo "  make project PROJECT=HADOOP  Run the pipeline for a specific project"
	@echo "  make worker       Run the worker process with default settings (6 hours)"
	@echo "  make worker-hourly  Run the worker process every hour"
	@echo "  make worker-interval INTERVAL=12  Run the worker process with a custom interval"
	@echo "  make worker-background  Run the worker as a background process (Linux/macOS)"
	@echo "  make test         Run all unit tests"
	@echo "  make test-transformer  Run transformer unit tests"
	@echo "  make test-extract  Run extract unit tests"
	@echo "  make setup        Set up the project environment"
	@echo "  make help         Display this help information"
