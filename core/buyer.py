from core.negotiation import negotiate
from core.ai_agent import ai_buyer_choice


def negotiate_and_choose(sellers, buyer_preferences="the lowest price", top_n=5, max_rounds=30):
    """
    A component for a buyer agent: negotiates a list of sellers with
    the deterministic engine (fast, free, scales to hundreds of
    participants), then lets a language model choose among the top
    finalists based on natural-language preferences that price alone
    doesn't capture.

    Meant to be imported by developers building their own buyer agent,
    not just used as a demo.

    Parameters:
        sellers (list[Seller]): the already-instantiated sellers to negotiate
        buyer_preferences (str): buyer preferences in natural language
            (e.g. "I prefer a stable vendor, even if slightly pricier")
        top_n (int): how many finalists (the cheapest ones) to pass to
            the AI for the final decision
        max_rounds (int): maximum rounds for the deterministic negotiation

    Returns:
        dict with:
            "finalists": the top_n Sellers with the lowest price after negotiation
            "history": the round-by-round negotiation history
            "chosen_merchant": the name chosen by the AI
            "reasoning": the AI's textual reasoning
    """
    outcome = negotiate(sellers, max_rounds=max_rounds)

    finalists = sorted(sellers, key=lambda s: s.current_price)[:top_n]

    offers = [
        {"merchant": s.name, "amount": s.current_price, "fee": 0, "strategy": s.strategy}
        for s in finalists
    ]

    choice = ai_buyer_choice(offers, buyer_preferences=buyer_preferences)

    return {
        "finalists": finalists,
        "history": outcome["history"],
        "chosen_merchant": choice["chosen_merchant"],
        "reasoning": choice["reasoning"],
    }