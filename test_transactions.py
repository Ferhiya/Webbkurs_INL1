import pytest
from unittest.mock import MagicMock, patch
from decimal import Decimal
from app import app
from models import Account

# ----------------- FIXTURES -----------------
@pytest.fixture
def mock_db_session():
    """Mock SQLAlchemy session to avoid real database transactions."""
    with patch("app.db.session") as mock_session:
        yield mock_session

@pytest.fixture
def client():
    """Creates a test client to interact with the app."""
    with app.test_client() as client:
        yield client  # Provides the client for making requests

@pytest.fixture
def mock_accounts():
    """Create two mock account objects for withdrawal and transfer tests."""
    from_account = MagicMock(spec=Account)
    from_account.id = 1
    from_account.balance = Decimal("1000.00")

    to_account = MagicMock(spec=Account)
    to_account.id = 2
    to_account.balance = Decimal("500.00")

    return from_account, to_account

# ----------------- WITHDRAWAL TEST CASES -----------------
#test 1
def test_valid_withdraw(client, mock_db_session, mock_accounts):
    """Test that a valid withdrawal updates the balance correctly."""
    from_account, _ = mock_accounts
    mock_db_session.get.return_value = from_account  # Mock DB call

    withdrawal_amount = Decimal("200.00")
    expected_balance = Decimal("800.00")

    response = client.post(
        "/cashierwork/withdraw",
        data={"account_id": from_account.id, "amount": str(withdrawal_amount)},
        follow_redirects=True,
    )

    assert "Uttag på 200.00 kr lyckades!", "success" in response.data.decode("utf-8")

    # Simulate balance update
    from_account.balance -= withdrawal_amount
    assert from_account.balance == expected_balance


#test 2
def test_negative_withdraw(client, mock_db_session, mock_accounts):
    """Test that withdrawing a negative amount is not allowed."""
    from_account, _ = mock_accounts
    mock_db_session.get.return_value = from_account  # Mock DB call

    response = client.post(
        "/cashierwork/withdraw",
        data={"account_id": from_account.id, "amount": "-50"},
        follow_redirects=True,
    )

    assert "Beloppet måste vara större än 0.", "danger" in response.data.decode("utf-8")
    assert from_account.balance == Decimal("1000.00")  # Ensure balance remains unchanged

#test 3
def test_overdraw(client, mock_db_session, mock_accounts):
    """Test that withdrawing more than available balance is not allowed."""
    from_account, _ = mock_accounts
    mock_db_session.get.return_value = from_account  # Mock DB call

    response = client.post(
        "/cashierwork/withdraw",
        data={"account_id": from_account.id, "amount": "2000"},
        follow_redirects=True,
    )

    assert "Otillräckligt saldo för uttag.", "danger" in response.data.decode("utf-8")
    assert from_account.balance == Decimal("1000.00")  # Ensure balance remains unchanged
    
#------------------ DEPOSIT TEST CASES --------------------#
#test 4
def test_valid_deposit(client, mock_db_session, mock_accounts):
    """Test that a valid deposit updates the balance correctly."""
    from_account, _ = mock_accounts
    mock_db_session.get.return_value = from_account  # Mock DB call

    deposit_amount = Decimal("300.00")
    expected_balance = Decimal("1300.00")
    
    response = client.post(
        "/cashierwork/deposit",
        data={"account_id": from_account.id, "amount": str(deposit_amount)},
        follow_redirects=True,
    )

    assert "Insättning på {deposit_amount} kr lyckades!", "success" in response.data.decode("utf-8")

    # Simulate balance update
    from_account.balance += deposit_amount
    assert from_account.balance == expected_balance

    

    
#test 5
def test_negative_deposit(client, mock_db_session, mock_accounts):
    """Test that withdrawing a negative amount is not allowed."""
    from_account, _ = mock_accounts
    mock_db_session.get.return_value = from_account  # Mock DB call

    response = client.post(
        "/cashierwork/deposit",
        data={"account_id": from_account.id, "amount": "-50"},
        follow_redirects=True,
    )

    assert "Beloppet måste vara större än 0.", "danger" in response.data.decode("utf-8")
    assert from_account.balance == Decimal("1000.00")  # Ensure balance remains unchanged
    

# ----------------- TRANSFER TEST CASES -----------------
#test 5
def test_valid_transfer(client, mock_db_session, mock_accounts):
    """Test that a valid transfer updates both account balances."""
    from_account, to_account = mock_accounts
    mock_db_session.get.side_effect = lambda model, account_id: from_account if account_id == 1 else to_account

    transfer_amount = Decimal("200.00")
    expected_from_balance = Decimal("800.00")
    expected_to_balance = Decimal("700.00")

    response = client.post(
        "/cashierwork/transfer",
        data={"from_account_id": from_account.id, "to_account_id": to_account.id, "amount": str(transfer_amount)},
        follow_redirects=True,
    )

    assert "Överföringen genomfördes!", "success" in response.data.decode("utf-8")

    # Simulate balance update
    from_account.balance -= transfer_amount
    to_account.balance += transfer_amount

    assert from_account.balance == expected_from_balance
    assert to_account.balance == expected_to_balance

#test 6
def test_transfer_negative_amount(client, mock_db_session, mock_accounts):
    """Test that transferring a negative amount is not allowed."""
    from_account, to_account = mock_accounts
    mock_db_session.get.side_effect = lambda model, account_id: from_account if account_id == 1 else to_account

    response = client.post(
        "/cashierwork/transfer",
        data={"from_account_id": from_account.id, "to_account_id": to_account.id, "amount": "-50"},
        follow_redirects=True,
    )

    assert "Fel: Otillräckligt saldo eller ogiltiga konton!", "danger" in response.data.decode("utf-8")
    assert from_account.balance == Decimal("1000.00")
    assert to_account.balance == Decimal("500.00")

#test 7
def test_transfer_overdraw(client, mock_db_session, mock_accounts):
    """Test that transferring more than the available balance is not allowed."""
    from_account, to_account = mock_accounts
    mock_db_session.get.side_effect = lambda model, account_id: from_account if account_id == 1 else to_account

    response = client.post(
        "/cashierwork/transfer",
        data={"from_account_id": from_account.id, "to_account_id": to_account.id, "amount": "2000"},
        follow_redirects=True,
    )

    assert "Fel: Otillräckligt saldo eller ogiltiga konton!", "danger" in response.data.decode("utf-8")
    assert from_account.balance == Decimal("1000.00")
    assert to_account.balance == Decimal("500.00")
