# C3a — Contract Audit Register

## Scope

I went through the API contract `contract/transactions-service.v1.yaml` which exposes three REST APIs:

- `POST /accounts`
- `GET /accounts/{accountId}`
- `POST /transactions`

I focused on gaps that affect money safety, testability, compatibility, and observability. I have not treated the backend engineer's verbal statements as contractual unless the YAML actually supports them.

## Finding classification

**Class:**
- **Money Safety** - It can affect the correctness of financial state.
- **Validation** - Weak request/response constraints.
- **Contract Ambiguity** - Behaviour is described, but contract does not define a testable outcome.
- **Observability** - API does not expose enough information for verification.
- **Security** - Security related contract requirement is absent or unclear.

**Severity**:
- **P0** — must be resolved before I would sign off a money-moving release.
- **P1** — significant contract/functional risk, release-blocking when exercised by a consumer or critical flow.
- **P2** — important quality issue, but not a reason to stop a money-moving release.

---

## Findings register location: `artifacts/C3a_contract-findings.pdf`
