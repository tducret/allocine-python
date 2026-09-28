.PHONY: check

check:
	.venv/bin/ruff check --fix .
	.venv/bin/ruff format .
	.venv/bin/ty check
