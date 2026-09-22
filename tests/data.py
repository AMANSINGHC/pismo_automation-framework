"""Test-data helpers."""

import random

# Far above the small ids an environment hands out and still inside the contract's `integer`
# type, so no run of this suite can have created it.
UNKNOWN_ACCOUNT_ID = 999_999_999
DOCUMENT_NUMBER_MIN_LENGTH = 10
DOCUMENT_NUMBER_MAX_LENGTH = 14
DEFAULT_DOCUMENT_NUMBER_LENGTH = 11


def unique_document_number(length: int = DEFAULT_DOCUMENT_NUMBER_LENGTH) -> str:
    """Return a document number that cannot collide with another run's account."""
    if not DOCUMENT_NUMBER_MIN_LENGTH <= length <= DOCUMENT_NUMBER_MAX_LENGTH:
        raise ValueError(
            f"length must be between {DOCUMENT_NUMBER_MIN_LENGTH} and "
            f"{DOCUMENT_NUMBER_MAX_LENGTH}, got {length}"
        )
    first_digit = random.choice("123456789")
    return first_digit + "".join(random.choices("0123456789", k=length - 1))
