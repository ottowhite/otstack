.PHONY: test check lint typecheck

test:
	uv run pytest

check: lint typecheck

lint:
	uv run ruff check src test

typecheck:
	uv run ty check src test
