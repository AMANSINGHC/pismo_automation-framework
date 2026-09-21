# pismo_automation-framework

API test automation for the Pismo transactions service. The tests are driven
by the contract in `contract/transactions-service.v1.yaml` and run against a Prism
mock by default, so the suite works from a clean clone with no backend running.

## Quick start

```bash
make install      # .venv on python3.12 + pinned requirements
make mock         # Prism mock of the contract on http://localhost:8080 (leave it running)
make test-smoke   # one happy-path test per endpoint; writes reports/ (see below)
```

By hand, if you prefer (`source .venv/bin/activate` is what the Makefile does for
every recipe):

```bash
python3.12 -m venv .venv
source .venv/bin/activate          # then `python` / `pip` are the venv ones
python -m pip install -r requirements.txt
prism mock -p 8080 contract/transactions-service.v1.yaml &
python -m pytest -m smoke -v
```

## Where to run it

The Base URL comes from `src/config/environments.yaml`; environment variables are
overrides only. Every run prints the environment it is about to exercise in the
report header. `make test` activates `.venv` inside its recipe shell; by hand,
activate once per shell (or skip activation and prefix each run with
`PATH="$PWD/.venv/bin:$PATH"`):

```bash
source .venv/bin/activate                       # once per shell
python -m pytest                                # prism (default), from environments.yaml
python -m pytest -m accounts                    # only the tests with tag `accounts`
python -m pytest --env staging --base-url https://staging.example
PISMO_ENV=staging PISMO_BASE_URL=https://staging.example python -m pytest
```

`make test` / `make test-smoke` stop with an actionable message when there is no
virtualenv yet, instead of falling back to a system python.

An environment without a base URL (for example `staging` as shipped) skips the run
with an actionable message instead of failing.

## Reports

Every run writes the same two files — no separate command to remember:

| File | Written for |
|---|---|
| `reports/junit.xml` | CI: one `<testcase>` per test with its duration, each failure's message, and a `pismo` property stating the environment the run exercised |
| `reports/report.html` | a human: the same results as one self-contained page (no sibling asset files) with the environment table, openable straight from the filesystem |

Both are output rather than source, and `reports/` is gitignored. The defaults come
from `conftest.py` and apply only to options a run leaves unset, so pointing them
somewhere else still works:

```bash
python -m pytest --junitxml=/tmp/junit.xml --html=/tmp/report.html
```

The failure message is the payload of a report, which is why the assertion helpers
build a verbose one on purpose: it names the request, the status expected and
received, and quotes the response body. A body therefore reaches a report only as
part of a message a test author wrote.

## Layout

```
conftest.py          run-wide pytest options (--env/--base-url), report header, settings fixture
contract/            the API contract under test
docs/                C1 strategy, C3a contract audit, C4 framework notes
reports/             junit.xml + report.html from the last run (gitignored)
src/config/          Base URL + HTTP settings resolution (environments.yaml)
src/clients/         service clients, one method per operation (accounts, transactions)
src/utils/           assertion helpers shared by the test modules
src/utils/transport/ HTTP layer + ApiResponse envelope (domain-free)
src/models/          typed request/response shapes from the contract
tests/               shared fixtures (conftest.py)
tests/accounts/      one file per Accounts endpoint
tests/transactions/  one file per Transactions endpoint
tests/data.py        test-data helpers (unique document numbers)
```

See `docs/C4_automation-architecture.md` for the layer responsibilities and the
reasoning behind the configuration and HTTP-layer choices.
