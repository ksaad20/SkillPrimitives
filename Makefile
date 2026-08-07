# =============================================================================
# Skill Primitives — Invincible Makefile
# =============================================================================
# Usage: make <target>
#        make help     # Show all available targets
# =============================================================================

.PHONY: help install dev-install update upgrade \
        test test-fast test-slow test-coverage \
        format lint typecheck quality fix \
        demo demo-all \
        zoo zoo-clean \
        paper paper-clean \
        space space-deploy \
        release release-check release-upload \
        clean clean-all clean-cache \
        ci

# -----------------------------------------------------------------------------
# Colors & Formatting
# -----------------------------------------------------------------------------
RESET  := \033[0m
BOLD   := \033[1m
DIM    := \033[2m
RED    := \033[31m
GREEN  := \033[32m
YELLOW := \033[33m
BLUE   := \033[34m
CYAN   := \033[36m

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
PYTHON        := python3
PIP           := $(PYTHON) -m pip
PYTEST        := $(PYTHON) -m pytest
BLACK         := $(PYTHON) -m black
RUFF          := $(PYTHON) -m ruff
MYPY          := $(PYTHON) -m mypy
PACKAGE_NAME  := skill_primitives
TESTS_DIR     := tests
DEMO_DIR      := demos
ZOO_DIR       := zoo
PAPER_DIR     := paper
SPACES_DIR    := spaces
BUILD_DIR     := build
DIST_DIR      := dist

# -----------------------------------------------------------------------------
# Help — The Default Target
# -----------------------------------------------------------------------------
help: ## Show this help message
	@echo ""
	@echo "$(BOLD)$(CYAN)  Skill Primitives$(RESET) — $(DIM)Natural Language to Robot Motion$(RESET)"
	@echo ""
	@echo "$(BOLD)Usage:$(RESET) make $(YELLOW)<target>$(RESET)"
	@echo ""
	@echo "$(BOLD)Setup & Installation:$(RESET)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-18s$(RESET) %s\n", $$1, $$2}' | \
		grep -E 'install|update|upgrade'
	@echo ""
	@echo "$(BOLD)Development & Quality:$(RESET)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-18s$(RESET) %s\n", $$1, $$2}' | \
		grep -E 'test|format|lint|typecheck|quality|fix'
	@echo ""
	@echo "$(BOLD)Demos & Experiments:$(RESET)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-18s$(RESET) %s\n", $$1, $$2}' | \
		grep -E 'demo|zoo|paper|space'
	@echo ""
	@echo "$(BOLD)Release & Maintenance:$(RESET)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-18s$(RESET) %s\n", $$1, $$2}' | \
		grep -E 'release|clean|ci'
	@echo ""

# -----------------------------------------------------------------------------
# Setup & Installation
# -----------------------------------------------------------------------------
install: ## Install package in production mode
	@echo "$(BLUE)▶ Installing skill-primitives...$(RESET)"
	$(PIP) install -e .

dev-install: ## Install package with all development dependencies
	@echo "$(BLUE)▶ Installing in development mode with all extras...$(RESET)"
	$(PIP) install -e ".[all]"

update: ## Update all dependencies to latest compatible versions
	@echo "$(BLUE)▶ Updating dependencies...$(RESET)"
	$(PIP) install --upgrade -e ".[all]"

upgrade: update ## Alias for 'make update'

# -----------------------------------------------------------------------------
# Testing
# -----------------------------------------------------------------------------
test: ## Run the full test suite
	@echo "$(BLUE)▶ Running full test suite...$(RESET)"
	$(PYTEST) $(TESTS_DIR) -v

test-fast: ## Run only fast tests (skip slow, gpu, integration)
	@echo "$(BLUE)▶ Running fast tests only...$(RESET)"
	$(PYTEST) $(TESTS_DIR) -v -m "not slow and not gpu and not integration"

test-slow: ## Run only slow tests
	@echo "$(BLUE)▶ Running slow tests...$(RESET)"
	$(PYTEST) $(TESTS_DIR) -v -m "slow"

test-coverage: ## Run tests with coverage report
	@echo "$(BLUE)▶ Running tests with coverage...$(RESET)"
	$(PYTEST) $(TESTS_DIR) --cov=$(PACKAGE_NAME) --cov-report=term-missing --cov-report=html

# -----------------------------------------------------------------------------
# Code Quality
# -----------------------------------------------------------------------------
format: ## Format all code with black
	@echo "$(BLUE)▶ Formatting with black...$(RESET)"
	$(BLACK) $(PACKAGE_NAME) $(TESTS_DIR) $(DEMO_DIR) $(ZOO_DIR) scripts

lint: ## Lint all code with ruff
	@echo "$(BLUE)▶ Linting with ruff...$(RESET)"
	$(RUFF) check $(PACKAGE_NAME) $(TESTS_DIR) $(DEMO_DIR) $(ZOO_DIR) scripts

typecheck: ## Run static type checking with mypy
	@echo "$(BLUE)▶ Type checking with mypy...$(RESET)"
	$(MYPY) $(PACKAGE_NAME)

quality: format lint typecheck ## Run all quality checks (format + lint + typecheck)

fix: ## Auto-fix linting issues where possible
	@echo "$(BLUE)▶ Auto-fixing with ruff...$(RESET)"
	$(RUFF) check --fix $(PACKAGE_NAME) $(TESTS_DIR) $(DEMO_DIR) $(ZOO_DIR) scripts
	@echo "$(BLUE)▶ Re-formatting with black...$(RESET)"
	$(BLACK) $(PACKAGE_NAME) $(TESTS_DIR) $(DEMO_DIR) $(ZOO_DIR) scripts

# -----------------------------------------------------------------------------
# Demos
# -----------------------------------------------------------------------------
demo: ## Run the 10-second hello demo
	@echo "$(BLUE)▶ Running hello demo...$(RESET)"
	$(PYTHON) -m skill_primitives.demo

demo-all: ## Run all demos sequentially
	@echo "$(BLUE)▶ Running all demos...$(RESET)"
	@for f in $(DEMO_DIR)/*.py; do \
		echo "$(CYAN)  → Running $$f...$(RESET)"; \
		$(PYTHON) $$f || exit 1; \
	done
	@echo "$(GREEN)✓ All demos completed$(RESET)"

# -----------------------------------------------------------------------------
# Zoo (Pre-Computed Skill Libraries)
# -----------------------------------------------------------------------------
zoo: ## Build all pre-computed skill zoos
	@echo "$(BLUE)▶ Building skill zoos...$(RESET)"
	$(PYTHON) scripts/build_zoo.py --all
	@echo "$(GREEN)✓ Zoos built in $(ZOO_DIR)/$(RESET)"

zoo-clean: ## Remove all generated zoo artifacts
	@echo "$(YELLOW)▶ Cleaning zoos...$(RESET)"
	rm -rf $(ZOO_DIR)/*/skills.parquet
	rm -rf $(ZOO_DIR)/*/metadata.yaml
	rm -rf $(ZOO_DIR)/*/preview.gif
	@echo "$(GREEN)✓ Zoos cleaned$(RESET)"

# -----------------------------------------------------------------------------
# Paper & Reproducibility
# -----------------------------------------------------------------------------
paper: ## Reproduce all paper figures and tables
	@echo "$(BLUE)▶ Reproducing paper figures...$(RESET)"
	$(PYTHON) $(PAPER_DIR)/reproduce_all.py
	@echo "$(GREEN)✓ Figures generated in $(PAPER_DIR)/figures/$(RESET)"

paper-clean: ## Remove all generated paper artifacts
	@echo "$(YELLOW)▶ Cleaning paper artifacts...$(RESET)"
	rm -rf $(PAPER_DIR)/figures/*.png
	rm -rf $(PAPER_DIR)/figures/*.pdf
	rm -rf $(PAPER_DIR)/tables/*.csv
	rm -rf $(PAPER_DIR)/data/*
	@echo "$(GREEN)✓ Paper artifacts cleaned$(RESET)"

# -----------------------------------------------------------------------------
# Hugging Face Space
# -----------------------------------------------------------------------------
space: ## Prepare the HF Space for deployment
	@echo "$(BLUE)▶ Preparing HF Space...$(RESET)"
	cd $(SPACES_DIR) && $(PIP) install -r requirements.txt
	@echo "$(GREEN)✓ Space ready in $(SPACES_DIR)/$(RESET)"

space-deploy: ## Deploy the HF Space (requires HF CLI login)
	@echo "$(BLUE)▶ Deploying to Hugging Face Spaces...$(RESET)"
	huggingface-cli upload $(HF_SPACE_NAME) $(SPACES_DIR)/ --repo-type=space

# -----------------------------------------------------------------------------
# Release & Packaging
# -----------------------------------------------------------------------------
release-check: ## Check the package build before release
	@echo "$(BLUE)▶ Checking package build...$(RESET)"
	rm -rf $(BUILD_DIR) $(DIST_DIR)
	$(PYTHON) -m build
	$(PYTHON) -m twine check $(DIST_DIR)/*

release: release-check ## Build and check the release package
	@echo "$(GREEN)✓ Release package ready in $(DIST_DIR)/$(RESET)"

release-upload: release ## Upload release to PyPI (requires credentials)
	@echo "$(YELLOW)▶ Uploading to PyPI...$(RESET)"
	$(PYTHON) -m twine upload $(DIST_DIR)/*

# -----------------------------------------------------------------------------
# CI / Automation
# -----------------------------------------------------------------------------
ci: dev-install quality test-fast ## Full CI pipeline (install → quality → fast tests)
	@echo "$(GREEN)✓ CI pipeline passed$(RESET)"

# -----------------------------------------------------------------------------
# Cleaning
# -----------------------------------------------------------------------------
clean: ## Remove build artifacts, caches, and generated files
	@echo "$(YELLOW)▶ Cleaning build artifacts...$(RESET)"
	rm -rf $(BUILD_DIR)
	rm -rf $(DIST_DIR)
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf htmlcov
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "$(GREEN)✓ Cleaned$(RESET)"

clean-all: clean zoo-clean paper-clean ## Nuclear option: clean everything
	@echo "$(GREEN)✓ Full clean completed$(RESET)"

clean-cache: ## Remove only Python cache files
	@echo "$(YELLOW)▶ Cleaning Python caches...$(RESET)"
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "$(GREEN)✓ Caches cleaned$(RESET)"
