import random
import string
import datetime


def generate_transaction_id():
    chars = string.ascii_letters + string.digits
    return "tx_pfc_" + "".join(random.choices(chars, k=12))


def pay(merchant, amount, budget_limit=1000.0, zone=None):
    """
    Simulates a payment via Cloudflare Pay per Crawl.

    Cloudflare acts as the Merchant of Record: the crawler/agent pays
    to access a site's content (zone), not to buy a product. Uses the
    same HTTP 402 mechanism as x402, but applied to crawling/content
    access instead of generic e-commerce.

    Parameters:
        merchant (str): name of the publisher/site owner
        amount (float): price to access the zone
        budget_limit (float): threshold above which the payment is rejected
        zone (str): domain/zone being accessed (optional)

    Returns:
        dict: the simulated transaction result
    """
    if zone is None:
        zone = merchant.lower().replace(" ", "") + ".com"

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
        "protocol": "payforcrawl",
        "merchant": merchant,
        "zone": zone,
        "amount": amount,
        "status": status,
        "reason": reason,
        "fee": round(amount * 0.03, 2) if status == "APPROVED" else 0.0,
        "timestamp": datetime.datetime.now().isoformat(),
    }

    return result