import random
import string
import datetime


def generate_stream_id():
    chars = string.ascii_letters + string.digits
    return "stream_" + "".join(random.choices(chars, k=12))


def pay_stream(merchant, rate_per_second, duration_seconds, budget_limit=1000.0):
    """
    Simulates a Web Monetization (Interledger Protocol) payment: a
    continuous background stream of micropayments for as long as a
    resource is being consumed, instead of a single upfront charge.
    If the stream stops early (e.g. the user closes the page), only
    the elapsed portion is ever charged.

    Parameters:
        merchant (str): name of the content/resource provider
        rate_per_second (float): micropayment rate per second of consumption
        duration_seconds (float): how long the stream ran for
        budget_limit (float): threshold above which the stream is rejected

    Returns:
        dict: the simulated transaction result, with total_cost computed
        from rate_per_second * duration_seconds
    """
    total_cost = round(rate_per_second * duration_seconds, 6)

    if rate_per_second <= 0 or duration_seconds <= 0:
        status = "REJECTED"
        reason = "invalid_amount"
    elif total_cost > budget_limit:
        status = "REJECTED"
        reason = "amount_exceeds_limit"
    else:
        status = "APPROVED"
        reason = None

    result = {
        "transaction_id": generate_stream_id(),
        "protocol": "web_monetization",
        "merchant": merchant,
        "rate_per_second": rate_per_second,
        "duration_seconds": duration_seconds,
        "amount": total_cost,
        "status": status,
        "reason": reason,
        "fee": 0.0,  # ILP is designed to have negligible/no protocol fee
        "timestamp": datetime.datetime.now().isoformat(),
    }

    return result