from protocols.x402.mock import pay as pay_x402
from protocols.mpp.mock import pay as pay_mpp
from protocols.visatap.mock import pay as pay_visatap
from protocols.mastercardpay.mock import pay as pay_mastercardpay
from protocols.payforcrawl.mock import pay as pay_payforcrawl

PROTOCOL_FUNCTIONS = {
    "x402": pay_x402,
    "mpp": pay_mpp,
    "visatap": pay_visatap,
    "mastercardpay": pay_mastercardpay,
    "payforcrawl": pay_payforcrawl,
}


class UnsupportedProtocolError(Exception):
    """Raised when an offer requires a protocol that doesn't execute
    payments (e.g. 'ap2', which authorizes but doesn't execute) or
    doesn't exist."""
    pass


def choose_and_pay(merchant, amount, budget_limit=1000.0):
    """Tries every protocol and picks the approved one with the lowest fee."""
    candidates = [fn(merchant=merchant, amount=amount, budget_limit=budget_limit)
                  for fn in PROTOCOL_FUNCTIONS.values()]

    approved = [c for c in candidates if c["status"] == "APPROVED"]
    chosen = min(approved, key=lambda c: c["fee"]) if approved else None

    return {"chosen": chosen, "attempts": candidates}


def choose_best_offer(offers, budget_limit=1000.0):
    """
    Compares multiple offers (different sellers/payment protocols for
    the same trip/product) and picks the one with the lowest TOTAL
    cost (price + fee).
    """
    results = []
    for offer in offers:
        protocol = offer["protocol"]

        if protocol not in PROTOCOL_FUNCTIONS:
            supported = ", ".join(PROTOCOL_FUNCTIONS.keys())
            raise UnsupportedProtocolError(
                f"Protocol '{protocol}' is not valid for a 'compare' offer. "
                f"'{protocol}' doesn't execute payments (it only authorizes them), or doesn't exist. "
                f"Valid protocols for compare/negotiate: {supported}."
            )

        pay_fn = PROTOCOL_FUNCTIONS[protocol]
        result = pay_fn(merchant=offer["merchant"], amount=offer["amount"], budget_limit=budget_limit)
        result["total_cost"] = round(result["amount"] + result["fee"], 2)
        results.append(result)

    approved = [r for r in results if r["status"] == "APPROVED"]
    chosen = min(approved, key=lambda r: r["total_cost"]) if approved else None

    return {"chosen": chosen, "attempts": results}