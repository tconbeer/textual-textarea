.PHONY: check
check:
	pytest
	black .
	ruff . --fix
	mypy

.PHONY: lint
lint:
	black .
	ruff . --fix
	mypy

.PHONY: serve
serve:
	textual run --dev -c python -m textual_textarea

profiles: .profiles/startup.html

.profiles/startup.html: src/scripts/profile_startup.py pyproject.toml $(wildcard src/textual_textarea/**/*.py)
	pyinstrument -r html -o .profiles/startup.html "src/scripts/profile_startup.py"
