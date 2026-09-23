---
name: api-automation
description: Work on the Pismo API test automation framework in this repository — a layered pytest + requests suite driven by the Swagger 2.0 contract in contract/. Use when a request touches tests/, src/clients/, src/models/, src/utils/, src/config/, conftest.py, pytest.ini, requirements.txt, or the Makefile test/mock targets; when asked to add or change an API test, add an operation to a service client, add a request/response model, wire or change a fixture, switch environment or base URL, fix a failing or skipped run, interpret reports/junit.xml or reports/report.html, or run the suite in parallel; and before answering architecture questions about this framework. It encodes the layer boundaries to preserve, the execution flow, configuration precedence, fixture/DI rules, request-response modeling, assertion and test-data strategy, coding conventions, and the contract gaps that must never be guessed at. `contract/`, `docs/` and `artifacts/` are read-only here — a change needed in them is reported back, never written.
---

# API automation — pismo_automation-framework

A contract-driven API test framework: pytest + requests, one suite over the operations the contract
in `contract/` documents, run first against a Prism mock of that contract and then against a real
environment. Every rule below follows from one sentence: **a test states intent; the layers do the
work.** If you are about to write a URL, a session, a header, a payload dict, or a raw `requests`
call inside a test, you are in the wrong file (§1).

Treat each MUST/NEVER as a gate on your diff, and run §13 before reporting a change as done.
Contract gaps (§8) are the one place where the correct action is usually **not** to write code. The
read-only folders are inputs, never outputs (§1, §16): read them, never write them.
## 1. Where a change goes — decide before you edit

| Asked to… | Edit | Never |
|---|---|---|
| Add/change an assertion or scenario | `tests/<service>/test_<endpoint>.py` | no HTTP/plumbing in a test |
| Add a cross-service journey | `tests/e2e/test_<journey>.py` — one test owning its call sequence, the only place several client calls belong | don't file a journey under a service, and don't put service fixtures in `tests/e2e/` |
| Add an operation to a service, or a request/response field | `src/clients/<service>_client.py` (path constants live there), `src/models/<service>.py` | no assertions in a client; don't invent a field the contract lacks (§8) |
| Add a reusable assertion or test helper | `src/utils/assertions.py`, `src/utils/concurrency.py` | don't import clients or `requests` there |
| Point a run at another environment, or change base URL / timeout / header logic | `src/config/environments.yaml`, `src/config/settings.py` | never read env vars outside `src/config`; no domain knowledge in config |
| Change fixtures (HTTP layer, clients, shared state) | `tests/conftest.py` | not for per-test data (that is `tests/data.py`) |
| Change a run-wide option, the header line, the `settings` fixture | root `conftest.py` | don't move the service fixtures there |
| Change run flags, markers, reports, or how a run is launched | `pytest.ini`, `Makefile` | don't pass report flags by hand per run; don't change the default `test` target's behaviour |
| Generate test data (unique document numbers) | `tests/data.py` | don't inline random data in a test |
| Add/upgrade a dependency | `requirements.txt` (exact pin) | no unpinned or unused deps |
| Change the contract, a register or an artefact | nothing — the read-only folders (§16) | |

**Read-only folders — `contract/`, `docs/`, `artifacts/`.** Read them freely: the contract is the field-level
truth and the registers are the citations. Never create, edit, delete or regenerate a file in those folders
(§16) — no YAML patch to make a test pass, no finding filed by you, no refreshed PDF: a change needed there is
reported, not written. `docs/C4_automation-architecture.md` is the architecture's own description — read it
before a non-trivial change, and report a boundary change against it rather than writing into it.

**Dependency direction (one way only):** `tests → src/clients → src/utils → src/config`, plus
`src/clients → src/models`; `src/models` and `src/config` are leaves. Never introduce: `tests`
importing `requests`; anything in `src/` importing `tests` or `pytest`; a per-resource client touching
sessions/URLs/headers; `src/utils/transport/` knowing a domain path; an `os.environ` read outside
`src/config`; `src/models` or `src/config` importing another `src` package.
## 2. Execution flow of a run — know this before debugging

1. `pytest.ini`: `testpaths = tests`, `pythonpath = .` (so `src…`/`tests…` import) and `addopts`
   (both report flags + `--strict-markers --strict-config`).
2. Root `conftest.py`: registers `--env` / `--base-url` in the `pismo` option group, prints the
   header `pismo: environment=… base_url=… timeout=…s config=…` — or `not configured (…)` — exactly
   once per run (before the first test), and defines the session-scoped `settings` fixture, which
   **skips** the run with an actionable reason when the selected environment has no usable base URL.
3. `tests/conftest.py` builds the session-scoped stack `settings → http_client → accounts_client` /
   `transactions_client`, plus the private `_created_account` helper behind `existing_account`
   (session) and `dedicated_account` (function): it really creates an account over the API and
   asserts the documented `201`, the shape, a positive id **and that the returned `document_number`
   is the one it sent**. That last round-trip is one the replaying mock cannot produce, so a mock run
   errors in fixture setup for every consumer (§9). Never skip instead.
4. The test body: request model → one client method → `assert_status` → `assert_shape` → specific assertions
   → `response.model(...)`; teardown closes `http_client`, then the two report files are written (§11).
## 3. Run it — the loop you will actually use

```bash
make install                     # .venv on python3.12 + pinned requirements.txt
make mock                        # Prism on :8080 from the contract — leave it running
make test                        # whole suite against prism (the default environment)
make test-smoke                  # `-m smoke -v`, the fast subset
make test-parallel WORKERS=2     # opt-in xdist; same two report files
python -m pytest --env staging --base-url https://…   # then the same suite on a real env
```

- `make mock` is foreground (`prism mock -p 8080 contract/transactions-service.v1.yaml`); to background
  it, `nohup prism mock -p 8080 contract/<file>.yaml > /tmp/prism.log 2>&1 &` and poll until it serves
  — `curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/` answers Prism's own `404` for an
  undefined route, which proves it is up. `EADDRINUSE` in the log means a mock is already listening.
  By hand: `source .venv/bin/activate`, then `python -m pytest …` — make recipes activate the venv in
  their own shell and refuse to run without one (`make install` first).
- The mock is the first gate, not the only one: re-run the same tests, unedited, against a real
  environment (`PISMO_ENV=… PISMO_BASE_URL=… python -m pytest`, or fill `base_url` in
  `src/config/environments.yaml`). An environment with no base URL skips the run with the exact place to
  set it (§5) — configuration, not a test failure.
- **Green looks like:** the `pismo:` header line, `collected <N> items`, `<N> passed`, the
  `- generated xml file: …/reports/junit.xml -` and `- Generated html report: …` lines. A missing
  header line means configuration is broken, not that the tests are fine.
- **A full green mock run does not exist here, by design.** Prism replays the contract example and stores
  nothing, so a mock run is largely red: the `existing_account` fixture asserts a `document_number`
  round-trip the mock cannot produce (its consumers error in setup), the account tests assert the echoed
  document number, and the negative, 4xx and idempotency cases assert conditions and message texts the
  YAML never binds. Parameters tagged `mock_compatible` mark the cases whose **own** expectations the
  replay satisfies; `-m mock_compatible` selects them. Never weaken an assertion — or the fixture — to
  move a case into it (§9).
- Never call a change verified on a subset: a marker selection (`-m …`), `-k` and `--env` change what actually
  ran — report the command, the pass count, and which environment.
## 4. Fixtures and dependency injection — the only way tests get dependencies

| Fixture | Defined in | Scope | Provides |
|---|---|---|---|
| `settings`, `http_client` | root / `tests/conftest.py` | session | resolved `Settings` (base URL, timeout, headers — or the run skips), and the `HttpClient` bound to it, `close()`d on teardown |
| `accounts_client` / `transactions_client` | `tests/conftest.py` | session | service clients over that one HTTP layer |
| `existing_account` / `dedicated_account` | `tests/conftest.py` | session / function | an `AccountResponse` really created over the API — shared by every test needing state, or fresh for the one test recording against it |

Rules:
- A test **asks for** what it needs as an annotated parameter (`accounts_client: AccountsClient`) and
  never constructs `Settings`, `HttpClient`, a client, a `requests` object or a URL itself.
- Shared setup needed by several tests → a session-scoped fixture in `tests/conftest.py`, next to the
  existing ones and visible in the test signature: no fixture in this repo is `autouse`.
- A fixture that prepares remote state asserts its own precondition with the shared `assert_status` /
  `assert_shape` helpers — the `_created_account` pattern (§2). A failure there is reported as an
  **error** in the fixture, never as a test failure, and the message carries status, method, URL and
  body. Never skip instead.
- Fixtures never assert the thing under test and never swallow exceptions; client methods return the
  response untouched so the test can assert it. They are also why `-n` costs extra API calls (§12), and a
  per-test fixture has to earn its extra setup `POST`: `dedicated_account` is the only function-scoped one,
  and it exists so a test can observe an account's **own** history without the shared account's other
  writes in it. Both fixtures share the private `_created_account` helper, so the precondition assertions
  exist once.
## 5. Configuration and environment handling

Precedence (highest first): explicit argument (`load_settings(base_url=…)`) → pytest CLI (`--env`,
`--base-url`) → environment variables (`PISMO_ENV`, `PISMO_BASE_URL`, `PISMO_TIMEOUT_S`) →
`src/config/environments.yaml` (`environment`, `defaults.timeout_s`,
`environments.<name>.base_url`).

- Add an environment by adding a key under `environments:` in the YAML — no code change. Shipping one
  with `base_url: ""` is the intended state for one you cannot reach yet: the run **skips** with the exact
  place to set the URL. The YAML is the source of truth and env vars are overrides only, so a clean clone
  works with no setup — never require an env var. `ConfigError` (missing/unknown environment, no base URL,
  non-numeric or `<= 0` timeout, malformed YAML) becomes a skip at the fixture and `not configured (…)` in
  the header: never turn it into a hard test failure and never paper over it with a default URL.
- Requests send `Accept`/`Content-Type` from `_default_headers()` only. **Authentication is deliberately
  unimplemented** (contract gap, §8): do not add a token header, credential env var or plumbing to guess a
  mechanism. When one is confirmed it is resolved in `src/config/settings.py`, so every client picks it up
  from one place.
## 6. Request and response modeling

- Every wire shape is a **frozen dataclass** in `src/models/<service>.py`: requests expose
  `to_payload()`, responses a `from_payload(cls, payload)` classmethod. Keep casts explicit
  (`int(payload["account_id"])`, `float(...)`, `str(...)`) and stay tolerant where the contract is
  loose (`payload.get("error", "")`, as `ErrorResponse` does).
- The `*_RESPONSE_FIELDS` mapping used by `assert_shape` is **derived** from the dataclass (`{f.name: f.type
  for f in fields(...)}`). Never hand-write a second field list or a parallel schema dict — adding a field to
  the dataclass must extend the shape assertion automatically; that is why field names have one source of truth.
- Add a model field only when the contract defines it (or as part of a recorded gap work item, §8).
  Enum-like identifiers become an `IntEnum` (`OperationType`) instead of bare ints in test bodies, and
  a value set the contract only exemplifies (`type: debit`) becomes a `str`-valued `Enum`
  (`TransactionType`): usable as an expected value, never as the dataclass annotation, because
  `assert_shape` matches annotations with `isinstance` and `_matches_type`.
- Path constants live in the client module (one `<RESOURCE>_PATH = "/<route>"` per route), not in the tests
  and not in the HTTP layer. A client method is one operation: `HTTPMethod.X` + `self._send(...)` returning
  the `ApiResponse` **untouched** — no status branching, no retry, no logging, no assertion. One-line
  docstring; a second line only for a real caveat (caller-supplied assumptions such as
  `IDEMPOTENCY_KEY_HEADER` are labelled there). Transport stays domain-free in turn: `src/utils/transport/`
  knows methods, URLs, timeouts and the `ApiResponse` envelope (`method`, `url`, `status_code`, `headers`,
  `body`, `elapsed_ms`, `raw`) — never accounts or transactions, and stays promotable into a shared
  infrastructure package.
## 7. Assertions and test data

Assertion order in a test (do not reshuffle it — the messages depend on it):
1. `assert_status(response, HTTPStatus.CREATED)` — always first; its message shows the status, method,
   URL and body, so a failure is readable without re-running.
2. `assert_shape(response.body, ACCOUNT_RESPONSE_FIELDS)` — presence **and** JSON type of every
   documented field.
3. `response.model(...)` for typed access — build the model as soon as the shape holds, so every
   field-level check below reads model attributes, never dict keys.
4. Field-specific checks on the model: `assert_iso8601(transaction.event_date)`, comparisons against
   the request you sent or against the `existing_account` fixture, then the model assertions
   (`account.account_id > 0`, `account.account_id == existing_account.account_id`).

Rules:
- Assert on the `ApiResponse` (`status_code`, `body`, `model(...)`); `response.raw` is an escape hatch
  to use only with a comment saying why. Never call `response.json()` in a test, and read field values
  off the typed model — never `response.body["field"]`. `response.body` is passed whole to
  `assert_shape` and echoed in `assert_status` failure messages; nothing else indexes it.
- Reuse `src/utils/assertions.py`. A repeated assertion becomes a helper — with expected-vs-actual and the
  offending payload in the message — not a copy-pasted block, and it moves **there** only once a second
  module wants it: a helper only one test module uses stays in that module, private (`_`). The
  transaction-response block is such a module-local helper, once: `_assert_transaction_created(response,
  request, expected_sign, expected_type)` in `tests/transactions/test_create_transaction.py` asserts 201 →
  shape → the request echoed as sent (`account_id`, `operation_type_id`) → ISO-8601 `event_date` → a positive
  `transaction_id` → the caller's `(sign, type)` assumption, returning the model. A test with a deliberately
  narrower expectation (`test_high_precision_amount_is_recorded`, `test_sub_unit_amount_is_recorded`) keeps
  its own assertions rather than widening itself to call it.
- `assert_shape` compares types via `_matches_type`: `bool` never counts as `int`, `float` accepts any
  JSON number. Do not re-implement that nuance in a test.
- Error payloads are read off `ErrorResponse`: the field is `error`, not `message`, and the text is
  compared with **exact equality** (`assert error.error == expected_error`) — never a substring, a
  regex or a paraphrase, because a re-worded assertion invents a contract nobody has. `assert_status`
  runs first, so a wrong status still reports the whole body.
- Assert only what the contract supports (§8), and when you must weaken an assertion keep the weakest
  invariant that is still true, with a comment naming the gap — the existing tests show the house style.
  Write the assertion the real service must satisfy even where the mock cannot produce it: a case the
  replay cannot satisfy is tagged or run where it can hold (§9), never quietly relaxed, and never a mock
  artefact (a replayed example value, an echoed id) pinned as the expected result.
- No sleeps, retries or polling to make an assertion pass; flakiness is a finding to raise, not
  something to hide. There is no contractual latency budget, so do not assert one.

Test data:
- Generated/unique data lives in `tests/data.py` (`unique_document_number()`,
  `unique_idempotency_key()`); per-scenario constants are module-level UPPER_CASE in the test file
  (`DEFAULT_AMOUNT = 100.5`). A value two endpoints' tests share goes in `tests/data.py` **once** —
  `NON_EXISTENT_ACCOUNT_ID`, used by both `test_get_unknown_account` and
  `test_unknown_account_is_rejected`: never copy the literal into each file (two homes drift) and never
  import one test module from another. No magic values inline, no `faker`, no data files.
- An expected error message is a module-level constant **next to the value that triggers it**
  (`ZERO_AMOUNT = 0.0` with `ZERO_AMOUNT_ERROR = "amount can't be zero"`) and travels with that value
  through the same `pytest.param(...)` — `test_create_account_with_invalid_document_number` carries
  `expected_status` and `expected_error` per case, `test_invalid_amount_is_rejected` an `expected_error`
  per amount. The contract documents no message text for any status, so every such constant is
  caller-supplied: assert only messages you actually know and report them as assumptions (§8) — the
  same treatment as `EXPECTED_SIGN_AND_TYPE`.
- Anything a test needs to pre-exist comes from a fixture (§4) — never a hardcoded id and never another
  test's leftovers (that breaks `-n`, §12). `tests/data.py`'s length guard (10–14 digits, default 11) is a
  **test-side** constraint, not a contract rule (§8): use the generator, never fixed document numbers.
## 8. Contract usage and required gaps handling

Read the contract in `contract/` (Swagger 2.0 — read-only, §16) before writing or changing any
assertion: 3 operations, tags `accounts` / `transactions`, `definitions.*` is the only field-level
truth, and the operation `description` prose is the only source for the operation-type list and the
amount-sign statement. `host: localhost:8080` and `basePath: /` are mock-local — environment targeting
comes from `src/config/environments.yaml`, never the contract.

Existing registers to cite (read-only, §16 — do not re-derive an audit): `docs/C3a-contract-audit.md` +
`artifacts/C3a_contract-findings.pdf` (findings register),
`docs/C3b-schema-validation-consumer-contracts-mock-fidelity.md` + its PDF, `docs/C4_test-design.md` +
its matrix. **A new finding is reported, not filed**: you name it in your summary and in the test's
explanatory comment; the register write is the caller's separate change.

Where the contract is silent — do not invent a rule:

| Contract gap (verified in the YAML / C3a) | What you must do instead |
|---|---|
| No `securityDefinitions`; no auth mechanism anywhere (C3a finding) | Never add credentials, tokens, auth headers or auth env vars — `_default_headers()` explains why |
| `amount` has no min/max/precision; the sign rule is prose only ("send a positive amount, the server applies the sign"), and the response example is `-100.5` while the request example is `50` | Never assert bounds, rounding or an unstated precision. `_assert_transaction_created` does assert the amount as sent, signed (`expected_sign * request.amount`) and the `type`, from `EXPECTED_SIGN_AND_TYPE` — a caller-supplied assumption, labelled in the code and reported as a gap, not a contract rule, and not evidence that the YAML echoes the amount or defines the sign. `test_amount_is_returned_with_expected_sign` reuses that signed expectation for a whole-number and a fractional amount, `test_high_precision_amount_is_recorded` / `test_sub_unit_amount_is_recorded` for `HIGH_PRECISION_AMOUNT` / `SUB_UNIT_AMOUNT` (the model writes every amount as a JSON number, so an integer leaves as `50.0`). `test_invalid_amount_is_rejected[zero-amount \| negative-amount]` carries the 422 for `0` and a negative amount **plus** the exact message the service answers with (`ZERO_AMOUNT_ERROR`, `NEGATIVE_AMOUNT_ERROR`). A new 422 trigger is a `pytest.param` in that test, adding a case without adding a test |
| No idempotency key, no duplicate-submission semantics | Never double-send a `POST` to prove "charged once", and never retry a POST (§6). One caller-agreed exception exists: `TestTransactionIdempotency` sends `CONCURRENT_ATTEMPTS` copies of one body in flight under one generated key (`unique_idempotency_key()`, header `IDEMPOTENCY_KEY_HEADER` — a caller-supplied assumption the client labels), because reaching the behaviour at all takes concurrent duplicates. `test_same_idempotency_key_replays_original_response`, `test_same_idempotency_key_with_different_body_is_rejected` and `test_missing_idempotency_key_is_rejected` extend it, each asserting a status and a message text the YAML never states. Assert only what is observable (every copy answered with the documented shape, one `transaction_id` across them, the amount and `type` the body sent). "Exactly one transaction exists" is **not** assertable — no operation returns a transaction count or state — so it is reported, never faked against a route the contract does not define |

| `operation_type_id` has no `enum` (1–4 exist only in prose); no definition has `required` | Don't invent an allowed-value list out of the four types, and don't assume a missing field is rejected. A real service is known to reject an unknown id with 422 `possible operation type - 1, 2, 3, 4` (`UNKNOWN_OPERATION_TYPE_ERROR`) — its own text corroborates that the prose list is exhaustive while leaving it unstated: `test_unknown_operation_type_is_rejected` asserts it with `UNKNOWN_OPERATION_TYPE_ID = 5`, one past the list |
| `account_id` on `POST /transactions` has no existence rule in the YAML (and no request field is ever `required`) | Don't invent one, and never assert a `404` for a write: a real service answers `422 account doesn't exist` (`UNKNOWN_ACCOUNT_ERROR`), which `test_unknown_account_is_rejected` asserts with `NON_EXISTENT_ACCOUNT_ID` (§7). `GET /accounts/{id}` words the same condition `account not found` — and `errorResponse.error`'s only `example` is that wording — so neither is a message the contract fixes: keep one constant per endpoint, never copy one across, and report the pair as a finding |
| `document_number: string` with no `minLength`/`maxLength`/`pattern` | Don't present or assert `tests/data.py`'s 10–14 bound as a contract rule: `test_create_account_with_invalid_document_number[empty \| below-minimum \| above-maximum \| non-digit]` carries every invalid input as data (`expected_status` and `expected_error` per case, the non-digit 422 included) and `test_create_account_with_duplicate_document_number` the 409 — none of those rules is in the YAML |
| `event_date: string` with no `format: date-time` | Our ISO-8601 + timezone check is stricter than the contract: keep it, but never claim the contract requires it |
| `type: string`, only the example `debit`, no enum or allowed-value list | Don't invent an allowed-value list the contract does not state. `TransactionType` (a `str`-valued `Enum`: `DEBIT`, `CREDIT`) holds only the expected values — the model field stays `str`, because `assert_shape` resolves annotations with `isinstance`. It is asserted per operation type from the same caller-supplied assumption, kept labelled and reported; never generalise it to another field |
| `400/404/405/422` exist without documented conditions; `errorResponse` has one non-required field, no error codes | Only assert the documented error shape where the environment really produces it — never against the Prism mock (§9). A new error test needs the trigger to be contractual first: where a real service's rule is known but absent from the YAML, write the assertion for that service, tag or select it as a real-environment case (§9) and report the gap — never leave it out, never weaken it to fit the mock. `errorResponse` documents no message text either, so a message assertion is caller-supplied by definition: assert it exactly, from a constant named after the triggering value, and only where you know it — the mock produces no error body at all (§9). Two endpoints already word one condition differently (`account not found` against `account doesn't exist`): never copy a message from the endpoint next door, and report such a pair as a finding |
| No `required`, no `additionalProperties: false`; `assert_shape` checks presence and type of all documented fields | Know that `assert_shape` is **stricter** than the contract — keep it as the suite's fidelity bar, but never call it schema validation, and don't extend it to reject unknown fields without a contract change |
| No list/pagination endpoints; no rate-limit, retry, correlation-id or observability contract; versioning only via `info.version: "1.0"` | Don't infer paging, throttling or tracing assertions; those behaviours are not observable yet |
## 9. Mock vs real environment — what the mock cannot verify

`make mock` runs `prism mock -p 8080` against the contract in `contract/`; a Prism 5.x mock accepts
this Swagger 2.0 file. The suite runs against the mock first and then a real environment (§3, §5), so
every assertion is written for the real service — but not every assertion can *hold* on the mock:

- **Stateless, replays the contract example, never echoes the request.** Round-trips (`document_number` and
  `operation_type_id` echoed back, `GET` returning what you created, amount equality) cannot be satisfied:
  every `POST /accounts` answers `{'account_id': 1, 'document_number': '12345678900'}` and every
  `POST /transactions` the example body, whatever you send. Measured on a live mock run: the
  `existing_account` fixture fails its `document_number` assertion, so every test needing pre-existing state
  **errors in setup**, and the account tests that assert the echoed document number fail (§4); a
  single-resource read answers with the example for whatever id you ask, so an unknown-id read is a real-env
  assertion — never a mock one.
- **Request validation is off by default.** Negative tests that rely on it need `prism mock --errors`, and
  their real home is the real environment; without the flag a violated schema is not an error response —
  every negative test here (`test_create_account_with_invalid_document_number`,
  `test_invalid_amount_is_rejected`, `test_unknown_operation_type_is_rejected`,
  `test_unknown_account_is_rejected`, `test_missing_idempotency_key_is_rejected`) gets 201 on the mock, and
  unmatched routes return Prism's own `problem+json` (not `errorResponse`), so error-shape assertions belong
  to a real environment too. **Duplicate submission is invisible:** two `POST /transactions` under one
  `Idempotency-Key` both answer the contract example, so a green there is a coincidence of the test data,
  not a verified dedupe.
- **`mock_compatible` is the only mock-side subset**: declared in `pytest.ini`, applied per `pytest.param`
  (`test_create_transaction_for_operation_type[normal-purchase]`,
  `test_amount_is_returned_with_expected_sign[decimal]` — the two that send the example's own operation type
  and amount) and selected with `-m mock_compatible`. Adding the mark claims the replay satisfies the case;
  it never parks a failing one — a case the mock cannot satisfy stays unmarked and is verified where it can
  hold, with the gap reported (§8).
- **So:** an unknown-resource read, a write against real state, 4xx body shapes and idempotency are
  real-environment assertions — write them for the contract's behaviour and select that environment
  (`--env` / `PISMO_ENV`, §5) rather than deleting or weakening them. What the mock is worth is the first
  gate on happy-path status codes, response shape/type, contract-example conformance and the
  client/HTTP/configuration plumbing; never "fix" a mock-specific failure by weakening an assertion a real
  environment would satisfy — report it (§8) and name it in the test's comment.
## 10. Recipes

**A. Add a test for an existing endpoint** (one file per endpoint; file names must be unique across
`tests/**` — there is no `__init__.py`, so pytest imports by basename):

1. `tests/<service>/test_<endpoint>.py`, or a new test in the existing file, with the house module
   docstring `` ``<METHOD> /<path>`` — contract tag: ``<service>``. ``, a module-level
   `pytestmark = pytest.mark.<service>` and the subset markers the existing tests carry (`smoke`,
   `nightly`, `negative`, `pre_release`…; `mock_compatible` only where §9 allows it).
2. Request the fixtures you need as annotated parameters; never build the plumbing.
3. One-line docstring stating the guarantee; module-level constant for a scenario value.
4. Exactly one client call, then assert in the §7 order. Register any new marker in `pytest.ini`
   (`--strict-markers` fails the run otherwise) and finish with `make test` (§13).

Canonical examples to mirror: `tests/accounts/test_create_account.py` (module docstring, import order,
`pytestmark`, class, assertions in the §7 order) and `tests/transactions/test_create_transaction.py`
(one `pytest.param` per operation type over one shared body carrying the module-local
`_assert_transaction_created` helper, with `mock_compatible` on the parameters the replay satisfies).
`test_create_account` also asserts the returned `document_number` is the one sent — a round-trip the
mock cannot satisfy (§9).

**B. Add an operation to a service** (client + model + test):
1. Contract first: if the operation or response is not in `contract/…yaml` this is a §8 gap — report
   it; never implement a guessed contract or patch the YAML (§16).
2. `src/models/<service>.py`: the frozen request/response dataclasses with `to_payload()` /
   `from_payload()`, then the derived `*_RESPONSE_FIELDS`. Contract fields only.
3. `src/clients/<service>_client.py`: a path constant if the route is new, then the method
   (`HTTPMethod` + `self._send`) returning the untouched `ApiResponse`.
4. `tests/<service>/`: the test per recipe A; add a fixture in `tests/conftest.py` only if the scenario needs
   **pre-existing** state, and register any new marker in `pytest.ini`. If you changed a fixture, the client
   or the HTTP layer, run the parallel mode too (§12) and report the boundary change in your summary
   (`docs/C4_automation-architecture.md` is read-only, §16).

**C. New service** (e.g. `cards`): `src/models/cards.py` + `src/clients/cards_client.py` + a
session-scoped `cards_client` fixture beside the others + `tests/cards/` + a `cards:` marker in
`pytest.ini` + a row in the README layout; the C4 rows are a reported change (§16). Nothing else in the
framework needs to change — that is the point of the boundary.
## 11. Reporting — do not break it

- `pytest.ini`'s `addopts` owns both artefacts, so **every** run writes them (make target, IDE runner,
  CI, bare `pytest`): `reports/junit.xml` (`--junit-xml`) and `reports/report.html` (`--html
  --self-contained-html`, pytest-html with the pytest-metadata environment table). Keep those flags in
  `addopts`; don't repeat them in recipes or README commands, and don't remove them.
- Stable CI contract: `junit_suite_name = pismo`, `junit_family = xunit2`, one `<testcase>` per test with
  its duration, each failure's message verbatim. A CI job can re-point the files without editing the repo:
  `python -m pytest --junit-xml=/tmp/junit.xml --html=/tmp/report.html --self-contained-html` (an explicit
  CLI flag beats `addopts`); under `-n` both plugins write once from the controller — one merged XML and one
  HTML with every test, so no per-worker report flags.
- `reports/` is gitignored output: never commit it, never quote results from a stale file — re-run,
  then read the header line and the counts. The environment is printed on stdout, not stamped into the
  artefacts, so a job running several environments gives each its own `--junit-xml`/`--html` path
  (known limitation, recorded in `docs/C4_automation-architecture.md`).
## 12. Parallel execution — opt-in, both modes must stay correct

- The default stays single-process: `-n` is deliberately **not** in `addopts`, so a normal run's order and
  API-call count are predictable. Turn it on per run: `make test-parallel WORKERS=N` (its guard prints an
  actionable message when `pytest-xdist` is missing), `python -m pytest -n4`, or `PYTEST_ADDOPTS="-n auto"
  python -m pytest` — `PYTEST_ADDOPTS` is applied after `addopts`, so CI can enable parallelism without
  editing the repo.
- A test must be distributable: no dependency on another test's state or execution order, `parametrize`
  inputs ordered (never a `set`), and never an assumption that a session fixture ran exactly once —
  `-n4` repeats each setup `POST` up to four times, a real increase in API calls against a shared
  environment; flag that in your summary when you add such a fixture.
- Under xdist, `-s`/`--pdb` are unavailable, `record_testsuite_property` is unsupported and pytest-html's
  `original` sort order is unreliable (the columns remain sortable). Against a stateful or money-moving
  environment, pin retries off (`--max-worker-restart=0`) so a crashed worker never re-executes a test that
  already changed state — and never retry a `POST`.
- Verify a parallel run like any other: same two report files, same test count, header line printed
  once. With a suite this small the win comes from network wait, not CPU — measure before claiming a
  speed-up.
## 13. Definition of done — run these before you report

```bash
make test                            # header line + "<N> passed" (N = collected count)
python -m pytest --env staging --base-url https://…   # same suite against a real environment
python -m pytest -m accounts -q      # if you added tests/markers: prove the selection works
make test-parallel WORKERS=2         # if you touched fixtures, clients, conftest or HttpClient
```

Boundary checks (copy-paste; each line's expected result is in its comment):

```bash
grep -rnE '^import requests' tests/ src/models/ src/config/ src/clients/  # only base_client.py
grep -rnE '^import pytest|^from pytest' src/ --include='*.py'             # nothing
grep -rnE 'os\.environ|getenv' src/ tests/ --include='*.py'               # only src/config/settings.py
grep -rnE 'from tests|import tests' src/ --include='*.py'                 # nothing
grep -rnE '^from src\.' src/models/ src/config/ --include='*.py'          # nothing (leaves)
grep -rnE '^[[:space:]]*assert ' src/ --include='*.py' | grep -v src/utils/assertions.py   # nothing
```

Then confirm, explicitly:

- [ ] every marker used is declared under `markers =` in `pytest.ini`, and a new test file's basename is unique across `tests/**`;
- [ ] a new dependency is pinned in `requirements.txt` and `make install` was run;
- [ ] `reports/junit.xml` has `<testsuite name="pismo" … tests="N">` with N equal to what you ran, and any failure message is verbatim in the XML;
- [ ] `git status --short` shows only intended files — `reports/`, `.venv/`, `__pycache__/`, `.pytest_cache/` stay ignored — and `git status --short -- contract docs artifacts` prints nothing (no YAML patch, register entry or refreshed PDF);
- [ ] no assertion was weakened without a comment naming the contract gap, and no sleep/retry was introduced;
- [ ] a boundary, fixture kind, client or cross-cutting change updated `README.md` where commands/layout changed, and a new contract gap is named in your summary and in the test's comment, not filed (§16);
- [ ] your summary states the exact commands run, how many tests passed, which environment each used (the mock, or a real one), and any side effects (extra `POST`s under `-n`).
## 14. Conventions a diff must follow

- **Imports and docstrings:** plain `import x` lines first, blank line, then `from x import y` — no
  isort/ruff config exists, so match the file you are editing and never reorder or reformat a file you
  merely visited. Every module opens with a docstring that orients the reader, public classes, functions and
  methods are documented, and a test method gets **one line stating the guarantee it pins**; docstrings in
  `src/config`/`src/utils` also carry the *why* (see `_default_headers`). Update the docstring in the same
  commit as the behaviour change.
- **Typing:** annotate every parameter and return (`-> None` on tests), `Any`/`Mapping` from `typing`,
  unions with `|`, frozen dataclasses for wire shapes, `IntEnum` for identifier enums, a `str`-valued `Enum`
  for a value set used only as an expected value (`TransactionType`) — never as the wire-shape annotation.
- **Naming and markers:** one folder per service; `test_<verb>_<resource>.py`; `Test<Operation>`;
  `test_<behaviour>`; `<Resource>Client` with `<verb>_<resource>()` methods; `<Resource>{Request,Response}`
  models; module constants UPPER_CASE; private helpers `_`. Tag the file with a module-level `pytestmark`
  for its service, carry the subset markers the existing tests carry (`smoke`, `nightly`, `negative`,
  `pre_release`…), use `mock_compatible` only where the replay satisfies the case (§9), and register every
  marker in `pytest.ini`.
- **Comments:** explain *why*, never restate the code; the contract-gap comments already in the tests are
  part of the deliverable — keep them, and add yours where you weaken or narrow an assertion.
- **Formatting:** no linter, formatter or type checker is configured (no pyproject, ruff, flake8, tox,
  pre-commit or CI workflow here), so the neighbour file is the style contract: wrap around 88–100 and check
  before you finish — `git ls-files '*.py' | xargs awk 'length>100'` must print nothing (add any file you
  have not committed yet, which `git ls-files` cannot see). Propose tooling in your summary; never smuggle a
  global reformat into a behavioural change.
- **Structure and dependencies:** empty `__init__.py` (packages are plain), one file per endpoint,
  `tests/data.py` for generated data, the diff in the layer that owns the change, and exact pins in
  `requirements.txt` only when stdlib or `requests` does not already do the job.
- **No stray output:** the `pismo:` header is the only sanctioned stdout; no `print` in `src/` or tests, no
  logging framework — failures must be visible through assertions.
## 15. Gotchas seen in this repository

1. `--strict-markers` fails **collection** for an unregistered or misspelled marker: seen here with
   `@pytest.mark.prerelease` in `tests/accounts/test_get_account.py` against the declared `pre_release` —
   pytest interrupts with `'prerelease' not found in markers configuration option` and the whole module
   collects nothing. Fix the spelling; never drop `--strict-markers`.
2. `.venv` is gitignored and may be gone ("No virtualenv at … - run 'make install' first", typically after
   `make clean`, which now also deletes `reports/` — re-run before quoting a count). Run `make install`;
   never fall back to a system python, and keep the python3.12 baseline (`PYTHON ?= python3.12`; the code
   uses `X | None` unions, and the 3.9 interpreter here cannot even import `src/config`).
3. `make test-parallel VENV=/abs/path` cannot work — the Makefile resolves `$(CURDIR)/$(VENV)`: pass a
   relative `VENV=` or use a separate clone.
4. `listen EADDRINUSE` from `prism mock` means a mock is already listening (fine) — confirm with the `curl`
   probe in §3 instead of concluding the mock is broken; `--strict-config` turns a mistyped `pytest.ini` key
   into a failure of **every** run (intentional: fix the key, don't drop the flag).
5. `<N> skipped` / `skipped="N"` with a reason means the selected environment has no base URL (`--env
   staging` reproduces it): read the header line before debugging a "broken" suite — there is no `xfail`
   bucket to confuse it with any more (§9).
6. **Known drift:** the Makefile's `WORKERS ?= auto` and the README agree, but the C4 table still says `4`
   (`docs/` is read-only, §16) — pass `WORKERS=` explicitly instead of quoting a default.
## 16. Deliberate framework gaps — do not "fix" them silently

Known decisions and deferred work. If a task touches one, say so explicitly, get it agreed and land it
as its own scoped change — never as a side effect of an unrelated diff; its documentation impact is
reported, not written by you (§1).

- **`contract/`, `docs/` and `artifacts/` are read-only**: they are inputs — the contract is the field-level
  truth, the registers and PDFs are the citations — never outputs of your change, and **authentication is
  unimplemented by design** and not to be guessed (§5, §8). No YAML patch to make a test pass, no finding
  filed by you, no regenerated PDF: a change you believe is needed there goes in your summary as a proposal.
- **Error-shape, negative and stateful flows**: verified on a real environment, not against the mock
  (§9) — do not fake them with a mock-side assertion.
- **Per-test environment gating**: there is none, and no `xfail` parking either. The same tests run
  against the mock and then a real environment; the only gate is run-level (no `base_url` ⇒ the whole run
  skips, §5). A case only a real service satisfies therefore fails on the mock by design and is tagged or
  selected rather than weakened (§9) — adding one is a scoped change to agree first.
- **CI and tooling**: the PR/nightly/pre-release gates in `docs/C4_test-design.md` are prose only and this
  repository has no CI configuration, so never claim a gate ran; reports use one fixed pair of artefact
  paths (§11), no lint/format/type gate exists (§14) and the `WORKERS` drift (§15) is doc debt — none of
  these is a bug to "fix" in passing; each is its own change, with its impact reported.

For depth, read in this order: `docs/C4_automation-architecture.md` (this framework's own description) →
`docs/C3a-contract-audit.md` + `artifacts/C3a_contract-findings.pdf` → `docs/C4_test-design.md` + its matrix →
`docs/C3b-…md` → `README.md` → the contract in `contract/`. Reading is always allowed; writing is not
(§1, §16). This skill is instructions, not a replacement for reading the file you are about to change.
