.PHONY: check
check:
	uv sync --group static --group test
	uv run ruff format .
	uv run ruff check . --fix
	uv run mypy
	uv run pytest

.PHONY: lint
lint:
	uv sync --group static --group test
	uv run ruff format .
	uv run ruff check . --fix
	uv run mypy

.PHONY: serve
serve:
	uv sync --group dev
	uv run textual run --dev -c python -m textual_textarea

profiles: .profiles/startup.html

.profiles/startup.html: src/scripts/profile_startup.py pyproject.toml $(wildcard src/textual_textarea/**/*.py)
	uv sync --group dev
	uv run pyinstrument -r html -o .profiles/startup.html "src/scripts/profile_startup.py"
