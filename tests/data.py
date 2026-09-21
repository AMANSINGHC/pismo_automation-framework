"""Test-data helpers."""

import random

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
