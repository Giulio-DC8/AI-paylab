import random
import string
import datetime


def generate_request_id():
    chars = string.ascii_letters + string.digits
    return "req_" + "".join(random.choices(chars, k=12))


def check_access(merchant, api_key_valid=True, credit_balance=10.0, request_cost=0.01, rate_limit_remaining=100):
    """
    Simulates the traditional API Key / OAuth access model: unlike the
    other protocols, there is no real-time negotiation or payment
    decision here — the payment already happened out-of-band (the
    user registered an account and added credit beforehand). At
    request time, the server only checks whether the pre-existing
    credential is still valid and has enough credit/quota left.

    Parameters:
        merchant (str): name of the API/service provider
        api_key_valid (bool): whether the provided key is valid at all
        credit_balance (float): remaining pre-paid credit on the account
        request_cost (float): cost of this specific request, deducted
            from credit_balance if approved
        rate_limit_remaining (int): remaining requests before hitting
            the rate limit window

    Returns:
        dict: the simulated result, with an http_status_code field
        (200/401/403/429) matching what a real API would return
    """
    if not api_key_valid:
        status = "REJECTED"
        reason = "invalid_api_key"
        http_status_code = 401
    elif rate_limit_remaining <= 0:
        status = "REJECTED"
        reason = "rate_limit_exceeded"
        http_status_code = 429
    elif credit_balance < request_cost:
        status = "REJECTED"
        reason = "insufficient_credit"
        http_status_code = 403
    else:
        status = "APPROVED"
        reason = None
        http_status_code = 200

    result = {
        "transaction_id": generate_request_id(),
        "protocol": "api_key_quota",
        "merchant": merchant,
        "http_status_code": http_status_code,
        "amount": request_cost,
        "request_cost": request_cost,
        "remaining_credit": round(credit_balance - request_cost, 4) if status == "APPROVED" else round(credit_balance, 4),
        "status": status,
        "reason": reason,
        "fee": 0.0,  # no protocol-level fee: cost was already fixed at setup time
        "timestamp": datetime.datetime.now().isoformat(),
    }

    return result