"""``POST /transactions`` — contract tag: ``transactions``."""

import pytest

from src.models.transaction import (
    TRANSACTION_RESPONSE_FIELDS,
    CreateTransactionRequest,
    OperationType,
    TransactionResponse,
    TransactionType,
)
from http import HTTPStatus
from src.models.account import AccountResponse
from src.clients.transactions_client import TransactionsClient
from src.models.error import ERROR_RESPONSE_FIELDS, ErrorResponse
from tests.data import UNKNOWN_ACCOUNT_ID, unique_idempotency_key
from src.utils.assertions import assert_iso8601, assert_shape, assert_status

ZERO_AMOUNT = 0.0
INTEGER_AMOUNT = 50
DECIMAL_AMOUNT = 50.75
TRANSACTION_AMOUNT = 50.0
NEGATIVE_AMOUNT = -TRANSACTION_AMOUNT
ZERO_AMOUNT_ERROR = "amount can't be zero"
CONCURRENT_ATTEMPTS = 5
UNKNOWN_ACCOUNT_ERROR = "account doesn't exist"
NEGATIVE_AMOUNT_ERROR = "amount can't be negative"
UNKNOWN_OPERATION_TYPE_ID = 5
UNKNOWN_OPERATION_TYPE_ERROR = "possible operation type - 1, 2, 3, 4"

MOCK_REPLAYS_EXAMPLE = pytest.mark.xfail(
    reason="Prism replays the contract example for every request (operation_type_id 1, amount "
    "-100.5, type debit), so no amount or operation type the request sent can be checked",
    strict=False,
)

MOCK_ACCEPTS_INVALID_REQUEST = pytest.mark.xfail(
    reason="The contract binds no 422 condition and no message text to a non-positive amount, an "
    "unknown operation_type_id or an account that does not exist, and the mock validates "
    "nothing, so it answers 201 with the example instead.",
    strict=False,
)

EXPECTED_SIGN_AND_TYPE = {
    OperationType.NORMAL_PURCHASE: (-1, TransactionType.DEBIT),
    OperationType.INSTALLMENT_PURCHASE: (-1, TransactionType.DEBIT),
    OperationType.WITHDRAWAL: (-1, TransactionType.DEBIT),
    OperationType.CREDIT_VOUCHER: (1, TransactionType.CREDIT),
}


@pytest.mark.transactions
class TestCreateTransaction:

    @pytest.mark.smoke
    @MOCK_REPLAYS_EXAMPLE
    @pytest.mark.parametrize(
        "operation_type",
        [
            pytest.param(OperationType.NORMAL_PURCHASE, id="normal-purchase"),
            pytest.param(OperationType.INSTALLMENT_PURCHASE, id="installment-purchase"),
            pytest.param(OperationType.WITHDRAWAL, id="withdrawal"),
            pytest.param(OperationType.CREDIT_VOUCHER, id="credit-voucher"),
        ],
    )
    def test_create_transaction(
        self,
        transactions_client: TransactionsClient,
        existing_account: AccountResponse,
        operation_type: OperationType,
    ) -> None:
        """Every documented operation type is accepted with 201 and recorded as the type sent."""
        request = CreateTransactionRequest(
            account_id=existing_account.account_id,
            amount=TRANSACTION_AMOUNT,
            operation_type_id=operation_type,
        )

        response = transactions_client.create_transaction(request)

        assert_status(response, HTTPStatus.CREATED)
        assert_shape(response.body, TRANSACTION_RESPONSE_FIELDS)

        transaction = response.model(TransactionResponse)
        assert transaction.account_id == existing_account.account_id
        assert_iso8601(transaction.event_date)
        assert transaction.operation_type_id == operation_type
        assert transaction.transaction_id > 0
        # The contract defines neither an operation type's sign/`type` 
        # (EXPECTED_SIGN_AND_TYPE is an assumption).
        expected_sign, expected_type = EXPECTED_SIGN_AND_TYPE[operation_type]
        assert transaction.type == expected_type
        assert transaction.amount == expected_sign * TRANSACTION_AMOUNT

    @pytest.mark.smoke
    @MOCK_REPLAYS_EXAMPLE
    @pytest.mark.parametrize(
        "amount",
        [
            pytest.param(INTEGER_AMOUNT, id="integer"),
            pytest.param(DECIMAL_AMOUNT, id="decimal"),
        ],
    )
    def test_amount_round_trip(
        self,
        transactions_client: TransactionsClient,
        existing_account: AccountResponse,
        amount: float,
    ) -> None:
        """A whole-number and a fractional amount are recorded with the value the request sent."""
        request = CreateTransactionRequest(
            account_id=existing_account.account_id,
            amount=amount,
            operation_type_id=OperationType.NORMAL_PURCHASE,
        )

        response = transactions_client.create_transaction(request)

        assert_status(response, HTTPStatus.CREATED)
        assert_shape(response.body, TRANSACTION_RESPONSE_FIELDS)

        transaction = response.model(TransactionResponse)
        expected_sign, _ = EXPECTED_SIGN_AND_TYPE[OperationType.NORMAL_PURCHASE]
        assert transaction.amount == expected_sign * amount

    @pytest.mark.pre_release
    @pytest.mark.idempotency
    @MOCK_REPLAYS_EXAMPLE
    def test_same_idempotency_key_charges_once(
        self,
        transactions_client: TransactionsClient,
        dedicated_account: AccountResponse,
    ) -> None:
        """Copies of one transaction in flight under one idempotency key are recorded once."""
        request = CreateTransactionRequest(
            account_id=dedicated_account.account_id,
            amount=TRANSACTION_AMOUNT,
            operation_type_id=OperationType.NORMAL_PURCHASE,
        )
        key = unique_idempotency_key()

        responses = transactions_client.create_transaction_concurrently(
            request, idempotency_key=key, attempts=CONCURRENT_ATTEMPTS
        )

        for response in responses:
            assert_status(response, HTTPStatus.CREATED)

        transactions = [response.model(TransactionResponse) for response in responses]
        # No documented endpoint exposes transaction count or account transaction state.
        # Duplicate detection is therefore limited to the response.
        # Diagnostic evidency only. NOT the correctness oracle.
        statuses = [(response.status_code, response.url) for response in responses]
        recorded = [
            (transaction.transaction_id, transaction.amount) for transaction in transactions
        ]
        evidence = f"statuses: {statuses}; transactions: {recorded}"
        transaction_ids = {transaction.transaction_id for transaction in transactions}
    
        assert len(transaction_ids) == 1, (
            f"Expected one transaction for one idempotency key, got {len(transaction_ids)}; "
            f"{evidence}"
        )
        # Query the transaction-state/count oracle for the created account and assert exactly 
        # one transaction exists.

        expected_sign, expected_type = EXPECTED_SIGN_AND_TYPE[OperationType.NORMAL_PURCHASE]
        for transaction in transactions:
            assert transaction.account_id == dedicated_account.account_id, evidence
            assert_iso8601(transaction.event_date)
            assert transaction.operation_type_id == OperationType.NORMAL_PURCHASE, evidence
            assert transaction.type == expected_type, evidence
            assert transaction.amount == expected_sign * TRANSACTION_AMOUNT, evidence

    @MOCK_ACCEPTS_INVALID_REQUEST
    @pytest.mark.parametrize(
        ("amount", "operation_type_id", "account_id", "expected_error"),
        [
            pytest.param(
                ZERO_AMOUNT,
                OperationType.NORMAL_PURCHASE,
                None,
                ZERO_AMOUNT_ERROR,
                id="zero-amount",
            ),
            pytest.param(
                NEGATIVE_AMOUNT,
                OperationType.NORMAL_PURCHASE,
                None,
                NEGATIVE_AMOUNT_ERROR,
                id="negative-amount",
            ),
            pytest.param(
                TRANSACTION_AMOUNT,
                UNKNOWN_OPERATION_TYPE_ID,
                None,
                UNKNOWN_OPERATION_TYPE_ERROR,
                id="unknown-operation-type",
            ),
            pytest.param(
                TRANSACTION_AMOUNT,
                OperationType.NORMAL_PURCHASE,
                UNKNOWN_ACCOUNT_ID,
                UNKNOWN_ACCOUNT_ERROR,
                id="unknown-account",
            ),
        ],
    )
    def test_create_transaction_with_invalid_request(
        self,
        transactions_client: TransactionsClient,
        existing_account: AccountResponse,
        amount: float,
        operation_type_id: int | OperationType,
        account_id: int | None,
        expected_error: str,
    ) -> None:
        """An invalid amount, operation type or account is rejected with 422 and its message."""
        request = CreateTransactionRequest(
            account_id=existing_account.account_id if account_id is None else account_id,
            amount=amount,
            operation_type_id=operation_type_id,
        )

        response = transactions_client.create_transaction(request)

        assert_status(response, HTTPStatus.UNPROCESSABLE_ENTITY)
        assert_shape(response.body, ERROR_RESPONSE_FIELDS)

        error = response.model(ErrorResponse)
        assert error.error == expected_error
