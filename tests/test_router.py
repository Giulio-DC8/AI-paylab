import pytest
from core.router import choose_best_offer, choose_and_pay, UnsupportedProtocolError


def test_unsupported_protocol_raises_clear_error():
    """An offer with a protocol that doesn't execute payments (e.g.
    'ap2', which only authorizes) must raise a clear error, not a
    generic KeyError."""
    offers = [
        {"merchant": "TestMerchant", "amount": 500, "protocol": "ap2"}
    ]

    with pytest.raises(UnsupportedProtocolError):
        choose_best_offer(offers)


def test_choose_best_offer_picks_lowest_total_cost():
    """Among multiple valid offers, it must pick the one with the
    lowest total cost (amount + fee), not necessarily the lowest
    price alone."""
    offers = [
        {"merchant": "Lufthansa", "amount": 950, "protocol": "visatap"},
        {"merchant": "Emirates", "amount": 900, "protocol": "x402"},
    ]

    outcome = choose_best_offer(offers)

    assert outcome["chosen"]["merchant"] == "Emirates"


def test_choose_and_pay_picks_lowest_fee_among_approved():
    """Among all execution protocols, it must pick the approved one
    with the lowest fee."""
    outcome = choose_and_pay(merchant="TestMerchant", amount=500)

    approved = [a for a in outcome["attempts"] if a["status"] == "APPROVED"]
    assert outcome["chosen"]["fee"] == min(a["fee"] for a in approved)