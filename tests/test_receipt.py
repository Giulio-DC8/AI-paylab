from protocols.x402.mock import pay
from receipt.generator import create_receipt, verify_receipt


def test_receipt_verifies_when_untouched():
    """A freshly created, unmodified receipt must verify as valid."""
    result = pay(merchant="Amazon", amount=500)
    receipt = create_receipt(result)

    assert verify_receipt(receipt) is True


def test_receipt_fails_when_tampered():
    """A receipt with a field modified after signing must fail verification."""
    result = pay(merchant="Amazon", amount=500)
    receipt = create_receipt(result)

    tampered_receipt = receipt.copy()
    tampered_receipt["amount"] = 5.0

    assert verify_receipt(tampered_receipt) is False


def test_rejected_payment_still_gets_a_valid_receipt():
    """Even a rejected payment (e.g. amount over the threshold) must get a valid receipt."""
    result = pay(merchant="Amazon", amount=5000)  # exceeds the default threshold
    receipt = create_receipt(result)

    assert receipt["status"] == "REJECTED"
    assert verify_receipt(receipt) is True