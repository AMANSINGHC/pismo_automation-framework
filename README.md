# pismo_automation-framework

API test automation for the Pismo transactions service. The tests are driven
by the contract in `contract/transactions-service.v1.yaml` and run against a Prism
mock by default, so the suite works from a clean clone with no backend running.

## Quick start

```bash
make install      # .venv on python3.12 + pinned requirements
make mock         # Prism mock of the contract on http://localhost:8080 (leave it running)
make test-smoke   # the happy path per endpoint; writes reports/ (see below)
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
overrides only. Every run prints the environment it is about to exercise, on the
header line pytest emits before the first test. `make test` activates `.venv` inside
its recipe shell; by hand,
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

## Parallel runs (opt-in)

The same suite split across worker processes by `pytest-xdist`; the two report files
and everything else about a run are unchanged:

```bash
make test-parallel                            # 4 workers
make test-parallel WORKERS=auto               # one per physical core
PYTEST_ADDOPTS="-n auto" python -m pytest     # turn it on without editing the file
```

`-n` is not in `pytest.ini` on purpose: a default run stays single-process, so its
order and the number of API calls it makes are predictable, and `PYTEST_ADDOPTS`
(applied after `addopts`) turns parallelism on without editing the repository. Two
rules keep the suite distributable — no test may depend on another test's state or
on execution order, and `parametrize` inputs must be ordered (a `set` breaks
distribution). One consequence to know: session-scoped fixtures run once **per
worker**, so `-n4` issues up to four `POST /accounts`. At the current size (22 tests
against the local mock) a parallel run is *slower* than a plain one, because worker
startup costs more than the tests do; it pays off as the suite grows, or against a
remote environment where each test waits on the network.

## Reports

Every run writes the same two files — no separate command to remember:

| File | Written for |
|---|---|
| `reports/junit.xml` | CI: one `<testcase>` per test with its duration, and each failure's message verbatim (`--junit-xml`, from pytest itself) |
| `reports/report.html` | a human: the same results as one self-contained page (no sibling asset files) with the environment table pytest-metadata adds, openable straight from the filesystem (`--html --self-contained-html`, from pytest-html) |

Both are output rather than source, and `reports/` is gitignored. The flags live in
`pytest.ini` (`addopts`), so every run writes them — `pytest` by hand, an IDE run,
`make test` — while an explicit `--junit-xml`/`--html` on the command line still
wins, which is how a CI job points them at its own results directory:

```bash
python -m pytest --junit-xml=/tmp/junit.xml --html=/tmp/report.html --self-contained-html
```

## Layout

```
conftest.py          run-wide pytest options (--env/--base-url), report header, settings fixture
contract/            the API contract under test
docs/                C1 strategy, C3a contract audit, C4 framework notes
reports/             junit.xml + report.html from the last run (gitignored)
src/config/          Base URL + HTTP settings resolution (environments.yaml)
src/clients/         service clients, one method per operation (accounts, transactions)
src/utils/           shared test helpers (assertions, concurrency)
src/utils/transport/ HTTP layer + ApiResponse envelope (domain-free)
src/models/          typed request/response shapes from the contract
tests/               shared fixtures (conftest.py)
tests/accounts/      one file per Accounts endpoint
tests/transactions/  one file per Transactions endpoint
tests/e2e/           cross-service user journey (account → transactions)
tests/data.py        test-data helpers (unique document numbers)
```

See `docs/C4_automation-architecture.md` for the layer responsibilities and the
reasoning behind the configuration and HTTP-layer choices.
