# Convenience targets; every command here is also runnable by hand (see README.md).
PYTHON ?= python3.12
VENV ?= .venv
PORT ?= 8080
WORKERS ?= auto

# Recipes run through /bin/sh. Activate the virtualenv in the same shell
# as the command so all Python tooling comes from the project environment.
VENV_DIR := $(CURDIR)/$(VENV)
ACTIVATE := . $(VENV_DIR)/bin/activate &&

.PHONY: venv install check-venv mock test test-smoke test-parallel clean

venv:
	$(PYTHON) -m venv $(VENV)

# Fail with an actionable message instead of quietly using a system python.
check-venv:
	@test -x $(VENV_DIR)/bin/python || \
		{ echo "No virtualenv at $(VENV_DIR) - run 'make install' first."; exit 1; }

install: venv
	$(ACTIVATE) python -m pip install -r requirements.txt

# Prism mock server generated from the OpenAPI contract in this repository.
mock:
	@command -v prism >/dev/null 2>&1 || \
		{ echo "Prism CLI not found - install @stoplight/prism-cli."; exit 1; }
	prism mock -p $(PORT) contract/transactions-service.v1.yaml

test: check-venv
	$(ACTIVATE) python -m pytest

test-smoke: check-venv
	$(ACTIVATE) python -m pytest -m smoke -v

# Parallel execution is opt-in so the default test run remains deterministic.
# WORKERS accepts any value supported by pytest-xdist, e.g. 4 or auto.
test-parallel: check-venv
	@$(ACTIVATE) python -c "import xdist" 2>/dev/null || \
		{ echo "pytest-xdist is not installed - run 'make install'."; exit 1; }
	$(ACTIVATE) python -m pytest -n $(WORKERS) -v

clean:
	rm -rf $(VENV) .pytest_cache reports
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
