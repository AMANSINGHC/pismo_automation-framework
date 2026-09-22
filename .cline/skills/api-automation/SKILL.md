---
name: api-automation
description: Work on the Pismo API test automation framework in this repository — a layered pytest + requests suite driven by the Swagger 2.0 contract in contract/. Use when a request touches tests/, src/clients/, src/models/, src/utils/, src/config/, conftest.py, pytest.ini, requirements.txt, or the Makefile test/mock targets; when asked to add or change an API test, add an operation to a service client, add a request/response model, wire or change a fixture, switch environment or base URL, fix a failing or skipped run, interpret reports/junit.xml or reports/report.html, or run the suite in parallel; and before answering architecture questions about this framework. It encodes the layer boundaries to preserve, the execution flow, configuration precedence, fixture/DI rules, request-response modeling, assertion and test-data strategy, coding conventions, and the contract gaps that must never be guessed at. `contract/`, `docs/` and `artifacts/` are read-only here — a change needed in them is reported back, never written.
---

# API automation — pismo_automation-framework

A contract-driven API test framework: pytest + requests, one suite over the operations the
contract in `contract/` documents, run first against a Prism mock of that contract and then
against a real environment.

Every rule below follows from one sentence: **a test states intent; the layers do the
work.** If you are about to write a URL, a session, a header, a payload dict, or a raw
`requests` call inside a test, you are in the wrong file. See §1.

Treat each MUST/NEVER as a gate on your diff, and run §13 before reporting a change as
done. Contract gaps (§8) are the one place where the correct action is usually **not**
to write code. `contract/`, `docs/` and `artifacts/` are read-only (§1, §16): read them,
never write them.

## 1. Where a change goes — decide before you edit

| Asked to… | Edit | Never |
|---|---|---|
| Add/change an assertion or scenario | `tests/<service>/test_<endpoint>.py` | no HTTP/plumbing in a test |
| Add an operation to a service | `src/clients/<service>_client.py` (keep path constants there) | no assertions in a client |
| Add/change a request or response field | `src/models/<service>.py` | don't invent a field the contract lacks (§8) |
| Add a reusable assertion | `src/utils/assertions.py` | don't import clients or `requests` there |
| Point a run at another environment | `src/config/environments.yaml` | never read env vars outside `src/config` |
| Change base URL / timeout / header logic | `src/config/settings.py` | no domain knowledge in config |
| Change fixtures (HTTP layer, clients, shared state) | `tests/conftest.py` | not for per-test data (that is `tests/data.py`) |
| Change a run-wide option, the header line, the `settings` fixture | root `conftest.py` | don't move the service fixtures there |
| Change run flags, markers, reports | `pytest.ini` | don't pass report flags by hand per run |
| Change how a run is launched | `Makefile` | don't change the default `test` target's behaviour |
| Generate test data (unique document numbers) | `tests/data.py` | don't inline random data in a test |
| Add/upgrade a dependency | `requirements.txt` (exact pin) | no unpinned or unused deps |
| Change the contract, a register or an artefact | nothing — the read-only folders (§16) |

**Read-only folders — `contract/`, `docs/`, `artifacts/`.** Read them freely: the contract is
the field-level truth and the registers are citations. Never create, edit, delete or
regenerate a file in those three folders (§16) — no YAML patch to make a test pass, no
finding filed by you, no refreshed PDF. A change needed there is reported, not written.

Layer responsibilities and the reasoning behind them are in
`docs/C4_automation-architecture.md` — read it before a non-trivial change; it is the
architecture's own description, and a boundary change is reported against it, not written
into it (§16).

**Dependency direction (one way only):** `tests → src/clients → src/utils → src/config`,
plus `src/clients → src/models`; `src/models` and `src/config` are leaves.
Never introduce: `tests` importing `requests`; anything in `src/` importing `tests` or
`pytest`; a per-resource client touching sessions/URLs/headers; `src/utils/transport/`
knowing a domain path; an `os.environ` read outside `src/config`; `src/models` or
`src/config` importing another `src` package.

## 2. Execution flow of a run — know this before debugging

1. `pytest.ini`: `testpaths = tests`, `pythonpath = .` (so `src…` and `tests…` import),
   `addopts` (both report flags + `--strict-markers --strict-config`).
2. Root `conftest.py`: registers `--env` / `--base-url` in the `pismo` option group,
   prints the header `pismo: environment=… base_url=… timeout=…s config=…` exactly once
   per run (before the first test), and defines the session-scoped `settings` fixture —
   which **skips** the run with an actionable reason when the selected environment has
   no usable base URL.
3. `tests/conftest.py` builds the session-scoped stack:
   `settings → http_client → accounts_client` / `transactions_client`, plus
   `existing_account`, which really creates an account over the API and raises
   `RuntimeError` (with method, URL and body) if it is not `201`.
4. The test body: build the request model → one client method → `assert_status` →
   `assert_shape` → specific assertions → `response.model(...)`.
5. Teardown: `http_client.close()`; pytest writes `reports/junit.xml`; pytest-html
   writes `reports/report.html`.

## 3. Run it — the loop you will actually use

```bash
make install                     # .venv on python3.12 + pinned requirements.txt
make mock                        # Prism on :8080 from the contract — leave it running
make test                        # whole suite against prism (the default environment)
make test-parallel WORKERS=2     # opt-in xdist; same two report files
python -m pytest --env staging --base-url https://…   # then the same suite on a real env
```

- `make mock` is foreground. To background it:
  `nohup prism mock -p 8080 contract/<file>.yaml > /tmp/prism.log 2>&1 &`
  then poll until it serves and the suite can start — any request that answers, instead of
  refusing the connection, proves it:
  `curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/` returns Prism's own `404`
  for a route the contract does not define (§9).
  `EADDRINUSE` in the log means a mock is already up — that is fine, do not kill it blindly.
- By hand: `source .venv/bin/activate`, then `python -m pytest …`. Make recipes activate
  the venv in their own shell and refuse to run without one (`make install` first).
- The mock is the first gate, not the only one: re-run the same tests, unedited, against a
  real environment (`PISMO_ENV=… PISMO_BASE_URL=… python -m pytest`, or fill `base_url` in
  `src/config/environments.yaml`). An environment that has no base URL yet skips the run
  with the exact place to set it (§5) — that is configuration, not a test failure.
- **Green looks like:** the `pismo:` header line, `collected 20 items`, `4 passed, 16 xfailed`
  (the `xfailed` nodes are the deliberately parked mock-vs-real cases, §9: the five account
  validation cases, `test_get_unknown_account`, all four `test_create_transaction` types, the
  two `test_amount_round_trip` amounts and the four invalid-request cases of
  `test_create_transaction_with_invalid_request` — Prism replays the contract example, so no
  amount, sign, `type` or operation type is echoed, and it applies no amount, operation-type or
  account rule at all),
  plus `- generated xml file: …/reports/junit.xml -` and `- Generated html report: …`. A
  missing header line means configuration is broken, not that the tests are fine.
- Never call a change verified on a subset: a marker selection (`-m …`), `-k` and `--env`
  change what actually ran. Report the command you ran and how many tests passed.

## 4. Fixtures and dependency injection — the only way tests get dependencies

| Fixture | Defined in | Scope | Provides |
|---|---|---|---|
| `settings` | root `conftest.py` | session | resolved `Settings` (base URL, timeout, headers), or skips the run |
| `http_client` | `tests/conftest.py` | session | `HttpClient` bound to the environment; `close()`d on teardown |
| `accounts_client` / `transactions_client` | `tests/conftest.py` | session | service clients over that one HTTP layer |
| `existing_account` | `tests/conftest.py` | session | an `AccountResponse` for an account really created over the API |

Rules:
- A test **asks for** what it needs as a parameter and annotates the type
  (`accounts_client: AccountsClient`). Never construct `Settings`, `HttpClient`, a
  client, a `requests` object, or a URL inside a test.
- Shared setup needed by several tests → a session-scoped fixture in `tests/conftest.py`,
  next to the existing ones. It must be visible in the test signature: no fixture in this
  repo is `autouse`, and a test should show what it depends on.
- A fixture that prepares remote state asserts its own precondition **loudly** with a
  `RuntimeError` naming the expected status, method, URL and body — the `existing_account`
  pattern. A broken environment must not be reported as a test failure, and must not be
  silently skipped either.
- Run-wide concerns (CLI options, the header line, `settings`) live in the **root**
  `conftest.py`; service-level fixtures stay in `tests/conftest.py`. Keep that split.
- Fixtures never assert the thing under test (that is the test's job) and never swallow
  exceptions; the client methods return the response untouched so the test can assert it.
- Fixtures that create remote state are also the reason `-n` costs extra API calls — see §12.

## 5. Configuration and environment handling

Precedence (highest first): explicit argument (`load_settings(base_url=…)`) →
pytest CLI (`--env`, `--base-url`) → environment variables (`PISMO_ENV`,
`PISMO_BASE_URL`, `PISMO_TIMEOUT_S`) → `src/config/environments.yaml`
(`environment`, `defaults.timeout_s`, `environments.<name>.base_url`).

- Add an environment by adding a key under `environments:` in the YAML — no code change.
  Shipping one with `base_url: ""` is the intended state for an environment you cannot
  reach yet: the run **skips** with the exact place to set the URL.
- `ConfigError` means unusable configuration (missing/unknown environment, no base URL,
  non-numeric or `<= 0` timeout, malformed YAML). At the fixture it becomes a skip; in the
  header it appears as `not configured (…)`. Never turn it into a hard test failure and
  never paper over it with a default URL.
- `src/config/environments.yaml` is the source of truth; env vars are overrides only, so a
  clean clone works with no setup. Do not require an env var anywhere.
- Requests send `Accept`/`Content-Type` from `_default_headers()` only. **Authentication is
  deliberately unimplemented** (contract gap, §8): do not add a token header, credential
  env var, or plumbing to guess a mechanism. When a mechanism is confirmed, it is resolved
  in `src/config/settings.py` so every client picks it up from one place.

## 6. Request and response modeling

- Every wire shape is a **frozen dataclass** in `src/models/<service>.py`: requests expose
  `to_payload()`, responses a `from_payload(cls, payload)` classmethod. Keep the casts
  explicit (`int(payload["account_id"])`, `float(...)`, `str(...)`) and stay tolerant where
  the contract is loose (`payload.get("error", "")`, as `ErrorResponse` does).
- The `*_RESPONSE_FIELDS` mapping used by `assert_shape` is **derived** from the dataclass
  (`{f.name: f.type for f in fields(...)}`). Never hand-write a second field list or a
  parallel schema dict — adding a field to the dataclass must extend the shape assertion
  automatically, and it is the reason field names have one source of truth.
- Add a model field only when the contract defines it (or as part of a recorded gap work
  item, §8). Enum-like identifiers become an `IntEnum` (`OperationType`) instead of bare
  ints in test bodies, and a value set the contract only exemplifies (`type: debit`) becomes a
  `str`-valued `Enum` (`TransactionType`): usable as an expected value, never as the dataclass
  annotation, because `assert_shape` matches annotations with `isinstance` and `_matches_type`.
- Path constants live in the client module (one `<RESOURCE>_PATH = "/<route>"` per route),
  not in the tests and not in the HTTP layer.
- A client method: one operation, `HTTPMethod.X` + `self._send(...)`, return the
  `ApiResponse` **untouched** — no status branching, no retry, no logging, no assertion.
  One-line docstring; add a second line only for a real caveat.
- Transport stays domain-free: `src/utils/transport/` knows about methods, URLs, timeouts
  and the `ApiResponse` envelope (`method`, `url`, `status_code`, `headers`, `body`,
  `elapsed_ms`, `raw`) — never about accounts or transactions. Keep it promotable into a
  shared infrastructure package.

## 7. Assertions and test data

Assertion order in a test (do not reshuffle it — the messages depend on it):
1. `assert_status(response, HTTPStatus.CREATED)` — always first; its message shows the
   status, method, URL and body, so a failure is readable without re-running.
2. `assert_shape(response.body, ACCOUNT_RESPONSE_FIELDS)` — presence **and** JSON type of
   every documented field.
3. `response.model(...)` for typed access — build the model as soon as the shape holds, so
   every field-level check below reads model attributes, never dict keys.
4. Field-specific checks on the model: `assert_iso8601(transaction.event_date)`,
   comparisons against the request you sent or against the `existing_account` fixture, then
   the model assertions (`account.account_id > 0`,
   `account.account_id == existing_account.account_id`).

Rules:
- Assert on the `ApiResponse` (`status_code`, `body`, `model(...)`). `response.raw` is an
  escape hatch: use it only with a comment saying why. Never call `response.json()` in a test.
- Read field values off the typed model (`response.model(...)`) — never `response.body["field"]`
  in a test. `response.body` is passed whole to `assert_shape` and echoed in `assert_status`
  failure messages; nothing else indexes it.
- Reuse `src/utils/assertions.py`. A repeated assertion becomes a helper **there** — with
  expected-vs-actual and the offending payload in the message — not a copy-pasted block.
- `assert_shape` compares types via `_matches_type`: `bool` never counts as `int`, `float`
  accepts any JSON number. Do not re-implement that nuance in a test.
- Error payloads are read off `ErrorResponse`: the field is `error`, not `message`, and the
  text is compared with **exact equality** (`assert error.error == expected_error`) — never a
  substring, a regex or a paraphrase, because a re-worded assertion invents a contract nobody
  has. `assert_status` runs first, so a wrong status still reports the whole body.
- Assert only what the contract supports (§8). When you must weaken an assertion, keep the
  weakest invariant that is still true and leave a comment naming the gap — the existing
  tests show the house style for that comment.
- An assertion must be true on the mock **and** on a real environment — the same tests run
  in both (§9). Never pin a mock artefact (a replayed example value, an echoed id) as the
  expected result, and never narrow an assertion just to keep the mock green.
- No sleeps, retries or polling to make an assertion pass; flakiness is a finding to raise,
  not something to hide. There is no contractual latency budget, so do not assert one.

Test data:
- Generated/unique data lives in `tests/data.py` (`unique_document_number()`); per-scenario
  constants are module-level UPPER_CASE in the test file (`TRANSACTION_AMOUNT = 50.0`). A value
  that two endpoints' tests share goes in `tests/data.py` **once** — `UNKNOWN_ACCOUNT_ID`, used
  by both `test_get_unknown_account` and `test_create_transaction_with_invalid_request`: never
  copy the literal into each file (two homes drift), and never import one test module from
  another. No magic values inline, no `faker`, no data files.
- An expected error message is a module-level constant **next to the value that triggers it**
  (`ZERO_AMOUNT = 0.0` with `ZERO_AMOUNT_ERROR = "amount can't be zero"`), and it travels with
  that value through the same `pytest.param(amount, expected_error, id=...)`. The contract
  documents no message text for any status, so every such constant is caller-supplied: assert
  only messages you actually know, and report them as assumptions (§8) — the same treatment as
  `EXPECTED_SIGN_AND_TYPE`.
- Anything a test needs to pre-exist comes from a fixture — never a hardcoded id and never
  another test's leftovers (that would break `-n`, §12).
- The length guard in `tests/data.py` (`DOCUMENT_NUMBER_MIN_LENGTH` 10,
  `DOCUMENT_NUMBER_MAX_LENGTH` 14, default 11) is a **test-side** constraint, not a contract
  rule (§8). Keep using the generator rather than fixed document numbers.

## 8. Contract usage and required gaps handling

Read the contract in `contract/` (Swagger 2.0 — read-only, §16) before writing or changing
any assertion: 3 operations, tags `accounts` / `transactions`, `definitions.*` is the only
field-level truth, and the operation `description` prose is the only source for the
operation-type list and the amount-sign statement. `host: localhost:8080` and `basePath: /`
are mock-local — environment targeting comes from `src/config/environments.yaml`, never the
contract.

Existing registers to cite (read-only, §16 — do not re-derive an audit from scratch):
`docs/C3a-contract-audit.md` + `artifacts/C3a_contract-findings.pdf` (findings register),
`docs/C3b-schema-validation-consumer-contracts-mock-fidelity.md` + its PDF,
`docs/C4_test-design.md` + its matrix. **A new finding is reported, not filed**: you name it
in your summary and in the test's explanatory comment; the register write is the caller's
separate change.

Where the contract is silent — do not invent a rule:

| Contract gap (verified in the YAML / C3a) | What you must do instead |
|---|---|
| No `securityDefinitions`; no auth mechanism anywhere (C3a finding) | Never add credentials, tokens, auth headers or auth env vars — `_default_headers()` explains why |
| `amount` has no min/max/precision; the sign rule is prose only ("send a positive amount, the server applies the sign"), and the response example is `-100.5` while the request example is `50` | Never assert bounds, rounding or an unstated precision. `test_create_transaction` **does** assert the amount as sent, signed (`expected_sign * TRANSACTION_AMOUNT`), and the `type`, from `EXPECTED_SIGN_AND_TYPE` — a caller-supplied assumption, labelled as such in the code and reported as a gap, not a contract rule, and not evidence that the YAML echoes the amount or defines the sign. `test_amount_round_trip` reuses that signed expectation for a whole-number and a fractional amount — the model writes every amount as a JSON number, so the integer case leaves as `50.0`, and the decimal case is chosen to be exactly representable — and `test_create_transaction_with_invalid_request` carries the 422 for `0` and for a negative amount **plus** the exact message the service answers each with (`amount can't be zero`, `amount can't be negative`) — the same kind of caller-supplied assumption about a rule the prose only implies, and about text the YAML never states: parked, and never presented as a bound or a message the contract sets. That test also carries two cases this row's neighbours would otherwise each grow their own test for (an unknown `operation_type_id`, an account that does not exist): four near-identical bodies for four invalid inputs is the duplication this skill keeps warning about, so a new 422 trigger is a `pytest.param` here, adding a case without adding a test |
| No idempotency key, no duplicate-submission semantics | Never double-send a `POST` to prove "charged once"; never retry a POST (§ transport rules) |
| `operation_type_id` has no `enum` (1–4 exist only in prose); no definition has `required` | Don't invent an allowed-value list out of the four types, and don't assume a missing field is rejected — but a real service **is** known to reject an unknown id with 422 `possible operation type - 1, 2, 3, 4`, whose own text corroborates that the prose list is exhaustive while leaving it unstated: that case sits in `test_create_transaction_with_invalid_request[unknown-operation-type]` (`UNKNOWN_OPERATION_TYPE_ID = 5`, one past the list), parked with the rest of that test because the YAML binds no 422 condition. The response echo is asserted for every documented type — and on the mock the whole `test_create_transaction` is parked (§9), never weakened |
| `account_id` on `POST /transactions` has no existence rule in the YAML (and no request field is ever `required`) | Don't invent one, and never assert a `404` for a write: a real service answers `422 account doesn't exist` for an account that is not there, and `test_create_transaction_with_invalid_request[unknown-account]` asserts exactly that (`UNKNOWN_ACCOUNT_ID` from `tests/data.py`, parked with the rest of the test because the YAML binds no 422 condition). `GET /accounts/{id}` words the same condition `account not found` — and `errorResponse.error`'s only `example` is that wording — so neither is a message the contract fixes: keep one constant per endpoint, never copy one across, and report the pair as a finding |
| `document_number: string` with no `minLength`/`maxLength`/`pattern` | Don't present or assert `tests/data.py`'s 10–14 bound as a contract rule — park the length cases as `xfail` (§9), as `test_create_account_with_invalid_document_number` does — that one test carries every invalid-input case as data, the non-digit `422` included, because `expected_status` is a parameter alongside `expected_error`; the 409 (duplicate) case in that file is parked the same way, none of those rules being in the YAML |
| `event_date: string` with no `format: date-time` | Our ISO-8601 + timezone check is stricter than the contract: keep it, but never claim the contract requires it |
| `type: string`, only the example `debit`, no enum or allowed-value list | Don't invent an allowed-value list the contract does not state. `TransactionType` (a `str`-valued `Enum`: `DEBIT`, `CREDIT`) holds only the expected values — the model field stays `str`, because `assert_shape` resolves annotations with `isinstance`. `test_create_transaction` asserts `DEBIT`/`CREDIT` per operation type from the same caller-supplied assumption, kept labelled and reported; never generalise it to another field |
| `400/404/405/422` exist without documented conditions; `errorResponse` has one non-required field, no error codes | Only assert the documented error shape where the environment really produces it — and never against the Prism mock (§9). A new error test needs the trigger to be contractual first — where a real service's rule is known but absent from the YAML, park the test as a non-strict `xfail` naming the gap instead of leaving it out (e.g. `test_get_unknown_account`, `test_create_transaction_with_invalid_request`). `errorResponse` documents no message text either, so a message assertion is caller-supplied by definition: assert it exactly, from a constant named after the triggering value, and only where you know it — the mock produces no error body at all (§9). Two endpoints already word one condition differently (`account not found` on `GET /accounts/{id}` against `account doesn't exist` on `POST /transactions`): never copy a message from the endpoint next door, and report such a pair as a finding rather than anointing either wording as canonical |
| No `required`, no `additionalProperties: false`; `assert_shape` checks presence and type of all documented fields | Know that `assert_shape` is **stricter** than the contract — keep it as the suite's fidelity bar, but never call it schema validation, and don't extend it to reject unknown fields without a contract change |
| No list/pagination endpoints; no rate-limit, retry, correlation-id or observability contract; versioning only via `info.version: "1.0"` | Don't infer paging, throttling or tracing assertions; those behaviours are not observable yet |

## 9. Mock vs real environment — what the mock cannot verify

`make mock` runs `prism mock -p 8080` against the contract in `contract/`; a Prism 5.x
mock accepts this Swagger 2.0 file. The suite runs against the mock first and then against a
real environment (§3, §5), so every assertion has to hold in both. Know the mock's fidelity
gaps before blaming a red run:

- **Stateless, replays the contract example, never echoes the request.** Value round-trips
  (`document_number` and `operation_type_id` echoed back, `GET` returning what you created,
  amount equality) cannot be asserted on the mock. Write the assertion the real service must
  satisfy anyway and park exactly what the mock cannot produce — the whole test, with one
  `pytest.param` per input the mock cannot satisfy, since the replayed example meets none of
  them: `test_create_transaction` asserts the echoed amount (signed) and `type` for all four
  documented types, and Prism replays `operation_type_id 1, -100.5, debit` for every one of
  them, so one non-strict `xfail` covers the test (§10A). `test_create_account` keeps its shape
  check plus a comment naming the real-env `document_number` equality, because there the
  example value equals the one the test sends. A single-resource read answers with the contract
  example whatever id you ask for, so `existing_account` proves the flow, not the data — and an
  unknown id draws that same 200 example, which is why `test_get_unknown_account` is parked as
  `xfail` (§8). A write's amount is the same story: `test_amount_round_trip` shares
  `MOCK_REPLAYS_EXAMPLE` with
  `test_create_transaction` for a whole-number and a fractional amount, and
  `test_create_transaction_with_invalid_request` is parked on rules the prose states (a positive
  amount) or the service applies (a known `operation_type_id`, an account that exists) but the
  YAML never binds to 422 — and whose message text the YAML never gives, so the message it
  asserts (`expected_error`, one per case) is caller-supplied too. `prism mock --errors` does
  not change any of that, because none of the four cases violates a part of the schema the YAML
  states (no `minimum`/`maximum` on `amount`, no `enum` on `operation_type_id`, no
  account-existence rule): the mock answers 201 with a transaction body that has no `error`
  field, so the run stops at the status assertion and the message check is never reached — it
  cannot pass vacuously.
- **Request validation is off by default.** Negative tests that rely on it need
  `prism mock --errors` on the mock, and their real home is the real environment; without
  the flag a violated schema is not an error response.
- **Unmatched routes return Prism's own `problem+json`, not `errorResponse`.** Error-shape
  assertions are verified on a real environment, never against the mock.
- So a read of an unknown resource, a write against real state, 4xx body shapes and
  idempotency are real-environment assertions: write them for the contract's behaviour and
  select that environment (`--env` / `PISMO_ENV`, §5) rather than deleting or weakening the
  assertion. While a real environment is unreachable, a missing documented condition is a gap
  you report (§8) — the register is not yours to edit (§16).
- Never "fix" a mock-specific failure by weakening an assertion that a real environment
  would satisfy; report it as a gap (§8) and name it in the test's comment.
- What the mock is worth: the first gate on happy-path status codes, response shape/type,
  contract example conformance, and exercising the client/HTTP/configuration plumbing end to
  end.

## 10. Recipes

**A. Add a test for an existing endpoint** (one file per endpoint; the file names must be
unique across `tests/**` — there is no `__init__.py`, so pytest imports by basename):

1. `tests/<service>/test_<endpoint>.py` (new endpoint) or a new test in the existing file.
2. Module docstring in the house form: `` ``<METHOD> /<path>`` — contract tag: ``<service>``. ``
3. Class `Test<Operation>` decorated with the **service** marker; the critical happy path
   additionally carries the subset marker the existing tests use (§14).
4. Request the fixtures you need as annotated parameters; never build the plumbing.
5. One-line docstring stating the guarantee; module-level constant for a scenario value.
6. Exactly one client call, then assert in the §7 order.
7. Any new marker must be declared in `pytest.ini` (`--strict-markers` fails the run
   otherwise). Finish with `make test` (§13).

```python
"""``<METHOD> /<path>`` — contract tag: ``<service>``."""

import pytest

from http import HTTPStatus
from tests.data import unique_document_number
from src.clients.accounts_client import AccountsClient
from src.utils.assertions import assert_shape, assert_status
from src.models.account import ACCOUNT_RESPONSE_FIELDS, AccountResponse, CreateAccountRequest


@pytest.mark.accounts
class TestCreateAccount:

    # The critical happy path also carries the subset marker the existing tests use.
    def test_create_account(self, accounts_client: AccountsClient) -> None:
        """A new account is answered with 201 and the documented response shape."""
        request = CreateAccountRequest(document_number=unique_document_number())

        response = accounts_client.create_account(request)

        assert_status(response, HTTPStatus.CREATED)
        assert_shape(response.body, ACCOUNT_RESPONSE_FIELDS)
```
(Fuller examples: the three files already in `tests/`; the real `test_create_account` is this
body parametrized over the minimum, default and maximum document lengths, and the real
`test_create_transaction` over the four operation-type IDs the contract's description lists —
one `pytest.param` per type, in the order the description lists them, sharing one body that
asserts the real behaviour and carries a single non-strict `@MOCK_REPLAYS_EXAMPLE` `xfail` on the
test, since Prism cannot satisfy any of its four inputs (§9). The same file adds
`test_amount_round_trip` — two `pytest.param` amount forms, the same replay mark on the whole
test — and `test_create_transaction_with_invalid_request`, which carries its own
`MOCK_ACCEPTS_INVALID_REQUEST` and asserts the 422, the error shape and the service's message for
four inputs, one `pytest.param` each: a zero amount, a negative amount, an unknown
`operation_type_id` and an unknown `account_id` (`expected_error` travels with each triggering
value).)

**B. Add an operation to a service** (client + model + test):

1. Contract first: confirm the operation and response exist in `contract/…yaml`. If they
   do not, this is a §8 gap — report it, and never implement a guessed contract or patch
   the YAML (§16).
2. `src/models/<service>.py`: add the frozen request/response dataclasses with
   `to_payload()` / `from_payload()`, then the derived `*_RESPONSE_FIELDS`. Contract fields
   only.
3. `src/clients/<service>_client.py`: add a path constant if the route is new, then the
   method (`HTTPMethod` + `self._send`), returning the untouched `ApiResponse`. No
   assertions, no status branching.
4. `tests/<service>/`: the test per recipe A. Add a session fixture in `tests/conftest.py`
   only if the scenario needs **pre-existing** state.
5. Register any new marker in `pytest.ini`; tag the class with the service marker.
6. If you changed a fixture, the client or the HTTP layer, also run the parallel mode (§12).
7. Report the boundary change in your summary when you add a layer, a client, a fixture kind
   or a cross-cutting behaviour: `docs/C4_automation-architecture.md` is the architecture's
   own record and read-only here (§16), so updating it is the caller's separate change.

**C. New service** (e.g. a `cards` service): `src/models/cards.py` +
`src/clients/cards_client.py` + a session-scoped `cards_client` fixture in
`tests/conftest.py` beside the others + `tests/cards/` + a `cards:` marker in
`pytest.ini` + a row in the README layout. The matching rows in the C4 documents are a
reported change, not a write (§16). Nothing else in the framework needs to change — that is
the point of the boundary.

## 11. Reporting — do not break it

- `pytest.ini`'s `addopts` owns both artefacts, so **every** run writes them (make target,
  IDE runner, CI, bare `pytest`): `reports/junit.xml` (`--junit-xml`, pytest core) and
  `reports/report.html` (`--html --self-contained-html`, pytest-html with the
  pytest-metadata environment table). Keep those flags in `addopts`; don't repeat them in
  recipes or README commands, and don't remove them.
- Stable CI contract: `junit_suite_name = pismo`, `junit_family = xunit2`, one `<testcase>`
  per test with its duration, each failure's message verbatim. A CI job can re-point the
  files without editing the repo: `python -m pytest --junit-xml=/tmp/junit.xml
  --html=/tmp/report.html --self-contained-html` (an explicit CLI flag beats `addopts`).
- Keep the HTML **self-contained**: a hand-run without `--self-contained-html` writes an
  `assets/` folder and breaks the "single openable file" promise.
- `reports/` is gitignored output: never commit it, and never quote results from a stale
  file — re-run, then read the header line and the counts.
- The environment is printed on stdout, not stamped into the artefacts. If a job runs
  several environments, give each its own `--junit-xml`/`--html` path (known limitation,
  recorded in `docs/C4_automation-architecture.md`).
- Under `-n` both plugins write once from the controller: one merged XML and one HTML with
  every test. Do not add per-worker report flags.

## 12. Parallel execution — opt-in, both modes must stay correct

- The default stays single-process: `-n` is deliberately **not** in `addopts`, so a normal
  run's order and API-call count are predictable. Don't move it into `pytest.ini`.
- Turn it on per run: `make test-parallel WORKERS=N` (its guard prints an actionable message
  when `pytest-xdist` is missing), `python -m pytest -n4`, or
  `PYTEST_ADDOPTS="-n auto" python -m pytest` — `PYTEST_ADDOPTS` is applied after `addopts`,
  so CI can enable parallelism without editing the repository.
- A test must be distributable: (1) no dependency on another test's state or on execution
  order, (2) `parametrize` inputs ordered — never a `set`, (3) never assume a session
  fixture ran exactly once.
- Session-scoped fixtures run once **per worker**: `-n4` repeats the fixture's setup `POST`
  up to four times (and any other fixture setup). That is a real increase in API calls
  against a shared environment — flag it in your summary when you add such a fixture.
- Under xdist, `-s`/`--pdb` are unavailable, `record_testsuite_property` is unsupported, and
  pytest-html's `original` sort order is unreliable (the columns remain sortable).
- Against a stateful or money-moving environment, pin retries off
  (`--max-worker-restart=0`) so a crashed worker never re-executes a test that already
  changed state — and never add a retry to a `POST`.
- Verify a parallel run like any other: same two report files, same test count, header line
  still printed once. At the current size (20 tests) parallel is **slower** than sequential;
  it pays off as the suite grows or when tests wait on the network. Say that instead of
  overselling it.

## 13. Definition of done — run these before you report

```bash
make test                            # header line + "<N> passed" (N = collected count)
python -m pytest --env staging --base-url https://…   # same suite against a real environment
python -m pytest -m accounts -q      # if you added tests/markers: prove the selection works
make test-parallel WORKERS=2         # if you touched fixtures, clients, conftest or HttpClient
```

Boundary checks (copy-paste; each line's expected result is in the comment):

```bash
grep -rn "^import requests" tests/ src/models/ src/config/ src/clients/ --include='*.py'
#   only src/clients/base_client.py (a type hint) — nothing else outside src/utils/transport
grep -rn "^import pytest\|^from pytest" src/ --include='*.py'          # nothing
grep -rn "os.environ\|getenv" src/ tests/ --include='*.py'             # only src/config/settings.py
grep -rn "from tests\|import tests" src/ --include='*.py'              # nothing
grep -rn "^from src\." src/models/ src/config/ --include='*.py'        # nothing (leaves)
grep -rn "http://\|https://" tests/ src/clients/ src/models/ --include='*.py'   # nothing
grep -rn "^[[:space:]]*assert " src/ --include='*.py' | grep -v src/utils/assertions.py   # nothing
```

Then confirm, explicitly:

- [ ] every marker used is declared under `markers =` in `pytest.ini`;
- [ ] a new test file's basename is unique across `tests/**` (no `__init__.py` → collection error otherwise);
- [ ] a new dependency is pinned in `requirements.txt` and `make install` was run;
- [ ] `reports/junit.xml` has `<testsuite name="pismo" … tests="N">` with N equal to what you ran, and any failure message is verbatim in the XML;
- [ ] `git status --short` shows only intended files — `reports/`, `.venv/`, `__pycache__/`, `.pytest_cache/` stay ignored;
- [ ] no assertion was weakened without a comment naming the contract gap, and no sleep/retry was introduced;
- [ ] if a boundary, fixture kind, client or cross-cutting behaviour changed: `README.md` was updated when commands/layout changed, and the doc side of it is reported, not written (§16);
- [ ] if you found a new contract gap: it is named in your summary and in the test's comment, and not filed — the registers are read-only (§16);
- [ ] `git status --short -- contract docs artifacts` prints nothing (no YAML patch, register entry or refreshed PDF);
- [ ] your summary states the exact commands run, how many tests passed, which environment each run used (the mock, or a real one), and any side effects (extra `POST`s under `-n`, a shared environment used).

## 14. Conventions a diff must follow

- **Imports:** plain `import x` lines first, blank line, then `from x import y`. No
  isort/ruff configuration exists — match the file you are editing and never reorder or
  reformat a file you merely visited.
- **Docstrings:** every module opens with one that orients the reader; public classes,
  functions and methods are documented; a test method gets **one line stating the guarantee
  it pins**; docstrings in `src/config`/`src/utils` also carry the *why* (see
  `_default_headers`). When you change behaviour, update the docstring in the same commit.
- **Typing:** annotate every parameter and return (`-> None` on tests), use
  `Any`/`Mapping` from `typing`, unions with `|`, frozen dataclasses for wire shapes,
  `IntEnum` for identifier enums, a `str`-valued `Enum` for a field's value set that is only
  used as an expected value (`TransactionType`) — not as the wire-shape annotation.
- **Naming:** one folder per service; `test_<verb>_<resource>.py`; `Test<Operation>`;
  `test_<behaviour>`; `<Resource>Client` with `<verb>_<resource>()` methods;
  `<Resource>{Request,Response}` models; module constants UPPER_CASE; private helpers `_`.
- **Markers:** the service tag on the class, plus the subset marker the existing tests carry
  on the critical happy path; register every marker in `pytest.ini`.
- **Comments:** explain *why*, never restate the code; the contract-gap comments already in
  the tests are part of the deliverable — keep them and add yours where you weaken or narrow
  an assertion.
- **Line length / formatting:** no linter, formatter or type checker is configured (no
  pyproject, ruff, flake8, tox, pre-commit or CI workflow in this repo). The neighbour file
  is the style contract: wrap around 88–100, and check before you finish —
  `git ls-files '*.py' | xargs awk 'length>100'` must print nothing. The 89–100 band is where
  the suite lives (36 tracked lines across `src/` + `tests/` when this was written; the exact
  number is a snapshot, not a quota to fill or trim). Propose tooling in your summary; never
  smuggle a global reformat into a behavioural change.
- **Structure:** keep `__init__.py` files empty (packages are plain), keep one-file-per-
  endpoint and `tests/data.py` for generated data, and keep the diff in the layer that owns
  the change.
- **Dependencies:** exact pins in `requirements.txt`, and only when stdlib or `requests` does
  not already do the job. No new dependency for a one-line helper.
- **No stray output:** the `pismo:` header is the only sanctioned stdout; no `print` in `src/`
  or tests, no logging framework — failures must be visible through assertions.

## 15. Gotchas seen in this repository

1. `.venv` is gitignored and may be gone ("No virtualenv at … - run 'make install' first",
   typically after `make clean`). Run `make install`; never fall back to a system python.
2. `make test-parallel VENV=/abs/path` cannot work — the Makefile resolves
   `$(CURDIR)/$(VENV)`. Pass a relative `VENV=` or use a separate clone.
3. `make clean` deletes `.venv`, `.pytest_cache` and `__pycache__` — deliberately **not**
   `reports/`, so the last run's artefacts survive a clean. Don't assume they were removed.
4. `listen EADDRINUSE` from `prism mock` means a mock is already listening (fine). Confirm
   with the `curl` probe in §3 instead of concluding the mock is broken.
5. `--strict-config` turns a mistyped key in `pytest.ini` into a failure of **every** run —
   intentional; fix the key, don't drop the flag.
6. `20 skipped` / `skipped="20"` with a reason means the selected environment has no base URL
   (`--env staging` reproduces it). Read the header line before debugging a "broken" suite.
   `skipped="16"` in a mock run is not that: `xfail` also lands in that JUnit attribute, so
   check those nodes are `type="pytest.xfail"`, not `pytest.skip`, before blaming configuration.
7. Two test modules with the same basename in different folders abort collection with
   "import file mismatch" (reproduced). Rename; don't add `__init__.py` files to fix it.
8. `report.html` written without `--self-contained-html` also writes an `assets/` folder —
   keep the flag wherever the HTML is produced.
9. **Known drift:** the Makefile's `WORKERS ?= auto` while the README and the C4 table say
   `4`. Pass `WORKERS=` explicitly instead of quoting a default; correct the prose if you
   touch those files.
10. Stale `reports/` are easy to mistake for fresh results — re-run before quoting counts.
11. The venv is python3.12 (`PYTHON ?= python3.12`) and the code uses `X | None`-style
    unions: keep the 3.12 baseline when you add syntax.

## 16. Deliberate framework gaps — do not "fix" them silently

Known decisions and deferred work. If a task touches one, say so explicitly, get it agreed
and land it as its own scoped change — never as a side effect of an unrelated diff. The
documentation impact of such a change is reported, not written by you (§1).

- **`contract/`, `docs/` and `artifacts/` are read-only**: they are inputs — the contract is
  the field-level truth, the registers and PDFs are the citations — never outputs of your
  change. No YAML patch to make a test pass, no finding filed by you, no regenerated PDF:
  a change you believe is needed there goes in your summary as a proposal for the caller.
- **Authentication**: unimplemented by design, and not to be guessed (§5, §8).
- **Error-shape, negative and stateful flows**: verified on a real environment, not against
  the mock (§9) — do not fake them with a mock-side assertion.
- **Per-test environment gating**: there is none. The same tests run against the mock and
  then a real environment, and the only gate is run-level (an environment with no `base_url`
  skips the whole run, §5). Landing an assertion that can only hold on a real environment is
  therefore a scoped change to agree first — never a mock-side workaround.
- **CI**: the PR/nightly/prerelease gates in `docs/C4_test-design.md` are prose only; this
  repository has no CI configuration, so never claim a gate ran.
- **Reports**: one fixed pair of artefact paths, not stamped per environment (§11).
- **`make clean` deliberately leaves `reports/` alone** (§15), there is no lint/format/type
  gate (§14), and the Makefile `WORKERS` default drift (§15) is documentation debt — none of
  these is a bug to "fix" in passing; each is its own change, with its impact reported.

For depth, read in this order: `docs/C4_automation-architecture.md` (this framework's own
description) → `docs/C3a-contract-audit.md` + `artifacts/C3a_contract-findings.pdf` →
`docs/C4_test-design.md` + its matrix → `docs/C3b-…md` → `README.md` → the contract in
`contract/`. Reading is always allowed; writing is not (§1, §16). This skill is
instructions, not a replacement for reading the file you are about to change.
