.PHONY: help install install-dev test coverage lint format type-check clean run docs

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python3
PIP := $(PYTHON) -m pip
PYTEST := $(PYTHON) -m pytest
BLACK := $(PYTHON) -m black
ISORT := $(PYTHON) -m isort
FLAKE8 := $(PYTHON) -m flake8
MYPY := $(PYTHON) -m mypy

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	$(PIP) install -r requirements.txt

install-dev: ## Install development dependencies
	$(PIP) install -r requirements-dev.txt
	$(PYTHON) -m pre_commit install

test: ## Run all tests
	$(PYTEST) tests/

test-unit: ## Run only unit tests
	$(PYTEST) tests/ -m unit

test-integration: ## Run only integration tests
	$(PYTEST) tests/ -m integration

test-smoke: ## Run smoke tests (quick validation)
	$(PYTEST) tests/ -m smoke --tb=short

coverage: ## Run tests with coverage report
	$(PYTEST) tests/ --cov=. --cov-report=html --cov-report=term
	@echo "Coverage report generated in htmlcov/index.html"

lint: ## Run all linters
	$(FLAKE8) *.py tests/
	$(ISORT) --check-only *.py tests/
	$(BLACK) --check *.py tests/

format: ## Format code with black and isort
	$(ISORT) *.py tests/
	$(BLACK) *.py tests/
	@echo "Code formatted successfully"

type-check: ## Run type checking with mypy
	$(MYPY) *.py

clean: ## Clean up generated files
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	find . -type d -name '*.egg-info' -exec rm -rf {} +
	rm -rf .pytest_cache .coverage htmlcov/ .mypy_cache/
	rm -f tmp.out *.log *.pid

run: ## Run the explorer (requires config.ini)
	$(PYTHON) -m explorer config.ini

run-daemon: ## Run the explorer as daemon
	$(PYTHON) -m explorer config.ini daemon

stop: ## Stop the explorer daemon
	$(PYTHON) -m explorer config.ini stop

status: ## Check explorer status
	$(PYTHON) -m explorer config.ini status

docs: ## Generate documentation
	cd docs && make html
	@echo "Documentation generated in docs/_build/html/index.html"

check: lint type-check test ## Run all checks (lint, type-check, test)

pre-commit: format lint type-check test-smoke ## Run pre-commit checks

init-dev: install-dev ## Initialize development environment
	@echo "Development environment initialized!"
	@echo "Run 'make test' to verify setup"

# Docker targets
docker-build: ## Build Docker image
	docker build -t multichain-explorer:dev .

docker-run: ## Run Docker container
	docker run -p 4444:4444 -v $(PWD):/app multichain-explorer:dev

# Benchmarking
benchmark: ## Run performance benchmarks
	$(PYTHON) tests/benchmark.py

# Security
security-check: ## Run security checks
	$(PYTHON) -m pip check
	$(PYTHON) -m safety check --json || true

# Release
version: ## Show current version
	@grep "version=" cfg.py | cut -d'"' -f2
