"""``POST /accounts`` — contract tag: ``accounts``."""

import pytest

from tests.data import (
    DEFAULT_DOCUMENT_NUMBER_LENGTH,
    DOCUMENT_NUMBER_MAX_LENGTH,
    DOCUMENT_NUMBER_MIN_LENGTH,
    unique_document_number,
)
from http import HTTPStatus
from src.clients.accounts_client import AccountsClient
from src.utils.assertions import assert_shape, assert_status
from src.models.error import ERROR_RESPONSE_FIELDS, ErrorResponse
from src.models.account import ACCOUNT_RESPONSE_FIELDS, AccountResponse, CreateAccountRequest

EMPTY_DOCUMENT_NUMBER = ""
NON_DIGIT_DOCUMENT_NUMBER = "1" * (DEFAULT_DOCUMENT_NUMBER_LENGTH - 1) + "a"
BELOW_MINIMUM_DOCUMENT_NUMBER = "1" * (DOCUMENT_NUMBER_MIN_LENGTH - 1)
ABOVE_MAXIMUM_DOCUMENT_NUMBER = "1" * (DOCUMENT_NUMBER_MAX_LENGTH + 1)

DOCUMENT_LENGTH_ERROR = "document_number should be b/w 10 and 14 digits"
EMPTY_DOCUMENT_NUMBER_ERROR = "document_number can't be empty"
NON_DIGIT_DOCUMENT_NUMBER_ERROR = "document_number should only contain digits"
DUPLICATE_DOCUMENT_NUMBER_ERROR = "document_number already exists"


@pytest.mark.accounts
class TestCreateAccount:

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        "document_number_length",
        [
            pytest.param(
                DOCUMENT_NUMBER_MIN_LENGTH, 
                id="minimum", 
                marks=pytest.mark.nightly,
            ),
            pytest.param(DEFAULT_DOCUMENT_NUMBER_LENGTH, id="default"),
            pytest.param(
                DOCUMENT_NUMBER_MAX_LENGTH, 
                id="maximum", 
                marks=pytest.mark.nightly,
            ),
        ],
    )
    def test_create_account(
        self, accounts_client: AccountsClient, document_number_length: int
    ) -> None:
        """A new account is answered with 201 and the documented response shape."""
        request = CreateAccountRequest(
            document_number=unique_document_number(document_number_length)
        )

        response = accounts_client.create_account(request)

        assert_status(response, HTTPStatus.CREATED)
        assert_shape(response.body, ACCOUNT_RESPONSE_FIELDS)

        account = response.model(AccountResponse)
        assert account.account_id > 0
        assert account.document_number == request.document_number

    @pytest.mark.smoke
    @pytest.mark.nightly
    @pytest.mark.negative
    @pytest.mark.parametrize(
        ("document_number", "expected_status", "expected_error"),
        [
            pytest.param(
                EMPTY_DOCUMENT_NUMBER,
                HTTPStatus.BAD_REQUEST,
                EMPTY_DOCUMENT_NUMBER_ERROR,
                id="empty",
            ),
            pytest.param(
                BELOW_MINIMUM_DOCUMENT_NUMBER,
                HTTPStatus.BAD_REQUEST,
                DOCUMENT_LENGTH_ERROR,
                id="below-minimum",
            ),
            pytest.param(
                ABOVE_MAXIMUM_DOCUMENT_NUMBER,
                HTTPStatus.BAD_REQUEST,
                DOCUMENT_LENGTH_ERROR,
                id="above-maximum",
            ),
            pytest.param(
                NON_DIGIT_DOCUMENT_NUMBER,
                HTTPStatus.UNPROCESSABLE_ENTITY,
                NON_DIGIT_DOCUMENT_NUMBER_ERROR,
                id="non-digit",
            ),
        ],
    )
    def test_create_account_with_invalid_document_number(
        self,
        accounts_client: AccountsClient,
        document_number: str,
        expected_status: HTTPStatus,
        expected_error: str,
    ) -> None:
        """An empty, out-of-range or non-digit document_number is rejected with 400 or 422."""
        request = CreateAccountRequest(document_number=document_number)

        response = accounts_client.create_account(request)

        assert_status(response, expected_status)
        assert_shape(response.body, ERROR_RESPONSE_FIELDS)

        error = response.model(ErrorResponse)
        assert error.error == expected_error

    @pytest.mark.smoke
    @pytest.mark.negative
    def test_create_account_with_duplicate_document_number(
        self, accounts_client: AccountsClient, existing_account: AccountResponse
    ) -> None:
        """A document_number that already has an account is rejected with 409."""
        request = CreateAccountRequest(document_number=existing_account.document_number)

        response = accounts_client.create_account(request)

        assert_status(response, HTTPStatus.CONFLICT)
        assert_shape(response.body, ERROR_RESPONSE_FIELDS)

        error = response.model(ErrorResponse)
        assert error.error == DUPLICATE_DOCUMENT_NUMBER_ERROR
