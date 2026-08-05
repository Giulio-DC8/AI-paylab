import random
import string
import datetime


def generate_transaction_id():
    chars = string.ascii_letters + string.digits
    return "tx_tap_" + "".join(random.choices(chars, k=12))


def generate_agent_token():
    """Simulates the token that recognizes the agent within the Visa network."""
    chars = string.ascii_letters + string.digits
    return "agenttoken_" + "".join(random.choices(chars, k=10))


def pay(merchant, amount, budget_limit=1000.0, agent_recognized=True):
    """
    Simulates a payment via Visa TAP (Trusted Agent Protocol).

    Unlike x402 and MPP, TAP doesn't introduce a new rail: it
    recognizes the AI agent as a trusted actor within the existing
    Visa network, using cards already issued by banks. If the agent
    isn't "recognized" by the network, the payment is rejected
    regardless of amount.

    Parameters:
        merchant (str): name of the merchant/vendor
        amount (float): amount to pay
        budget_limit (float): threshold above which the payment is rejected
        agent_recognized (bool): if False, simulates an agent not recognized by the network

    Returns:
        dict: the simulated transaction result
    """
    agent_token = generate_agent_token()

    if not agent_recognized:
        status = "REJECTED"
        reason = "agent_not_recognized"
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
        "protocol": "visatap",
        "agent_token": agent_token,
        "merchant": merchant,
        "amount": amount,
        "currency": "EUR",
        "status": status,
        "reason": reason,
        "fee": round(amount * 0.015, 2) if status == "APPROVED" else 0.0,
        "timestamp": datetime.datetime.now().isoformat(),
    }

    return result