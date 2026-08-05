from protocols.api_key_quota.mock import check_access


def test_valid_key_with_sufficient_credit_is_approved():
    """A valid key with enough credit must return HTTP 200 and deduct the cost."""
    result = check_access(merchant="WeatherAPI", api_key_valid=True, credit_balance=10.0, request_cost=0.01)

    assert result["status"] == "APPROVED"
    assert result["http_status_code"] == 200
    assert result["remaining_credit"] == 9.99


def test_invalid_key_returns_401():
    """An invalid API key must be rejected with HTTP 401, regardless of credit."""
    result = check_access(merchant="WeatherAPI", api_key_valid=False, credit_balance=100.0)

    assert result["status"] == "REJECTED"
    assert result["http_status_code"] == 401
    assert result["reason"] == "invalid_api_key"


def test_insufficient_credit_returns_403():
    """A valid key with not enough credit must be rejected with HTTP 403."""
    result = check_access(merchant="WeatherAPI", api_key_valid=True, credit_balance=0.005, request_cost=0.01)

    assert result["status"] == "REJECTED"
    assert result["http_status_code"] == 403
    assert result["reason"] == "insufficient_credit"


def test_rate_limit_exceeded_returns_429():
    """A valid key with sufficient credit but no rate limit left must be rejected with HTTP 429."""
    result = check_access(merchant="WeatherAPI", api_key_valid=True, rate_limit_remaining=0)

    assert result["status"] == "REJECTED"
    assert result["http_status_code"] == 429
    assert result["reason"] == "rate_limit_exceeded"


def test_no_protocol_level_fee():
    """Unlike the other protocols, api_key_quota has no per-transaction fee:
    the cost was already fixed out-of-band when the account was set up."""
    result = check_access(merchant="WeatherAPI")

    assert result["fee"] == 0.0