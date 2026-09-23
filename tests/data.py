"""Test-data helpers."""

import uuid

# Outside fixture-generated IDs, the contract only requires an integer,
# so we assume this ID is unique in the test environment.
NON_EXISTENT_ACCOUNT_ID = 999_999_999

DOCUMENT_NUMBER_MIN_LENGTH = 10
DOCUMENT_NUMBER_MAX_LENGTH = 14
DEFAULT_DOCUMENT_NUMBER_LENGTH = 11


def unique_document_number(length: int = DEFAULT_DOCUMENT_NUMBER_LENGTH) -> str:
    """Generate a valid-looking document number for isolated test data."""
    if not DOCUMENT_NUMBER_MIN_LENGTH <= length <= DOCUMENT_NUMBER_MAX_LENGTH:
        raise ValueError(
            f"length must be between {DOCUMENT_NUMBER_MIN_LENGTH} and "
            f"{DOCUMENT_NUMBER_MAX_LENGTH}, got {length}"
        )
    
    digits = uuid.uuid4().int
    value = str(digits).zfill(length)[-length:]

    if value[0] == "0":
        value = "1" + value[1:]

    return value


def unique_idempotency_key() -> str:
    """Generate a unique-looking idempotency key for test isolation."""
    return uuid.uuid4().hex
