# C4 — Automation framework

Test automation framework for backend services, layered so a test only states intent.

## Layers

| Layer | Location | Responsibility |
|---|---|---|
| Tests | `tests/` | One folder per service (`tests/accounts/`, `tests/transactions/`), one file per API endpoint, grouped in a class that carries the service's tag. Asserts only: status, documented fields, field types; unique payload data comes from `tests/data.py`.|
| Service clients | `src/clients/` | One method per operation (`AccountsClient`, `TransactionsClient`): build the payload, send it, expose the status/body as an `ApiResponse` and parse it into a typed model. Knows nothing about sessions or URLs. |
| HTTP layer | `src/utils/transport/http_client.py` | One `requests.Session` per run: base URL, headers, timeout. Domain-free, so it can be promoted into a shared test-infrastructure package later. |
| Response envelope | `src/utils/transport/api_response.py` | `ApiResponse`: the frozen record of what came back (method, URL, status, headers, body, elapsed time, raw `requests.Response`). Transport-agnostic, so both the service clients and the assertions depend on it without depending on each other. |
| Configuration | `src/config/settings.py` + `src/config/environments.yaml` | Resolves the Base URL, the timeout and the default headers for the run. |
| Models | `src/models/` | Typed request/response shapes lifted from the contract. The `*_RESPONSE_FIELDS` specs the assertions check are derived from the dataclasses themselves, so field names and expected JSON types have one source of truth. |

Dependencies point one way only: `tests → src/clients → src/utils → src/config`,
plus `src/clients → src/models` for the typed shapes; `src/models` and
`src/config` are leaves that import nothing from the other `src` packages. No
module below `tests/` imports a test, and nothing outside `src/config` reads the
environment.

## Switching the Base URL

`src/config/environments.yaml` is the source of truth; environment variables are
overrides, so a run can be re-pointed without touching code or YAML.

| Priority | Source | Example |
|---|---|---|
| 1 | Explicit argument | `load_settings(base_url=...)` |
| 2 | pytest CLI | `--env staging --base-url https://staging.example` |
| 3 | Environment variable | `PISMO_ENV`, `PISMO_BASE_URL`, `PISMO_TIMEOUT_S` |
| 4 | `environments.yaml` | `environments.prism.base_url`, `defaults.timeout_s` |

Each run prints its target in the report header, and records it in both report
artifacts (see Reports):

```
pismo: environment=prism base_url=http://localhost:8080 timeout=10.0s config=.../environments.yaml
```

An environment whose `base_url` is empty (as `staging` ships) makes the run skip
with the exact place to set it, rather than failing with a connection error.

## Reports

Every run writes two artifacts under `reports/`, defaulted in the root
`conftest.py` so that a plain `pytest`, an IDE run and `make test` all produce
them without a flag to remember:

| Artifact | Read by |
|---|---|
| `reports/junit.xml` | CI: one `<testcase>` per test with its duration, and each failure's message verbatim |
| `reports/report.html` | a human: a single self-contained page (no sibling asset files) holding the results table and an environment table |

Two of those details are deliberate rather than incidental:

- **Only options a run leaves unset are defaulted**, so `--junitxml`/`--html` still
  win and a CI job can write to its own results directory. The directory itself is
  created by the hook, because a fresh clone has no `reports/` and a missing
  directory must not be able to fail a run.
- **Both artifacts state their environment.** The JUnit XML carries it as a `pismo`
  `<property>` (through pytest's `record_testsuite_property`), the HTML in its
  environment table (the stash route pytest-html documents for pytest-metadata). A
  run whose environment has no base URL never reaches a request, and records that
  reason too, so a CI job holding only the XML learns why nothing ran.

Failure messages are the payload of a report, which is why the assertion helpers
build them with the request, both statuses and the response body in them. A body
therefore reaches a report only as part of a message a test author wrote; nothing
logs or captures traffic behind the tests' back.

## HTTP layer decisions

- **No automatic retries.** A transient failure surfaces as the `requests` exception
  that caused it (`ConnectionError`, `Timeout`, ...) instead of being retried behind
  the test's back. Retrying `POST /transactions` would be unsafe anyway, a retry can 
  move money twice. If retries are ever added, they must be limited to safe methods.
- **Timeouts are always explicit** (`defaults.timeout_s`), so a hung environment
  fails fast.
- **Redirects are not followed**: a 3xx is a signal to assert on, not something to
  paper over.

## Prism mock notes

`prism mock -p 8080 contract/transactions-service.v1.yaml` (see `make mock`).

- Prism 5.14.2 accepts this Swagger 2.0 file and serves the contract examples:
  `POST /accounts` → 201, `GET /accounts/1` → 200, `POST /transactions` → 201.
- It is **stateless** and replays the contract example, so it never echoes the
  request body. Smoke tests therefore assert shape and types, not values.
- Request validation errors are only returned when Prism is started with
  `--errors` (off by default). Negative tests that rely on validation must use it.
- Unmatched routes return Prism's own `problem+json` body, not the contract's
  `errorResponse`, so error-shape assertions must not run against the mock.

## Scope and next steps

Covered now: one smoke test per endpoint, green against the contract mock, the
configuration/HTTP/client plumbing they run through, and the JUnit XML + HTML
report every run leaves behind.

Next, driven by the C3a findings register: boundary and negative tests for
`document_number`, `amount` and `operation_type_id`; error-shape tests for the
4xx responses; idempotency and audit assertions once those behaviours become
contractual; and a stateful environment to cover flows the stateless mock cannot
(for example `GET` of a non-existent account, or a transaction on a real account).
That will also reintroduce per-environment capabilities (stateful vs stateless,
auth enforced or not) as simple `environments.yaml` keys. Authentication itself
stays unimplemented until the mechanism is confirmed — no credential plumbing,
environment variable or header is in place to guess at.
