# SUBMISSION — Transactions Service QA Case Study

**Candidate:** Aman Chauhan  
**Total active time spent:** ~12 hours 15 minutes  
**Stack chosen:** Python, Pytest, Requests, Prism, Make. Chosen to keep the implementation fast, deterministic, maintainable, and aligned with my strongest automation experience.

---

## 0. Read this first

**What I Built** - API automation framework for Transactions Service using Python/Pytest, with a Prism mock as the default environment and a configuration to support staging environment. The submission includes a risk-based test strategy, contract audit, executable contract tests, functional/API coverage, traceability, an incident analysis for PISMO-4412, a E2E user journey, defect predictions, and AI-assisted engineering notes.
**What I Found** - The most important findings are that idempotency is described in hearsay but not in the contract, the published APIs does not expose enough state to prove the required exactly-one transaction behavior under concurrency, and audit creation/atomicity is not externally verifiable. 
**What I Fix** - Before real-money use, I would require the idempotency contract and transaction-state oracle to be defined and verified, together with a guarantee for atomic business/audit writes.

---

## 1. Index

| # | Deliverable | Where | How to run | Time spent |
|---|---|---|---|---:|
| C1 | Test strategy, risk & metrics | `artifacts/C1_test-strategy-risk-metrics.pdf` | — | 1h 30m |
| C2 | Framework & CI design | `artifacts/C2_CI-design_flake-and-env-strategy.pdf` | `make test`, `make test-smoke`, `make test-parallel` | 1h 15min |
| C3a | Contract audit register | `artifacts/C3a_contract-findings.pdf` | — | 2h |
| C3b | Contract tests + consumer contracts + mock fidelity | `artifacts/C3b_validation-layer.pdf`, `tests/contract/` | `make test-contract` / `python -m pytest -m contract -v` | 1h 15m |
| C4 | Test design + executable suite + traceability matrix | `artifacts/C4_test-design_tracebality-matrix.pdf`, `tests/accounts/`, `tests/transactions/`, `tests/contract/` | `make test`, `make test-smoke` | 3h |
| C5 | Defect register & predictions | `artifacts/C5_contract-defects-register.pdf`, `artifacts/C5_predicted-implementation-defects.pdf` | — | 30m |
| T1 | PISMO-4412 incident write-up + guardrail | `artifacts/T1_PISMO-4412.pdf`, `tests/transactions/test_create_transaction.py` | `python -m pytest tests/transactions/test_create_transaction.py -v` | 1h 30m |
| T3 | API E2E journey | `tests/e2e/` | `python -m pytest tests/e2e -v` | 15m |
| T4 | AI-assisted test generation & guardrails | `AI_NOTES.md`, `.cline/agents/api-test-generator.md`, `.cline/skills/api-automation/SKILL.md` | — | 45m |
| — | AI notes | `AI_NOTES.md` | — | 15m |

### Prerequisites / setup

Assuming a clean machine with Python 3.12.x installed:

```bash
make install
make mock
```

Leave Prism running, then in another shell:

```bash
make test-smoke
```

For the full suite:

```bash
make test
```

Contract-focused tests:

```bash
make test-contract
```

Parallel execution is opt-in:

```bash
make test-parallel
```

---

## 2. What my green build does and does not prove

### Contract assertions

The tests under `tests/contract/` assert facts supported by the supplied OpenAPI contract:

- documented success status codes
- documented error status codes that Prism can exercise
- documented response field names
- documented JSON field types
- documented error response shape

### Mock/example validation

A Prism mock is generated from the same OpenAPI contract being tested. Therefore, a green result against Prism demonstrates that the:

- test harness can construct and send the request
- selected Prism behavior can be exercised
- tests with mock_compatible tag pass against the mock

### Tests designed to survive against staging

All tests under `tests/contract`, `tests/accounts`, `tests/transactions`, and `tests/e2e` are designed to run against staging, with assertions based on the contract, hearsay, domain reasoning, and assumptions documented in `artifacts/C4_test-design_tracebality-matrix.pdf`. Tests tagged `contract` and `mock_compatible` can run against the Prism mock.

---

## 3. What I deliberately did not do, and why

| Skipped / limited | Why | What I'd do with another day |
|---|---|---|
| OpenAPI/JSON-Schema validator | The assessment can be satisfied with contract tests, and a large custom validator would add framework complexity without improving the core risk story enough for the available time. | Add a small OpenAPI-driven validator using the YAML as the schema source, including request/response validation and documented response selection. |
| Performance measurements | Prism measures mock/harness behavior rather than real service performance. | Built a performance framework harness that can used for load testing in a real environment. |
| Full cross-cutting malformed-body/content-type/oversized-body suite against Prism | Due to lack of time. | Add these tests with AI-assisted test generation. |

---

## 4. Top findings

I use the following classification:

- **Money Safety** — can directly affect financial correctness.
- **Observability** — prevents proving or reconciling an important invariant.
- **Validation** — request/response constraints are incomplete.
- **Contract Ambiguity** — behavior is described or implied but not deterministically specified.
- **Security** — authentication/authorization requirements are absent or unclear.

Severity:

- **P0** — must be resolved before sign-off of a money-moving release.
- **P1** — significant contract/functional risk; release-blocking when exercised by a critical flow.
- **P2** — important quality issue but not by itself a reason to stop a money-moving release.

| # | Finding | Class | Severity | Business impact |
|---|---|---|---|---|
| 1 | Idempotency header and replay semantics are absent from the contract, while idempotency is relied upon to prevent double-debits. | Money Safety / Contract Ambiguity | P0 | Retry storms can create duplicate financial operations, and consumers have no contractual definition of key presence, format, replay, or key reuse. |
| 2 | The API does not expose an authoritative transaction-state/count oracle needed to prove exactly one transaction under concurrent same-key requests. | Money Safety / Observability | P0 | A response-level replay test cannot distinguish one durable transaction from multiple durable writes that happen to return similar responses. |
| 3 | Audit creation and business/audit write atomicity are hearsay and are not represented or verifiable through the published API. | Money Safety / Observability | P0 | A missing/divergent audit record can make financial activity difficult or impossible to reconcile. |
| 4 | Operation-specific sign/type mapping is not fully contractual. | Money Safety / Contract Ambiguity | P0 | A wrong debit/credit direction can move financial state in the wrong direction. |
| 5 | Amount precision/range/currency/unit constraints are incomplete or absent from the contract. | Money Safety / Validation | P0 | Different consumers can interpret or send monetary values differently, creating rounding, precision, or unit errors. |
| 6 | Required request properties and several validation rules are not explicitly declared. | Validation | P1 | Consumers cannot reliably determine which requests are valid before making money-moving calls. |
| 7 | Response properties are not marked required, weakening the provider guarantee for fields needed for reconciliation. | Validation | P1 | A syntactically successful response could omit fields consumers need to process or reconcile the transaction. |
| 8 | Authentication/authorization requirements are not defined in the supplied contract. | Security | P0 | Consumers cannot determine who is permitted to create accounts or move money, and QA cannot build a contractual access-control gate. |

---

## 5. What I'd require fixed before this service is trusted with real money

1. **Define and prove idempotency end-to-end.** The contract should specify the header name, key format, same-key/same-body replay behavior, same-key/different-body behavior, and missing-key behavior. The provider must provide a way to verify that exactly one transaction was persisted.

2. **Make financial semantics contractual and testable.** Explicitly define currency/unit, amount precision and limits, zero/negative behavior, and the complete operation-type → transaction type/sign mapping for every operation ID.

3. **Make auditability verifiable.** Define the audit guarantee and provide a test-environment oracle for audit records, including a way to prove that the business write and audit write are atomic.

4. **Close the API schema gaps.** Define required request/response properties and deterministic validation/error behavior for invalid inputs.

5. **Define security requirements.** Authentication and authorization must be explicit and covered by provider/consumer tests before release.

---

## 6. Open questions for the dev / PO

Refer `artifacts/C1_test-strategy-risk-metrics.pdf` Section 4.

---
