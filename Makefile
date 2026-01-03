.PHONY: help install dev-install test test-unit test-integration test-cov lint format typecheck run daemon clean validate-configs

help:
	@echo "Immerse Yourself - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install         - Install production dependencies"
	@echo "  make dev-install     - Install development dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test            - Run all tests"
	@echo "  make test-unit       - Run unit tests only"
	@echo "  make test-integration - Run integration tests"
	@echo "  make test-cov        - Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint            - Run linters (ruff)"
	@echo "  make format          - Format code with black"
	@echo "  make typecheck       - Run mypy type checking"
	@echo ""
	@echo "Running:"
	@echo "  make run             - Start GUI launcher"
	@echo "  make daemon          - Start lighting daemon (debug mode)"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean           - Remove cache and build artifacts"
	@echo "  make validate-configs - Validate all YAML configs"

install:
	pip install -r requirements.txt

dev-install: install
	@if [ -f requirements-dev.txt ]; then \
		pip install -r requirements-dev.txt; \
	else \
		echo "requirements-dev.txt not found, skipping dev dependencies"; \
	fi

test:
	@if command -v pytest > /dev/null; then \
		pytest tests/ -v --tb=short; \
	else \
		echo "pytest not installed. Run 'make dev-install' first"; \
	fi

test-unit:
	@if command -v pytest > /dev/null; then \
		pytest tests/ -v -m "not integration" --tb=short; \
	else \
		echo "pytest not installed. Run 'make dev-install' first"; \
	fi

test-integration:
	@if command -v pytest > /dev/null; then \
		pytest tests/ -v -m integration --tb=short; \
	else \
		echo "pytest not installed. Run 'make dev-install' first"; \
	fi

test-cov:
	@if command -v pytest > /dev/null; then \
		pytest tests/ -v --cov=engines --cov=config_loader --cov=lighting_daemon --cov-report=html --cov-report=term; \
	else \
		echo "pytest not installed. Run 'make dev-install' first"; \
	fi

lint:
	@if command -v ruff > /dev/null; then \
		ruff check engines/ launcher.py config_loader.py lighting_daemon.py tests/ 2>/dev/null || true; \
		echo "✓ Linting complete"; \
	else \
		echo "ruff not installed. Run 'make dev-install' to install"; \
	fi

format:
	@if command -v black > /dev/null; then \
		black engines/ launcher.py config_loader.py lighting_daemon.py tests/ 2>/dev/null || true; \
		echo "✓ Code formatted"; \
	else \
		echo "black not installed. Run 'make dev-install' to install"; \
	fi

typecheck:
	@if command -v mypy > /dev/null; then \
		mypy engines/ launcher.py config_loader.py lighting_daemon.py --ignore-missing-imports 2>/dev/null || true; \
	else \
		echo "mypy not installed. Run 'make dev-install' to install"; \
	fi

run:
	python3 launcher.py

daemon:
	@echo "Starting lighting daemon in debug mode..."
	@echo "Send JSON commands to stdin. Example:"
	@echo '  {"command": "ping"}'
	@echo ""
	python3 lighting_daemon.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .coverage .mypy_cache 2>/dev/null || true
	@echo "✓ Cleaned build artifacts"

validate-configs:
	@echo "Validating YAML configurations..."
	@python3 -c "from config_loader import ConfigLoader; \
		loader = ConfigLoader('env_conf'); \
		configs = loader.discover_all(); \
		print(f'✓ Validated {len(configs)} configuration(s)')"
