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

check: lint types test

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .hypothesis htmlcov
	rm -rf build dist *.egg-info coverage.xml .coverage
	find . -type d -name __pycache__ -not -path "./.venv/*" -exec rm -rf {} +
