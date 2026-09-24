# pismo_automation-framework

API test automation for the Pismo transactions service. The tests are driven by the
contract in `contract/transactions-service.v1.yaml` and run against a Prism mock by
default, so a clean clone needs no backend running. The mock replays the contract's
examples instead of holding state, so only part of the suite can be green there — see
[Mock vs real environment](#mock-vs-real-environment).

## Quick start

```bash
make install      # .venv on python3.12 + pinned requirements
make mock         # Prism mock of the contract on http://localhost:8080 (leave it running)
make test-smoke   # the fast subset (-m smoke); writes reports/ (see below)
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

Against the mock, the contract tests pass and the functional cases are red by design —
[Mock vs real environment](#mock-vs-real-environment) says which is which.

## Where to run it

The Base URL comes from `src/config/environments.yaml`; environment variables are
overrides only. Every run prints the environment it is about to exercise, on the
header line pytest emits before the first test. `make test` activates `.venv` inside
its recipe shell; by hand, activate once per shell (or skip activation and prefix
each run with `PATH="$PWD/.venv/bin:$PATH"`):

```bash
source .venv/bin/activate                       # once per shell
python -m pytest                                # prism (default), from environments.yaml
python -m pytest -m accounts                    # only the tests with tag `accounts`
python -m pytest -m contract                    # only the tests that assert the contract itself
python -m pytest --env staging --base-url https://staging.example
PISMO_ENV=staging PISMO_BASE_URL=https://staging.example python -m pytest
```

Every `make test*` target stops with an actionable message when there is no virtualenv
yet, instead of falling back to a system python (`make test-parallel` also reports a
missing `pytest-xdist`).

An environment without a base URL (for example `staging` as shipped) skips the run
with an actionable message instead of failing.

## Contract tests

`tests/contract/` is the executable copy of what the contract promises — one assertion per
documented fact, the contract itself as the oracle:

| File | Asserts |
|---|---|
| `test_accounts_contract.py` | `POST /accounts` ⇒ 201, `GET /accounts/{accountId}` ⇒ 200, each with `accountResponse`'s field names and JSON types |
| `test_transactions_contract.py` | `POST /transactions` ⇒ 201 with `transactionResponse`'s field names and JSON types |
| `test_error_responses_contract.py` | a request that breaks a documented request field type ⇒ the documented 400 (`POST /accounts`, `GET /accounts/{accountId}`) or 422 (`POST /transactions`), each with `errorResponse`'s single `error` field as a string |

```bash
make test-contract                              # `-m contract -v`
python -m pytest -m contract -v
```

They are neither a hand-rolled OpenAPI/JSON-Schema validator nor a second functional suite. The
documented status, and the documented field names and JSON types, are asserted; everything the YAML
never binds — document-number length and uniqueness, the operation-type list, the amount's sign, the
`event_date` format, error message texts, `404`/`405` — is either left to the functional tests or
named as unasserted in the module docstring that owns the decision. Each docstring also states the
one oracle its assertions come from.

Because the mock replays the contract's own examples and validates the requests it is asked to
serve, these tests are green in the default mock environment too. The rest of a mock
run is red by design — [Mock vs real environment](#mock-vs-real-environment) says which
cases the mock can serve and which need a stateful service. Against a real environment the
same tests run unedited — the only input
that has to exist there is the data they address: the read of `GET /accounts/1` and the write of
`POST /transactions` need that account to exist.

## Mock vs real environment

`make mock` runs the contract's own examples through Prism, which validates each request
it is served but stores nothing: the call is answered from the example and the response
never echoes the request. That is enough for the contract tests and for the plumbing, and
it is why a full `make test` against the mock is red by design — the functional cases need
a service that keeps state.

| Case | Against the mock | Needs a real service |
|---|---|---|
| A field of the wrong type: a non-string `document_number`, a string `operation_type_id` | the documented `400` / `422` and `errorResponse` body | — |
| A request the YAML never constrains: an empty, short, long or non-digit `document_number`, `amount: 0`, an unlisted `operation_type_id` | replayed as `201`; the rejection cases (C3a findings, not contract) fail | yes |
| Round-trip values: the `document_number` an account was created with, a transaction's `amount` / `operation_type_id` | the example is replayed, so the assertion fails, or fails in the fixture that creates the account | yes |
| A read of data that has to exist: `GET /accounts/1`, a transaction for a real account | satisfied by the example | yes |
| `404` for an unknown account | not reproducible: `GET /accounts/999` answers `200` with the example | yes |
| A route or method the contract does not define | Prism's own `problem+json` (`405`), not the contract's `errorResponse` | yes |

Pointing `--base-url` (or `PISMO_BASE_URL`) at a real environment is the only change the
tests need: nothing under `tests/` knows which one it is talking to.

## Parallel runs (opt-in)

The same suite split across worker processes by `pytest-xdist`; the two report files
and everything else about a run are unchanged:

```bash
make test-parallel                            # -n auto: one worker per physical core
make test-parallel WORKERS=4                  # a fixed worker count
PYTEST_ADDOPTS="-n auto" python -m pytest     # turn it on without editing the file
```

`-n` is not in `pytest.ini` on purpose: a default run stays single-process, so its
order and the number of API calls it makes are predictable, and `PYTEST_ADDOPTS`
(applied after `addopts`) turns parallelism on without editing the repository. Two
rules keep the suite distributable — no test may depend on another test's state or
on execution order, and `parametrize` inputs must be ordered (a `set` breaks
distribution). One consequence to know: session-scoped fixtures run once **per
worker**, so `-n4` issues up to four `POST /accounts`. At the current size (33 tests
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
artifacts/           the C1-C5 and T1 write-ups as PDFs
conftest.py          run-wide pytest options (--env/--base-url), report header, settings fixture
contract/            the API contract under test
docs/                one pointer note per artifact (C1, C2, C3a/b, C4, C5, T1)
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
tests/contract/      the contract's own promises, executable (documented status + shapes)
tests/data.py        test-data helpers (unique document numbers)
```

Each module's docstring records why it is shaped that way — the HTTP layer's no-retry and
`allow_redirects=False` choices, the configuration's precedence, why authentication is
deliberately absent — and `AI_NOTES.md` records the design suggestions that were considered
and rejected.
