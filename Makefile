# Convenience targets; every command here is also runnable by hand (see README.md).
PYTHON ?= python3.12
VENV ?= .venv
PORT ?= 8080

# Recipes run through `sh`, one shell per line, so the venv has to be activated in
# the same shell as the command: `$(ACTIVATE) python ...` is the makefile equivalent
# of a hand-run `source .venv/bin/activate` session. Use `.`, not `source`: the
# recipe shell is /bin/sh, not bash. $(CURDIR) keeps the path absolute, so
# `make -C <dir>` and IDE runners behave the same.
VENV_DIR := $(CURDIR)/$(VENV)
ACTIVATE := . $(VENV_DIR)/bin/activate &&

.PHONY: venv install check-venv mock test test-smoke clean

venv:
	$(PYTHON) -m venv $(VENV)

# Fail with an actionable message instead of quietly using a system python.
check-venv:
	@test -x $(VENV_DIR)/bin/python || \
		{ echo "No virtualenv at $(VENV_DIR) - run 'make install' first."; exit 1; }

install: venv
	$(ACTIVATE) python -m pip install -r requirements.txt

# Prism mock server generated from the contract in this repository.
mock:
	prism mock -p $(PORT) contract/transactions-service.v1.yaml

test: check-venv
	$(ACTIVATE) python -m pytest

test-smoke: check-venv
	$(ACTIVATE) python -m pytest -m smoke -v

clean:
	rm -rf $(VENV) .pytest_cache
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
