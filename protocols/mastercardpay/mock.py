import random
import string
import datetime


def generate_transaction_id():
    chars = string.ascii_letters + string.digits
    return "tx_mcap_" + "".join(random.choices(chars, k=12))


def generate_agent_credential():
    """Simulates the credential that recognizes the agent within the Mastercard network."""
    chars = string.ascii_letters + string.digits
    return "mccred_" + "".join(random.choices(chars, k=10))


def pay(merchant, amount, budget_limit=1000.0, agent_verified=True):
    """
    Simulates a payment via Mastercard Agent Pay.

    Like Visa TAP, it recognizes the AI agent as a trusted actor
    within the existing Mastercard network, using cards already
    issued by partner banks.

    Parameters:
        merchant (str): name of the merchant/vendor
        amount (float): amount to pay
        budget_limit (float): threshold above which the payment is rejected
        agent_verified (bool): if False, simulates an agent not verified by the network

    Returns:
        dict: the simulated transaction result
    """
    agent_credential = generate_agent_credential()

    if not agent_verified:
        status = "REJECTED"
        reason = "agent_not_verified"
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
        "protocol": "mastercardpay",
        "agent_credential": agent_credential,
        "merchant": merchant,
        "amount": amount,
        "currency": "EUR",
        "status": status,
        "reason": reason,
        "fee": round(amount * 0.015, 2) if status == "APPROVED" else 0.0,
        "timestamp": datetime.datetime.now().isoformat(),
    }

    return result