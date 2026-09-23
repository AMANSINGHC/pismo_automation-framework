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
from src.utils.transport.api_response import ApiResponse
from src.clients.transactions_client import TransactionsClient
from src.models.error import ERROR_RESPONSE_FIELDS, ErrorResponse
from tests.data import NON_EXISTENT_ACCOUNT_ID, unique_idempotency_key
from src.utils.assertions import assert_iso8601, assert_shape, assert_status

pytestmark = pytest.mark.transactions

DEFAULT_AMOUNT = 100.5
INTEGER_AMOUNT = 50
SUB_UNIT_AMOUNT = 0.01
HIGH_PRECISION_AMOUNT = 10.123456

ZERO_AMOUNT = 0.0
NEGATIVE_AMOUNT = -DEFAULT_AMOUNT

CONCURRENT_ATTEMPTS = 5

UNKNOWN_OPERATION_TYPE_ID = 5

ZERO_AMOUNT_ERROR = "amount can't be zero"
UNKNOWN_ACCOUNT_ERROR = "account doesn't exist"
NEGATIVE_AMOUNT_ERROR = "amount can't be negative"
UNKNOWN_OPERATION_TYPE_ERROR = "possible operation type - 1, 2, 3, 4"
MISSING_IDEMPOTENCY_KEY_ERROR = "idempotency key is required"

EXPECTED_SIGN_AND_TYPE = {
    OperationType.NORMAL_PURCHASE: (-1, TransactionType.DEBIT),
    OperationType.INSTALLMENT_PURCHASE: (-1, TransactionType.DEBIT),
    OperationType.WITHDRAWAL: (-1, TransactionType.DEBIT),
    OperationType.CREDIT_VOUCHER: (1, TransactionType.CREDIT),
}


def _assert_transaction_created(
    response: ApiResponse,
    request: CreateTransactionRequest,
    expected_sign: int,
    expected_type: TransactionType,
) -> TransactionResponse:
    """Validate the common contract and transaction-response invariants."""
    assert_status(response, HTTPStatus.CREATED)
    assert_shape(response.body, TRANSACTION_RESPONSE_FIELDS)

    transaction = response.model(TransactionResponse)
    assert transaction.account_id == request.account_id, (
        f"Expected account_id {request.account_id} as sent, got {transaction.account_id}: "
        f"{response.body}"
    )
    assert_iso8601(transaction.event_date)
    assert transaction.operation_type_id == request.operation_type_id, (
        f"Expected operation_type_id {request.operation_type_id} as sent, got "
        f"{transaction.operation_type_id}: {response.body}"
    )
    assert transaction.transaction_id > 0, (
        f"Expected transaction_id to be positive, got {transaction.transaction_id}: "
        f"{response.body}"
    )

    assert transaction.type == expected_type, (
        f"Expected type {expected_type} for operation_type_id {request.operation_type_id}, "
        f"got {transaction.type}: {response.body}"
    )
    assert transaction.amount == expected_sign * request.amount, (
        f"Expected amount {expected_sign * request.amount} (sign {expected_sign} applied to "
        f"{request.amount} as sent), got {transaction.amount}: {response.body}"
    )
    return transaction


class TestCreateTransaction:

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        "operation_type",
        [
            pytest.param(
                OperationType.NORMAL_PURCHASE,
                id="normal-purchase",
                marks=pytest.mark.mock_compatible,
            ),
            pytest.param(OperationType.INSTALLMENT_PURCHASE, id="installment-purchase"),
            pytest.param(OperationType.WITHDRAWAL, id="withdrawal"),
            pytest.param(OperationType.CREDIT_VOUCHER, id="credit-voucher"),
        ],
    )
    def test_create_transaction_for_operation_type(
        self,
        transactions_client: TransactionsClient,
        existing_account: AccountResponse,
        operation_type: OperationType,
    ) -> None:
        """Create a transaction for each operation type."""
        request = CreateTransactionRequest(
            account_id=existing_account.account_id,
            amount=DEFAULT_AMOUNT,
            operation_type_id=operation_type,
        )

        response = transactions_client.create_transaction(request)

        # The contract defines neither an operation type's sign/`type`
        # (EXPECTED_SIGN_AND_TYPE is an assumption).
        expected_sign, expected_type = EXPECTED_SIGN_AND_TYPE[operation_type]
        _assert_transaction_created(response, request, expected_sign, expected_type)


class TestTransactionAmount:

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        "amount",
        [
            pytest.param(INTEGER_AMOUNT, id="integer"),
            pytest.param(
                DEFAULT_AMOUNT,
                id="decimal",
                marks=pytest.mark.mock_compatible,
            ),
        ],
    )
    def test_amount_is_returned_with_expected_sign(
        self,
        transactions_client: TransactionsClient,
        existing_account: AccountResponse,
        amount: float,
    ) -> None:
        """The transaction amount is returned with the expected operation sign."""
        request = CreateTransactionRequest(
            account_id=existing_account.account_id,
            amount=amount,
            operation_type_id=OperationType.NORMAL_PURCHASE,
        )

        response = transactions_client.create_transaction(request)

        assert_status(response, HTTPStatus.CREATED)

        transaction = response.model(TransactionResponse)
        expected_sign, _ = EXPECTED_SIGN_AND_TYPE[OperationType.NORMAL_PURCHASE]
        assert transaction.amount == expected_sign * amount

    @pytest.mark.smoke
    @pytest.mark.nightly
    def test_high_precision_amount_is_recorded(
        self,
        transactions_client: TransactionsClient,
        existing_account: AccountResponse,
    ) -> None:
        """An amount with six decimals is accepted and returned with the debit sign."""
        request = CreateTransactionRequest(
            account_id=existing_account.account_id,
            amount=HIGH_PRECISION_AMOUNT,
            operation_type_id=OperationType.NORMAL_PURCHASE,
        )

        response = transactions_client.create_transaction(request)

        assert_status(response, HTTPStatus.CREATED)
        assert_shape(response.body, TRANSACTION_RESPONSE_FIELDS)

        transaction = response.model(TransactionResponse)
        expected_sign, _ = EXPECTED_SIGN_AND_TYPE[OperationType.NORMAL_PURCHASE]
        # amount has no precision or rounding rule in the contract, so assert only the
        # returned magnitude and the sign promised based on domain reasoning and assumption.
        assert transaction.amount * expected_sign > 0, (
            f"Expected the sign {expected_sign} the prose promises on {HIGH_PRECISION_AMOUNT} "
            f"as sent, got {transaction.amount}: {response.body}"
        )

    @pytest.mark.smoke
    @pytest.mark.nightly
    def test_sub_unit_amount_is_recorded(
        self,
        transactions_client: TransactionsClient,
        existing_account: AccountResponse,
    ) -> None:
        """A one-paisa amount is accepted and returned as sent, signed."""
        request = CreateTransactionRequest(
            account_id=existing_account.account_id,
            amount=SUB_UNIT_AMOUNT,
            operation_type_id=OperationType.NORMAL_PURCHASE,
        )

        response = transactions_client.create_transaction(request)

        # Storage units are not observable: no transaction state oracle is exposed,
        # so the returned amount is the closest available evidence.
        expected_sign, expected_type = EXPECTED_SIGN_AND_TYPE[OperationType.NORMAL_PURCHASE]
        _assert_transaction_created(response, request, expected_sign, expected_type)


@pytest.mark.idempotency
class TestTransactionIdempotency:

    @pytest.mark.nightly
    @pytest.mark.pre_release
    def test_same_idempotency_key_concurrent_replay(
        self,
        transactions_client: TransactionsClient,
        dedicated_account: AccountResponse,
    ) -> None:
        """Send the same transaction concurrently under one idempotency key."""
        request = CreateTransactionRequest(
            account_id=dedicated_account.account_id,
            amount=DEFAULT_AMOUNT,
            operation_type_id=OperationType.NORMAL_PURCHASE,
        )
        key = unique_idempotency_key()

        responses = transactions_client.create_transaction_concurrently(
            request, idempotency_key=key, attempts=CONCURRENT_ATTEMPTS
        )

        assert len(responses) == CONCURRENT_ATTEMPTS

        expected_sign, expected_type = EXPECTED_SIGN_AND_TYPE[OperationType.NORMAL_PURCHASE]
        transactions = [
            _assert_transaction_created(
                response, request, expected_sign, expected_type
            )
            for response in responses
        ]

        # No documented endpoint exposes transaction count or account transaction state.
        # Duplicate detection is therefore limited to the response.
        # Diagnostic evidence only. NOT the correctness oracle.
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
        # Query the transaction-state/count oracle (not available) for the created account and 
        # assert exactly one transaction exists.

    @pytest.mark.nightly
    @pytest.mark.pre_release
    def test_same_idempotency_key_replays_original_response(
        self,
        transactions_client: TransactionsClient,
        dedicated_account: AccountResponse,
    ) -> None:
        """A sequential replay of one key and body is answered 201 with the original result."""
        request = CreateTransactionRequest(
            account_id=dedicated_account.account_id,
            amount=DEFAULT_AMOUNT,
            operation_type_id=OperationType.NORMAL_PURCHASE,
        )
        key = unique_idempotency_key()
        expected_sign, expected_type = EXPECTED_SIGN_AND_TYPE[OperationType.NORMAL_PURCHASE]

        first_response = transactions_client.create_transaction(request, idempotency_key=key)
        first = _assert_transaction_created(
            first_response, request, expected_sign, expected_type
        )

        replay_response = transactions_client.create_transaction(request, idempotency_key=key)

        replay = _assert_transaction_created(
            replay_response, request, expected_sign, expected_type
        )
        assert replay == first, (
            f"Expected the replay to return the original transaction {first!r}, "
            f"got {replay!r}: {replay_response.body}"
        )
        # Query the transaction-state/count oracle (not available) for the created account and 
        # assert exactly one transaction exists.

    @pytest.mark.nightly
    @pytest.mark.pre_release
    def test_same_idempotency_key_with_different_body_is_rejected(
        self,
        transactions_client: TransactionsClient,
        existing_account: AccountResponse,
    ) -> None:
        """Reusing one idempotency key with a changed body is rejected with 409."""
        key = unique_idempotency_key()
        request = CreateTransactionRequest(
            account_id=existing_account.account_id,
            amount=DEFAULT_AMOUNT,
            operation_type_id=OperationType.NORMAL_PURCHASE,
        )
        # The replay carries the same key under a different body.
        replayed = CreateTransactionRequest(
            account_id=existing_account.account_id,
            amount=DEFAULT_AMOUNT,
            operation_type_id=OperationType.CREDIT_VOUCHER,
        )

        first = transactions_client.create_transaction(request, idempotency_key=key)

        assert_status(first, HTTPStatus.CREATED)

        response = transactions_client.create_transaction(replayed, idempotency_key=key)

        assert_status(response, HTTPStatus.CONFLICT)
        assert_shape(response.body, ERROR_RESPONSE_FIELDS)

    @pytest.mark.nightly
    @pytest.mark.negative
    @pytest.mark.pre_release
    def test_missing_idempotency_key_is_rejected(
        self,
        transactions_client: TransactionsClient,
        dedicated_account: AccountResponse,
    ) -> None:
        """A request carrying no idempotency key is rejected with 400 and its message."""
        request = CreateTransactionRequest(
            account_id=dedicated_account.account_id,
            amount=DEFAULT_AMOUNT,
            operation_type_id=OperationType.NORMAL_PURCHASE,
        )

        response = transactions_client.create_transaction(request)

        assert_status(response, HTTPStatus.BAD_REQUEST)
        assert_shape(response.body, ERROR_RESPONSE_FIELDS)

        error = response.model(ErrorResponse)
        assert error.error == MISSING_IDEMPOTENCY_KEY_ERROR


@pytest.mark.negative
class TestCreateTransactionNegative:

    @pytest.mark.smoke
    @pytest.mark.nightly
    @pytest.mark.negative
    @pytest.mark.parametrize(
        ("amount", "expected_error"),
        [
            pytest.param(
                ZERO_AMOUNT,
                ZERO_AMOUNT_ERROR,
                id="zero-amount",
            ),
            pytest.param(
                NEGATIVE_AMOUNT,
                NEGATIVE_AMOUNT_ERROR,
                id="negative-amount",
            ),
        ],
    )
    def test_invalid_amount_is_rejected(
        self,
        transactions_client: TransactionsClient,
        existing_account: AccountResponse,
        amount: float,
        expected_error: str,
    ) -> None:
        """A zero or negative amount is rejected with 422 and its message."""
        request = CreateTransactionRequest(
            account_id=existing_account.account_id,
            amount=amount,
            operation_type_id=OperationType.NORMAL_PURCHASE,
        )

        response = transactions_client.create_transaction(request)

        assert_status(response, HTTPStatus.UNPROCESSABLE_ENTITY)
        assert_shape(response.body, ERROR_RESPONSE_FIELDS)

        error = response.model(ErrorResponse)
        assert error.error == expected_error

    @pytest.mark.smoke
    def test_unknown_operation_type_is_rejected(
        self,
        transactions_client: TransactionsClient,
        existing_account: AccountResponse,
    ) -> None:
        """An unknown operation type is rejected with 422 and its message."""
        request = CreateTransactionRequest(
            account_id=existing_account.account_id,
            amount=DEFAULT_AMOUNT,
            operation_type_id=UNKNOWN_OPERATION_TYPE_ID,
        )

        response = transactions_client.create_transaction(request)

        assert_status(response, HTTPStatus.UNPROCESSABLE_ENTITY)
        assert_shape(response.body, ERROR_RESPONSE_FIELDS)

        error = response.model(ErrorResponse)
        assert error.error == UNKNOWN_OPERATION_TYPE_ERROR

    @pytest.mark.smoke
    def test_unknown_account_is_rejected(
        self,
        transactions_client: TransactionsClient,
    ) -> None:
        """An unknown account is rejected with 422 and its message."""
        request = CreateTransactionRequest(
            account_id=NON_EXISTENT_ACCOUNT_ID,
            amount=DEFAULT_AMOUNT,
            operation_type_id=OperationType.NORMAL_PURCHASE,
        )

        response = transactions_client.create_transaction(request)

        assert_status(response, HTTPStatus.UNPROCESSABLE_ENTITY)
        assert_shape(response.body, ERROR_RESPONSE_FIELDS)

        error = response.model(ErrorResponse)
        assert error.error == UNKNOWN_ACCOUNT_ERROR
