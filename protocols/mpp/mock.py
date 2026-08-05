import random
import string
import datetime


def generate_transaction_id():
    chars = string.ascii_letters + string.digits
    return "tx_mpp_" + "".join(random.choices(chars, k=12))


def pay(merchant, amount, budget_limit=1000.0, currency="EUR"):
    """
    Simulates a payment via the MPP protocol (card/fiat rail).

    Unlike x402 (stablecoin), MPP represents a payment over a
    traditional rail (card/fiat) with a pre-authorized session.
    """
    if amount <= 0:
        status = "REJECTED"
        reason = "invalid_amount"
    elif amount > budget_limit:
        status = "REJECTED"
        reason = "amount_exceeds_limit"
    else:
        status = "APPROVED"
        reason = None

    result = {
        "transaction_id": generate_transaction_id(),
        "protocol": "mpp",
        "merchant": merchant,
        "amount": amount,
        "currency": currency,
        "status": status,
        "reason": reason,
        "fee": round(amount * 0.02, 2) if status == "APPROVED" else 0.0,
        "timestamp": datetime.datetime.now().isoformat(),
    }

    return result