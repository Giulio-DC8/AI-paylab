import random
import string
import datetime


def generate_transaction_id():
    chars = string.ascii_letters + string.digits
    return "tx_" + "".join(random.choices(chars, k=12))


def pay(merchant, amount, budget_limit=1000.0):
    """
    Simulates a payment via the x402 protocol.

    Parameters:
        merchant (str): name of the merchant/vendor
        amount (float): amount to pay
        budget_limit (float): threshold above which the payment is rejected

    Returns:
        dict: the simulated transaction result
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
        "protocol": "x402",
        "merchant": merchant,
        "amount": amount,
        "status": status,
        "reason": reason,
        "fee": round(amount * 0.01, 2) if status == "APPROVED" else 0.0,
        "timestamp": datetime.datetime.now().isoformat(),
    }

    return result