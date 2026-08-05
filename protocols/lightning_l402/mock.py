import random
import string
import datetime


def generate_transaction_id():
    chars = string.ascii_letters + string.digits
    return "tx_l402_" + "".join(random.choices(chars, k=12))


def generate_macaroon():
    """Simulates an L402 macaroon: a token that bundles authentication
    and payment authorization for a specific resource/request."""
    chars = string.ascii_letters + string.digits
    return "macaroon_" + "".join(random.choices(chars, k=16))


def pay_per_request(merchant, cost_per_request, request_count, budget_limit=1000.0):
    """
    Simulates a Lightning L402 payment: unlike the other protocols
    (single fixed-amount transaction), L402 charges per individual
    request against a resource, bundling authentication and payment
    into one step via a macaroon token.

    Parameters:
        merchant (str): name of the resource/API provider
        cost_per_request (float): price for a single request (typically
            a fraction of a cent)
        request_count (int): how many requests are being made in this batch
        budget_limit (float): threshold above which the total is rejected

    Returns:
        dict: the simulated transaction result, with total_cost computed
        from cost_per_request * request_count
    """
    total_cost = round(cost_per_request * request_count, 6)

    if cost_per_request <= 0 or request_count <= 0:
        status = "REJECTED"
        reason = "invalid_amount"
    elif total_cost > budget_limit:
        status = "REJECTED"
        reason = "amount_exceeds_limit"
    else:
        status = "APPROVED"
        reason = None

    result = {
        "transaction_id": generate_transaction_id(),
        "protocol": "lightning_l402",
        "macaroon": generate_macaroon(),
        "merchant": merchant,
        "cost_per_request": cost_per_request,
        "request_count": request_count,
        "amount": total_cost,
        "status": status,
        "reason": reason,
        "fee": round(total_cost * 0.001, 6) if status == "APPROVED" else 0.0,
        "timestamp": datetime.datetime.now().isoformat(),
    }

    return result