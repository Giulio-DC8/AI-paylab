import random
import string
import datetime


def generate_transaction_id():
    chars = string.ascii_letters + string.digits
    return "tx_ap2_" + "".join(random.choices(chars, k=12))


def generate_mandate_id():
    chars = string.ascii_letters + string.digits
    return "mandate_" + "".join(random.choices(chars, k=10))


def pay(merchant, amount, budget_limit=1000.0, mandate_signed=True):
    """
    Simulates a payment via the AP2 protocol.

    Unlike x402, AP2 first requires a "mandate" signed by the
    user/agent authorizing the spend. If the mandate isn't signed,
    the payment is rejected regardless of amount.

    Parameters:
        merchant (str): name of the merchant/vendor
        amount (float): amount to pay
        budget_limit (float): threshold above which the payment is rejected
        mandate_signed (bool): if False, simulates a missing/unsigned mandate

    Returns:
        dict: the simulated transaction result
    """
    mandate_id = generate_mandate_id()

    if not mandate_signed:
        status = "REJECTED"
        reason = "mandate_not_signed"
    elif amount <= 0:
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
        "protocol": "ap2",
        "mandate_id": mandate_id,
        "merchant": merchant,
        "amount": amount,
        "status": status,
        "reason": reason,
        "fee": round(amount * 0.005, 2) if status == "APPROVED" else 0.0,
        "timestamp": datetime.datetime.now().isoformat(),
    }

    return result