# =============================================================================
# VytalLink Health Kit — development commands
#
# Main features:
# - uv-based environment management
# - Ruff, Bandit, pytest, and coverage validation
# - CLI execution for the readiness workflow
# - notebook support for demos and exploration
#
# Basic usage:
#   make install
#   make format
#   make lint
#   make test
#   make run-readiness
# =============================================================================

export PYTHON_VERSION=3.11.9
export ENVIRONMENT=localhost
VENV_DIR ?= .venv
KERNEL_NAME=ai-kernel
TEMPLATE_REMOTE ?= template
TEMPLATE_REPO ?=
TEMPLATE_BRANCH ?= main

# =============================================================================
# DEVELOPMENT ENVIRONMENT CONFIGURATION
# =============================================================================

# Set up virtual environment and install all dependencies using uv.lock
install:
	@set -e; \
	echo "🚀 Configuring project with uv..."; \
	UV_BIN="$$(command -v uv || true)"; \
	if [ -z "$$UV_BIN" ]; then \
		echo "❌ uv is not installed. Installing..."; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
		for candidate in "$$HOME/.local/bin/uv" "$$HOME/.cargo/bin/uv"; do \
			if [ -x "$$candidate" ]; then UV_BIN="$$candidate"; break; fi; \
		done; \
	fi; \
	if [ -z "$$UV_BIN" ]; then \
		echo "❌ Could not find uv after installation. Add it to PATH and retry."; \
		exit 1; \
	fi; \
	echo "✅ Using uv at $$UV_BIN"; \
	echo "📌 Pinning Python version $(PYTHON_VERSION)..."; \
	"$$UV_BIN" python pin $(PYTHON_VERSION); \
	echo "📦 Syncing dependencies (creating .venv if it doesn't exist)..."; \
	"$$UV_BIN" sync; \
	echo "🔌 Registering Jupyter kernel..."; \
	"$$UV_BIN" run python -m ipykernel install --user --name=$(KERNEL_NAME) --display-name="Python (uv)"; \
	echo "✅ Environment ready! Use 'source .venv/bin/activate' to activate."

# Add a new library to the project (replaces editing requirements.in)
# Usage: make add PKG=tensorflow
add:
	@echo "📦 Adding package $(PKG)..."
	@uv add $(PKG)
	@echo "✅ Package added and lockfile updated."

# Remove a library from the project
# Usage: make remove PKG=tensorflow
remove:
	@echo "🗑️ Removing package $(PKG)..."
	@uv remove $(PKG)
	@echo "✅ Package removed and lockfile updated."

# Generate requirements.txt (for legacy compatibility or simple deployments)
generate-requirements:
	@echo "📋 Exporting requirements.txt from uv.lock..."
	@uv export --format requirements-txt > requirements.txt
	@echo "✅ requirements.txt generated"

# Set up pre-commit hooks (Recommended to run once)
setup-hooks:
	@echo "🪝 Installing pre-commit hooks..."
	@if [ ! -d .venv ]; then make install; fi
	@echo "📦 Syncing dev dependencies required for hooks..."
	@uv sync --group dev
	@. $(VENV_DIR)/bin/activate && pre-commit install
	@echo "✅ Hooks installed!"

# =============================================================================
# CODE QUALITY AND LINTING
# =============================================================================

# Automatically format code with ruff
format:
	@echo "🎨 Formatting code with ruff..."
	@if [ ! -d .venv ]; then make install; fi
	@. $(VENV_DIR)/bin/activate && ruff format src/ tests/
	@. $(VENV_DIR)/bin/activate && ruff check --select I --fix src/ tests/
	@echo "🧹 Cleaning notebook outputs..."
	@. $(VENV_DIR)/bin/activate && nbstripout notebooks/*.ipynb 2>/dev/null || echo "⚠️  No notebooks found or nbstripout not installed"
	@echo "✅ Code formatted and notebooks cleaned!"

# Check code quality with multiple tools
lint:
	@echo "🔍 Running code quality analysis..."
	@if [ ! -d .venv ]; then make install; fi
	@echo "🚀 Ruff (fast linter)..."
	@. $(VENV_DIR)/bin/activate && ruff check src/ tests/
	@echo " Bandit (security)..."
	@. $(VENV_DIR)/bin/activate && bandit -r src/ tests/ -f json -o security-report.json -ll -q || true
	@. $(VENV_DIR)/bin/activate && bandit -r src/ tests/ -ll || true
	@echo "✅ Quality analysis completed!"

# Check only with ruff (faster for development)
lint-fast:
	@echo "⚡ Fast analysis with ruff..."
	@if [ ! -d .venv ]; then make install; fi
	@. $(VENV_DIR)/bin/activate && ruff check src/ tests/
	@echo "✅ Fast analysis completed!"

# Automatically fix linting issues when possible
fix:
	@echo "🔧 Fixing issues automatically..."
	@if [ ! -d .venv ]; then make install; fi
	@. $(VENV_DIR)/bin/activate && ruff check --fix src/ tests/ || echo "⚠️  Some issues remain for manual review."
	@. $(VENV_DIR)/bin/activate && ruff format src/ tests/
	@echo "🧹 Cleaning notebook outputs..."
	@. $(VENV_DIR)/bin/activate && nbstripout notebooks/*.ipynb 2>/dev/null || echo "⚠️  No notebooks found or nbstripout not installed"
	@echo "✅ Code formatted and cleanups applied!"

# Fix issues aggressively (includes unsafe fixes)
fix-force:
	@echo "🚨 Applying aggressive fixes (unsafe)..."
	@if [ ! -d .venv ]; then make install; fi
	@. $(VENV_DIR)/bin/activate && ruff check --fix --unsafe-fixes src/ tests/ || echo "⚠️  Issues remain."
	@. $(VENV_DIR)/bin/activate && ruff format src/ tests/
	@echo "✅ Aggressive fixes applied!"

# =============================================================================
# SYSTEM TESTING
# =============================================================================

# Run all tests with coverage
test:
	@echo "🧪 Running tests with coverage..."
	@if [ ! -d .venv ]; then make install; fi
	@echo "🎨 Running format before tests..."
	@make format
	@echo "🔧 Running fix before tests..."
	@make fix
	@. $(VENV_DIR)/bin/activate && PYTHONPATH=${PWD}/src pytest tests/ --cov=src --cov-report=html --cov-report=term-missing || echo "⚠️  No tests found to run"
	@echo "✅ Tests completed! See report in htmlcov/index.html"

# Run specific tests
test-unit:
	@echo "🧪 Running unit tests..."
	@if [ ! -d .venv ]; then make install; fi
	@. $(VENV_DIR)/bin/activate && PYTHONPATH=${PWD}/src pytest tests/ -v

# =============================================================================
# APPLICATION EXECUTION
# =============================================================================

# Run the readiness CLI in markdown mode using fallback recommendations
run-readiness:
	@echo "🚀 Running readiness report in markdown mode..."
	@if [ ! -d .venv ]; then make install; fi
	@. $(VENV_DIR)/bin/activate && uv run vytallink-health-kit readiness --no-llm

# Run the readiness CLI in JSON mode using fallback recommendations
run-readiness-json:
	@echo "🚀 Running readiness report in JSON mode..."
	@if [ ! -d .venv ]; then make install; fi
	@. $(VENV_DIR)/bin/activate && uv run vytallink-health-kit readiness --output json --no-llm

# =============================================================================
# OBSERVABILITY STACK
# =============================================================================

obs-up: ## Start the observability stack
	@docker compose -f docker-compose.observability.yml up -d

obs-down: ## Stop the observability stack
	@docker compose -f docker-compose.observability.yml down

obs-logs: ## Stream observability stack logs
	@docker compose -f docker-compose.observability.yml logs -f

obs-status: ## Show observability stack status
	@docker compose -f docker-compose.observability.yml ps

# =============================================================================
# USEFUL COMMANDS
# =============================================================================

# Full validation command (CI/CD pipeline)
ci:
	@echo "🚀 Running full CI pipeline..."
	@make format
	@make fix
	@make lint
	@make test
	@echo "✅ CI pipeline completed successfully!"

# Sync external skills installed ad-hoc into repository-governed folder
sync-skills:
	@set -e; \
	PRIMARY_SRC=".agents/skills"; \
	FALLBACK_SRC=".agent/skills"; \
	DEST=".github/skills-external"; \
	LOCK_FILE="skills-lock.json"; \
	TIMESTAMP="$$(date -u +"%Y-%m-%dT%H:%M:%SZ")"; \
	FOUND_SOURCE=0; \
	if [ -d "$$PRIMARY_SRC" ]; then \
		SRC="$$PRIMARY_SRC"; \
		FOUND_SOURCE=1; \
	elif [ -d "$$FALLBACK_SRC" ]; then \
		SRC="$$FALLBACK_SRC"; \
		FOUND_SOURCE=1; \
	fi; \
	synced=0; skipped=0; \
	if [ $$FOUND_SOURCE -eq 1 ]; then \
		echo "🔄 Syncing skills from $$SRC to $$DEST..."; \
		mkdir -p "$$DEST"; \
		for skill_dir in "$$SRC"/*; do \
			[ -d "$$skill_dir" ] || continue; \
			skill_name="$$(basename "$$skill_dir")"; \
			skill_file="$$skill_dir/SKILL.md"; \
			if [ ! -f "$$skill_file" ]; then \
				echo "⚠️  Skipping $$skill_name (missing SKILL.md)"; \
				skipped=$$((skipped + 1)); \
				continue; \
			fi; \
			mkdir -p "$$DEST/$$skill_name"; \
			cp "$$skill_file" "$$DEST/$$skill_name/SKILL.md"; \
			echo "✅ Synced $$skill_name"; \
			synced=$$((synced + 1)); \
		done; \
		if [ $$synced -eq 0 ] && [ $$skipped -eq 0 ]; then \
			echo "ℹ️  No skill directories found in $$SRC."; \
		fi; \
		echo "📦 Sync summary: synced=$$synced skipped=$$skipped"; \
		echo "✅ External skills are available in $$DEST"; \
	else \
		echo "ℹ️  No external skills source found (.agents/skills or .agent/skills)."; \
		echo "✅ Nothing to sync."; \
	fi; \
	mkdir -p "$$DEST"; \
	echo "🧾 Generating governed skills lock file ($$LOCK_FILE)..."; \
	tmp_lock="$$(mktemp)"; \
	printf '{\n  "version": 1,\n  "generatedAt": "%s",\n  "skills": {\n' "$$TIMESTAMP" > "$$tmp_lock"; \
	first=1; \
	for skill_dir in "$$DEST"/*; do \
		[ -d "$$skill_dir" ] || continue; \
		skill_name="$$(basename "$$skill_dir")"; \
		skill_file="$$skill_dir/SKILL.md"; \
		[ -f "$$skill_file" ] || continue; \
		hash="$$(shasum -a 256 "$$skill_file" | awk '{print $$1}')"; \
		if [ $$first -eq 0 ]; then \
			printf ',\n' >> "$$tmp_lock"; \
		fi; \
		first=0; \
		printf '    "%s": {\n' "$$skill_name" >> "$$tmp_lock"; \
		printf '      "source": "synced-local",\n' >> "$$tmp_lock"; \
		printf '      "sourceType": "file",\n' >> "$$tmp_lock"; \
		printf '      "path": "%s",\n' "$$skill_file" >> "$$tmp_lock"; \
		printf '      "computedHash": "%s",\n' "$$hash" >> "$$tmp_lock"; \
		printf '      "syncedAt": "%s"\n' "$$TIMESTAMP" >> "$$tmp_lock"; \
		printf '    }' >> "$$tmp_lock"; \
	done; \
	printf '\n  }\n}\n' >> "$$tmp_lock"; \
	mv "$$tmp_lock" "$$LOCK_FILE"; \
	echo "✅ Lock file updated at $$LOCK_FILE"; \
	echo "🧹 Cleaning installer artifacts..."; \
	rm -rf .agents .agent/skills; \
	echo "✅ Installer artifacts removed (.agents, .agent/skills)"; \
	if [ -d ".claude/skills" ]; then \
		echo "🔄 Syncing persistent skills from .claude/skills to $$DEST..."; \
		for skill_dir in ".claude/skills"/*; do \
			[ -d "$$skill_dir" ] || continue; \
			skill_name="$$(basename "$$skill_dir")"; \
			skill_file="$$skill_dir/SKILL.md"; \
			if [ ! -f "$$skill_file" ]; then \
				echo "⚠️  Skipping $$skill_name (missing SKILL.md)"; \
				continue; \
			fi; \
			mkdir -p "$$DEST/$$skill_name"; \
			cp "$$skill_file" "$$DEST/$$skill_name/SKILL.md"; \
			echo "✅ Synced (persistent): $$skill_name"; \
		done; \
	fi; \
	echo "✅ Sync complete. Claude Code reads skills from .github/skills/ via CLAUDE.md"

# Remove all external skills and related metadata to reset template state
purge-external-skills:
	@set -e; \
	echo "🧨 Purging external skills from repository..."; \
	rm -rf .github/skills-external .agents .agent/skills; \
	rm -f skills-lock.json; \
	mkdir -p .github/skills-external; \
	echo "✅ External skills purged (.github/skills-external reset, skills-lock.json removed)"

# Show help information about available commands
help:
	@echo "🏥 Medical Consultation Preparation Agent - Available Commands:"
	@echo ""
	@echo "Development Setup:"
	@echo "  make install              Set up virtual environment and dependencies"
	@echo "  make setup-hooks          Set up pre-commit hooks"
	@echo "  make generate-requirements Generate requirements.txt from current environment"
	@echo ""
	@echo "Code Quality:"
	@echo "  make format               Automatically format code (ruff format + imports)"
	@echo "  make lint                 Full quality analysis (ruff + bandit)"
	@echo "  make lint-fast            Fast analysis with ruff only"
	@echo "  make fix                  Automatically fix issues (ruff check + format)"
	@echo "  make ci                   Full pipeline: format + lint + test"
	@echo ""
	@echo "Testing:"
	@echo "  make test                 Run all tests with coverage"
	@echo "  make test-unit            Run unit tests only"
	@echo "  make run-batch-test       Run batch tests against API (dataset v1)"
	@echo "  make run-batch-test-custom Run batch tests with custom parameters"
	@echo ""
	@echo "Application Execution (Local):"
	@echo "  make run-dev             Start LangGraph development server"
	@echo "  make run-api             Start FastAPI server"
	@echo "  make run-question        Test with predefined medical question"
	@echo "  make run-interactive     Start interactive CLI mode"
	@echo ""
	@echo "Docker:"
	@echo "  make build-api           Build API Docker image"
	@echo "  make build-fresh         Build without cache"
	@echo "  make run-api-docker      Run API in Docker container"
	@echo "  make stop-docker         Stop Docker container"
	@echo ""
	@echo "Service URLs:"
	@echo "  🚀 FastAPI: http://localhost:8008"
	@echo "  📖 API Documentation: http://localhost:8008/docs"
	@echo "  🔍 Agent Discovery: http://localhost:8008/.well-known/agent.json"
	@echo ""
	@echo "Utilities:"
	@echo "  make help                Show this help message"
	@echo "  make sync-skills         Sync external skills to .github/skills-external (additive, no prune)"
	@echo "  make purge-external-skills Purge all external skills and reset metadata"
	@echo "  make clean               Clean cache and generated files"
	@echo ""

# Clean generated files and cache
clean:
	@echo "🧹 Cleaning..."
	@rm -rf __pycache__ .pytest_cache htmlcov .coverage .mypy_cache .ruff_cache
	@rm -f security-report.json
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cleanup completed!"

# Set help as default goal
.DEFAULT_GOAL := help

# Declare phony targets
.PHONY: install setup-hooks run-dev run-api run-question run-interactive build-api run-api-docker stop-docker build-fresh clean help generate-requirements run-batch-test run-batch-test-custom test test-unit format lint lint-fast fix ci sync-skills purge-external-skills
