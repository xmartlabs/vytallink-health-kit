# =============================================================================
# This Makefile provides commands to configure, run, and work with
# the VytalLink Health Kit — Daily Readiness Agent.
#
# Main features:
# - Virtual environment management with uv
# - Linting and formatting tools for code quality
# - Development and production server
# - Interactive CLI and single question mode
# - Batch testing against the API
# - Docker containerization support
#
# Basic usage:
#   make install          # Set up development environment
#   make format           # Automatically format code
#   make lint             # Check code quality
#   make test             # Run tests
#   make run-api          # Start API server
#   make build-api        # Build API Docker image
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

# Start LangGraph development server
run-dev:
	@echo "🚀 Starting development server..."
	@if [ ! -d .venv ]; then make install; fi
	@. $(VENV_DIR)/bin/activate && langgraph dev

# Start FastAPI server
run-api:
	@echo "🚀 Starting API server..."
	@if [ ! -d .venv ]; then make install; fi
	@. $(VENV_DIR)/bin/activate && PYTHONPATH=${PWD} uvicorn api:app --reload --host 0.0.0.0 --port 8008 --log-level debug

# Run CLI with a predefined question
run-question:
	@echo "🚀 Running a single question"
	@if [ ! -d .venv ]; then make install; fi
	@. $(VENV_DIR)/bin/activate && PYTHONPATH=${PWD}/src python main.py --question "I have frequent headaches, can you help me prepare my medical consultation?"

# Start interactive CLI mode
run-interactive:
	@echo "🚀 Starting interactive CLI mode"
	@if [ ! -d .venv ]; then make install; fi
	@. $(VENV_DIR)/bin/activate && PYTHONPATH=${PWD}/src python main.py --interactive

# =============================================================================
# DOCKER BUILD AND DEPLOYMENT
# =============================================================================

# Docker configuration variables
IMG_NAME ?= vytallink-health-kit
IMAGE_TAG ?= latest
CONTAINER_NAME ?= medical-agent-server
API_PORT ?= 8008

# Enable Docker BuildKit
export DOCKER_BUILDKIT=1

# Build API Docker image
build-api:
	@echo "🔨 Building FastAPI Docker image (using Dockerfile.api)..."
	@docker build --platform=linux/amd64 -t ${IMG_NAME}:${IMAGE_TAG} -f Dockerfile.api .
	@echo "✅ FastAPI Docker image built successfully!"

# Run Docker container
run-api-docker:
	@echo "🚀 Running Docker container..."
	@docker run --platform=linux/amd64 -e ENV=production -d -p ${API_PORT}:${API_PORT} --env-file .env ${IMG_NAME}:${IMAGE_TAG}
	@echo "✅ Docker container running at http://localhost:${API_PORT}!"

# Build without cache
build-fresh:
	@echo "🔨 Building Docker image without cache..."
	@docker build --no-cache --platform=linux/amd64 -t ${IMG_NAME}:${IMAGE_TAG} -f Dockerfile.api .
	@echo "✅ Docker image built successfully!"

# Stop Docker container
stop-docker:
	@echo "🛑 Stopping Docker container..."
	@docker stop ${CONTAINER_NAME} 2>/dev/null || true
	@docker rm ${CONTAINER_NAME} 2>/dev/null || true
	@echo "✅ Container stopped!"

# =============================================================================
# USEFUL COMMANDS
# =============================================================================

# Full validation command (CI/CD pipeline)
ci:
	@echo "🚀 Running full CI pipeline..."
	@make format
	@make lint
	@make test
	@echo "✅ CI pipeline completed successfully!"

# =============================================================================
# TEMPLATE SYNC WORKFLOW
# =============================================================================

# Add (or update) template remote used for repository synchronization.
# Usage:
#   make template-remote-setup
#   make template-remote-setup TEMPLATE_REPO=git@github.com:org/your-template.git
template-remote-setup:
	@set -e; \
	echo "🔗 Configuring template remote '$${TEMPLATE_REMOTE:-$(TEMPLATE_REMOTE)}'..."; \
	if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then \
		echo "❌ This directory is not a git repository."; \
		exit 1; \
	fi; \
	if git remote get-url $(TEMPLATE_REMOTE) >/dev/null 2>&1; then \
		echo "ℹ️  Remote '$(TEMPLATE_REMOTE)' already exists. Updating URL..."; \
		git remote set-url $(TEMPLATE_REMOTE) $(TEMPLATE_REPO); \
	else \
		echo "➕ Adding remote '$(TEMPLATE_REMOTE)'..."; \
		git remote add $(TEMPLATE_REMOTE) $(TEMPLATE_REPO); \
	fi; \
	echo "✅ Template remote configured:"; \
	git remote -v | grep '^$(TEMPLATE_REMOTE)\s' || true

# Fetch template updates and show commit delta before merging/rebasing.
# Usage:
#   make template-sync-preview
template-sync-preview:
	@set -e; \
	echo "📥 Fetching updates from $(TEMPLATE_REMOTE)..."; \
	git fetch $(TEMPLATE_REMOTE); \
	echo "📊 Incoming commits from $(TEMPLATE_REMOTE)/$(TEMPLATE_BRANCH):"; \
	if git rev-list --count HEAD..$(TEMPLATE_REMOTE)/$(TEMPLATE_BRANCH) >/dev/null 2>&1; then \
		count="$$(git rev-list --count HEAD..$(TEMPLATE_REMOTE)/$(TEMPLATE_BRANCH))"; \
		echo "   $$count commit(s) ahead in template branch."; \
		git --no-pager log --oneline --decorate --graph HEAD..$(TEMPLATE_REMOTE)/$(TEMPLATE_BRANCH) | head -n 30 || true; \
	else \
		echo "⚠️  Could not compare branches. Verify remote/branch names."; \
	fi

# Merge template changes into current branch.
# Usage:
#   make template-sync-merge
#   make template-sync-merge TEMPLATE_BRANCH=develop
template-sync-merge:
	@set -e; \
	echo "🧭 Checking working tree status..."; \
	if [ -n "$$(git status --porcelain)" ]; then \
		echo "❌ Working tree is not clean. Commit or stash before syncing."; \
		exit 1; \
	fi; \
	git fetch $(TEMPLATE_REMOTE); \
	echo "🔀 Merging $(TEMPLATE_REMOTE)/$(TEMPLATE_BRANCH) into $$(git branch --show-current)..."; \
	git merge --no-ff $(TEMPLATE_REMOTE)/$(TEMPLATE_BRANCH) || { \
		echo "⚠️  Merge conflicts detected. Resolve them and continue with 'git commit'."; \
		echo "   Tip: git status && git diff --name-only --diff-filter=U"; \
		exit 1; \
	}; \
	echo "✅ Template merge completed."

# Rebase current branch on top of template changes.
# Usage:
#   make template-sync-rebase
template-sync-rebase:
	@set -e; \
	echo "🧭 Checking working tree status..."; \
	if [ -n "$$(git status --porcelain)" ]; then \
		echo "❌ Working tree is not clean. Commit or stash before syncing."; \
		exit 1; \
	fi; \
	git fetch $(TEMPLATE_REMOTE); \
	echo "🧬 Rebasing $$(git branch --show-current) onto $(TEMPLATE_REMOTE)/$(TEMPLATE_BRANCH)..."; \
	git rebase $(TEMPLATE_REMOTE)/$(TEMPLATE_BRANCH) || { \
		echo "⚠️  Rebase conflicts detected. Resolve and continue with 'git rebase --continue'."; \
		echo "   If needed: git rebase --abort"; \
		exit 1; \
	}; \
	echo "✅ Template rebase completed."

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
	@echo "  make template-remote-setup Add/update template upstream remote"
	@echo "  make template-sync-preview Fetch template and preview incoming commits"
	@echo "  make template-sync-merge Merge template branch into current branch"
	@echo "  make template-sync-rebase Rebase current branch onto template branch"
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
.PHONY: install setup-hooks run-dev run-api run-question run-interactive build-api run-api-docker stop-docker build-fresh clean help generate-requirements run-batch-test run-batch-test-custom test test-unit format lint lint-fast fix ci template-remote-setup template-sync-preview template-sync-merge template-sync-rebase sync-skills purge-external-skills
