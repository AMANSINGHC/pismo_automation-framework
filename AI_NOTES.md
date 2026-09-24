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

I used AI to help plan the initial automation architecture by providing it basic context:

* Test --> Service Client --> HTTP Layer --> Actual Service
* framework needs to be supported on mock + test environment without making changes to the tests.

I subsequently refined the architecture based on the needs of the assessment. Examples include:

* Moving the HTTP client into reusable utility/infrastructure code.
* Keeping assertions in tests rather than the HTTP/client layer.
* Using one generic HTTP `request()` method instead of separate `get()`/`post()` methods.
* Using HTTP-library enums instead of raw HTTP method/status strings.
* Keeping transport utilities together.
* Keeping test-specific data under `tests/`.
* Avoiding unnecessary abstractions where the current scope did not justify them.
* Designing the contract integration so the framework is not permanently coupled to a single contract file.

### 1.3 Configuration and environment planning

AI helped with configuration planning.

I chose to:

* Keep configuration in YAML.
* Merge `environments.py` and `settings.py` into the current `settings.py` implementation.
* Defer the proposed `EnvironmentProfile` abstraction because it added complexity that was not currently required.

I also deliberately did not implement `PISMO_AUTH_TOKEN` because the authentication mechanism was not confirmed in the contract.

### 1.4 Test generation

I used the repository-specific Cline agent: `.cline/agents/api-test-generator.md` to generate and refine tests for:

* Empty `document_number`
* Document-number length boundaries
* Invalid document characters
* Duplicate `document_number`
* Transaction operation types
* Amount round-trip behavior
* Zero and negative amounts
* Unknown operation type
* Non-existent account
* Idempotency replay scenarios
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
* Consolidating related invalid document-number tests.
* Grouping transaction tests according to behavior.

The intent was to reduce duplicated test structure while keeping individual scenarios explicit.

### 1.6 Framework refactoring

AI was used to help refine the framework implementation, including:

* Removing unnecessary context-manager methods.
* Removing the `expect` parameter from the HTTP layer. This should not be responsible for assertions.
* Moving reusable transport utilities.
* Deriving response fields from dataclasses instead of maintaining duplicated field lists.
* Centralizing pytest configuration in the root `conftest.py`.
* Adding JUnit XML and HTML reporting.
* Keeping generated reports out of source control.
* Adding generic concurrency utilities.
* Keeping concurrency utilities separate from transport-specific utilities.
* Using reusable fixtures for test prerequisites.
* Keeping local assertion helpers local to the test file when they are not shared.

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

I caught this during review of the generated assertion against the intended test oracle and changed the assertion to verify the exact requested operation.

I reviewed whether the assertion would actually fail for the defect the test was intended to detect.

---

## 3. One Decision I Made Against AI's Suggestion

### Authentication was deliberately not implemented

The framework contained a potential `PISMO_AUTH_TOKEN` concept, but the authentication mechanism had not been confirmed.

I deliberately decided to not implement PISMO_AUTH_TOKEN during planning phase as it's not available in the contract.
