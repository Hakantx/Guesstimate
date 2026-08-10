.PHONY: help install lint fmt types test test-fast cov check bench clean

help:
	@echo "install  install dependencies into .venv"
	@echo "lint     ruff check"
	@echo "fmt      ruff format + fix"
	@echo "types    mypy strict"
	@echo "test     pytest"
	@echo "test-fast pytest, skipping the slow brute-force checks"
	@echo "cov      pytest with coverage report"
	@echo "check    lint + types + test, what CI runs"
	@echo "bench    run the benchmark sweep into docs/benchmarks/"
	@echo "clean    remove caches and build artifacts"
	@echo "serve    run the API on :8000"
	@echo "schema   regenerate web/src/api/types.ts from the API"
	@echo "web-check  web typecheck + tests"

install:
	uv sync

lint:
	uv run ruff check .
	uv run ruff format --check .

fmt:
	uv run ruff format .
	uv run ruff check --fix .

types:
	uv run mypy guesstimate tests

test:
	uv run pytest

test-fast:
	uv run pytest -m "not slow"

cov:
	uv run pytest --cov=guesstimate --cov-report=term-missing --cov-report=xml

bench:
	uv run python -m guesstimate.bench $(ARGS)

serve:
	uv run uvicorn guesstimate.api:app --reload

# The web client's types -- and crucially its error codes -- are generated from
# the API rather than written twice. A code added in schemas.py shows up here
# as a build failure, not as a runtime surprise in someone's browser.
schema:
	cd web && npm run generate

web-install:
	cd web && npm install

web-check:
	cd web && npm run typecheck && npm run test

check: lint types test

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .hypothesis htmlcov
	rm -rf build dist *.egg-info coverage.xml .coverage
	find . -type d -name __pycache__ -not -path "./.venv/*" -exec rm -rf {} +
