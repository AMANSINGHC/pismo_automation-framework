# AI Notes

## 1. What I Used AI For

I used AI as an assistant during the development of this test automation framework. I used it for planning, scaffolding, implementation, test generation, refactoring, documentation, and creating reusable Cline agent instructions.

### 1.1 Project scaffolding

I used AI to create the initial project skeleton:

* `contract/`
* `docs/`
* `src/clients/`
* `src/config/`
* `src/models/`
* `src/utils/`
* `SUBMISSION.md`
* `AI_NOTES.md`
* `requirements.txt`
* `pytest.ini`

I manually copied the actual `transactions-service.v1.yaml` contract into the repository and pinned the `pytest` and `requests` dependency versions.

### 1.2 Architecture planning

AI was used to help plan the initial automation architecture:

```text
Test
  ↓
Service Client
  ↓
HTTP Layer
```

The framework was designed so the Base URL can be switched between the Prism mock and a future staging/test environment without rewriting the tests.

I subsequently refined the architecture based on the needs of the assessment. Examples include:

* Moving the HTTP client into reusable utility/infrastructure code.
* Keeping assertions in tests rather than the HTTP/client layer.
* Using one generic HTTP `request()` method instead of separate `get()`/`post()` methods.
* Using HTTP-library enums instead of raw HTTP method/status strings.
* Keeping transport utilities together.
* Keeping test-specific data under `tests/`.
* Avoiding unnecessary abstractions where the current scope did not justify them.

### 1.3 Configuration and environment planning

AI helped with configuration planning.

I chose to:

* Keep configuration in YAML.
* Merge `environments.py` and `settings.py` into the current `settings.py` implementation.
* Defer the proposed `EnvironmentProfile` abstraction because it added complexity that was not currently required.

I also deliberately did not implement `PISMO_AUTH_TOKEN` because the authentication mechanism was not confirmed in the contract.

This avoided turning an assumption into framework behavior.

### 1.4 Test generation

I used the repository-specific Cline agent:

```text
.cline/agents/api-test-generator.md
```

to generate and refine tests for:

* Empty `document_number`
* Document-number length boundaries
* Invalid document characters
* Duplicate `document_number`
* Unknown account
* Transaction operation types
* Amount round-trip behavior
* Zero and negative amounts
* Unknown operation type
* Non-existent account
* Idempotency concurrency
* E2E account/transaction journey

AI was generally given the specific scenario and expected behavior rather than being asked to invent business rules.

### 1.5 Test refactoring and parametrization

AI was also used to consolidate tests where the scenarios exercised the same behavior.

Examples:

* Parametrizing document-number validation tests.
* Combining invalid document-number scenarios.
* Parametrizing transaction operation types.
* Parametrizing amount round-trip cases.
* Parametrizing invalid transaction scenarios.

The intent was to reduce duplicated test structure while keeping individual scenarios explicit.

### 1.6 Framework refactoring

AI was used to help refine the framework implementation, including:

* Removing unnecessary context-manager methods.
* Removing the `expect` parameter from the HTTP layer.
* Moving reusable transport utilities.
* Deriving response fields from dataclasses instead of maintaining duplicated field lists.
* Centralizing pytest configuration in the root `conftest.py`.
* Adding JUnit XML and HTML reporting.
* Keeping generated reports out of source control.
* Adding generic concurrency utilities.

### 1.7 Cline skill creation

I used AI to inspect the framework and create:

```text
.cline/skills/api-automation/SKILL.md
```

The skill captures the framework's:

* Architecture
* Directory responsibilities
* Test execution flow
* Fixture/dependency injection approach
* Configuration handling
* Request/response modeling
* Assertion strategy
* Test-data strategy
* Reporting
* Parallel execution
* Contract usage
* Testing patterns
* Coding conventions

The prompt explicitly instructed the AI not to invent missing rules and to identify contract gaps instead.

The generated skill was reviewed against the framework rather than being treated as authoritative simply because AI generated it.

---

## 2. One Place Where AI Was Wrong

### Incorrect transaction operation assertion

One concrete example occurred while generating transaction tests.

AI generated an assertion equivalent to:

```python
assert transaction.operation_type_id in OPERATION_TYPES
```

This assertion was syntactically valid but logically too weak.

The purpose of the parameterized test was to verify that the operation type returned by the service matched the operation type requested.

For example:

```text
Requested operation: INSTALLMENT_PURCHASE
Returned operation:  WITHDRAWAL
```

With the AI-generated assertion:

```python
assert transaction.operation_type_id in OPERATION_TYPES
```

the test could still pass because `WITHDRAWAL` is itself a valid operation type.

That means the test could pass while the service returned the wrong operation.

I caught this during review of the generated assertion against the intended test oracle.

I changed the assertion to verify the exact requested operation.

I reviewed whether the assertion would actually fail for the defect the test was intended to detect.

---

## 3. One Decision I Made Against AI's Suggestion

### Authentication was deliberately not implemented

The framework contained a potential `PISMO_AUTH_TOKEN` concept, but the authentication mechanism had not been confirmed.

I deliberately decided:

```text
Do not implement PISMO_AUTH_TOKEN.
```

I did not want to introduce authentication behavior based on an assumption that was not established by the available contract or requirements.

This was a deliberate choice to leave an under-specified area unresolved rather than inventing behavior.

The same principle was applied throughout the framework:

```text
Contract
   ↓
What is explicitly defined?
   ↓
Hearsay / domain reasoning / assumption
   ↓
Clearly identify the source
```

---

## 4. Additional Example of Human Judgment

For transaction amount and type assertions, I explicitly instructed AI to use the following expected behavior:

* Operations 1, 2 and 3 produce negative amounts and `debit`.
* Operation 4 produces a positive amount and `credit`.

I subsequently strengthened the amount assertion to match the **exact expected amount including its sign**, based on the request.

These behaviors must not automatically be described as OpenAPI guarantees unless the contract explicitly defines them.

The source of the expected behavior therefore matters:

```text
CONTRACT
HEARSAY
DOMAIN REASONING
ASSUMPTION
```

This prevents an AI-generated assertion from silently becoming the specification.

---

## 5. AI Guardrails I Applied

I used several guardrails when working with AI:

### Contract is the source of contractual behavior

AI was instructed to refer to:

```text
contract/transactions-service.v1.yaml
```

and not invent missing requirements.

### Assertions require review

For every generated assertion, I considered:

1. What behavior is being asserted?
2. Why should that behavior be true?
3. What is the oracle?
4. What source establishes the expected behavior?
5. Would the assertion fail for the defect the test is intended to catch?

### Avoid invented business behavior

Where the contract does not define behavior, I do not silently convert an assumption into a contractual assertion.

### Preserve architecture

AI-generated changes were constrained by the framework architecture:

```text
Tests
  ↓
Service Client
  ↓
HTTP / Transport
```

Assertions remain in tests, while transport/client layers are responsible for request execution and response handling.

### Avoid unnecessary abstraction

I deliberately removed or deferred abstractions that were not justified by the current scope, including:

* `EnvironmentProfile`
* `_wire.py`
* HTTP context-manager methods
* Dedicated HTTP `get()`/`post()` wrappers
* Separate idempotency test class

### Human review of generated code

Generated code was reviewed against:

* The OpenAPI contract
* Existing framework conventions
* Intended test oracle
* Test isolation requirements
* Assertion strength
* Maintainability

---

## 6. AI and the Idempotency Test

AI was used to help plan the PISMO-4412 concurrency test.

The important design decision was that response equality is **not** the state oracle.

The intended flow is:

```text
N concurrent POST /transactions
          ↓
same idempotency key
same request body
          ↓
query transaction state/count
          ↓
assert count == 1
```

The test also collects response/request IDs and transaction IDs for diagnostics.

This distinction was deliberate because identical responses alone do not prove that exactly one transaction was persisted.

---

## 7. AI and the E2E Journey

AI was used to generate the API-level E2E journey:

```text
Create account
      ↓
Create transaction: operation 1
      ↓
Create transaction: operation 2
      ↓
Create transaction: operation 3
      ↓
Create transaction: operation 4
      ↓
Verify transaction responses
      ↓
Verify account association
```

The journey was explicitly scoped rather than allowing AI to invent additional UI or business workflows.