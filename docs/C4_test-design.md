# C4 - Test Design & Executable Suite

Test Case Matrix: `artifacts/C4_test-design_tracebality-matrix.pdf`

Amount Edge Case Matrix: `artifacts/C4_test-design_tracebality-matrix.pdf`

Traceability Matrix: `artifacts/C4_test-design_tracebality-matrix.pdf`

**CI Gates with Scope:**
- **PR** - Contract validation; Contract tests; Critical account, transaction and HTTP tests.
- **Nightly** - Full boundaries, money probe, idempotency scenarios, very large inputs and additional negative scenarios.
- **Prerelease** - Full critical suite, idempotency scenarios, transaction state and audit integration checks.
