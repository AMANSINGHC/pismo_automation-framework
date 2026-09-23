"""End-to-end account transaction journey."""

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
from src.utils.assertions import assert_iso8601, assert_shape, assert_status

TRANSACTION_AMOUNT = 100.5

EXPECTED_SIGN_AND_TYPE = {
    OperationType.NORMAL_PURCHASE: (-1, TransactionType.DEBIT),
    OperationType.INSTALLMENT_PURCHASE: (-1, TransactionType.DEBIT),
    OperationType.WITHDRAWAL: (-1, TransactionType.DEBIT),
    OperationType.CREDIT_VOUCHER: (1, TransactionType.CREDIT),
}


@pytest.mark.e2e
@pytest.mark.nightly
@pytest.mark.pre_release
class TestAccountTransactionJourney:

    def test_account_transaction_journey(
        self,
        dedicated_account: AccountResponse,
        transactions_client: TransactionsClient,
    ) -> None:
        """A dedicated account is charged once per documented operation type."""
        for operation_type in OperationType:
            request = CreateTransactionRequest(
                account_id=dedicated_account.account_id,
                amount=TRANSACTION_AMOUNT,
                operation_type_id=operation_type,
            )

            response = transactions_client.create_transaction(request)

            assert_status(response, HTTPStatus.CREATED)
            assert_shape(response.body, TRANSACTION_RESPONSE_FIELDS)

            transaction = response.model(TransactionResponse)
            where = f"{operation_type.name}: {response.body}"
            assert transaction.account_id == dedicated_account.account_id, where
            assert_iso8601(transaction.event_date)
            assert transaction.operation_type_id == operation_type, where
            assert transaction.transaction_id > 0, where
            # The contract states the server applies the sign but not which sign belongs to
            # which operation type (EXPECTED_SIGN_AND_TYPE is an assumption).
            expected_sign, expected_type = EXPECTED_SIGN_AND_TYPE[operation_type]
            assert transaction.type == expected_type, where
            assert transaction.amount == expected_sign * TRANSACTION_AMOUNT, where
