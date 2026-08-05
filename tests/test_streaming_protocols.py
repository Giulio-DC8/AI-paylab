from protocols.lightning_l402.mock import pay_per_request
from protocols.web_monetization.mock import pay_stream


def test_lightning_l402_computes_total_from_per_request_cost():
    """The total amount must equal cost_per_request * request_count."""
    result = pay_per_request(merchant="API_Provider", cost_per_request=0.0001, request_count=1000)

    assert result["amount"] == 0.1
    assert result["status"] == "APPROVED"
    assert "macaroon" in result


def test_lightning_l402_rejects_when_total_exceeds_budget():
    """If cost_per_request * request_count exceeds budget_limit, it must be rejected."""
    result = pay_per_request(
        merchant="API_Provider",
        cost_per_request=10.0,
        request_count=1000,
        budget_limit=1000.0,
    )

    assert result["status"] == "REJECTED"
    assert result["reason"] == "amount_exceeds_limit"


def test_lightning_l402_rejects_invalid_amount():
    """Zero or negative cost_per_request or request_count must be rejected."""
    result = pay_per_request(merchant="API_Provider", cost_per_request=0, request_count=1000)

    assert result["status"] == "REJECTED"
    assert result["reason"] == "invalid_amount"


def test_web_monetization_computes_total_from_rate_and_duration():
    """The total amount must equal rate_per_second * duration_seconds."""
    result = pay_stream(merchant="ContentSite", rate_per_second=0.001, duration_seconds=30)

    assert result["amount"] == 0.03
    assert result["status"] == "APPROVED"


def test_web_monetization_has_no_protocol_fee():
    """Web Monetization/ILP is designed to have negligible/no protocol fee."""
    result = pay_stream(merchant="ContentSite", rate_per_second=0.001, duration_seconds=30)

    assert result["fee"] == 0.0


def test_web_monetization_rejects_when_total_exceeds_budget():
    """If rate_per_second * duration_seconds exceeds budget_limit, it must be rejected."""
    result = pay_stream(
        merchant="ContentSite",
        rate_per_second=100.0,
        duration_seconds=30,
        budget_limit=1000.0,
    )

    assert result["status"] == "REJECTED"
    assert result["reason"] == "amount_exceeds_limit"