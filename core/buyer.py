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


class Buyer:
    """
    Stateful wrapper around negotiate_and_choose(): holds the buyer's
    preferences and negotiation settings so they don't need to be
    passed at every call. Adds no logic of its own - choose() just
    forwards to negotiate_and_choose() with the stored settings.

    choose() inherits every limitation of the AI-assisted path it
    delegates to:
    - Not deterministic: the same sellers/preferences can yield a
      different chosen_merchant/reasoning across calls, since the
      final pick is made by an LLM (core/ai_agent.py's
      ai_buyer_choice()), not by the deterministic negotiate() engine.
    - Requires GEMINI_API_KEY to be set in the environment - raises
      RuntimeError otherwise (see core/ai_agent.py's _get_client()).
    - Not covered by automated tests, for the same reason it isn't
      reproducible: there's no fixed expected output to assert against.
    """

    def __init__(self, preferences="the lowest price", top_n=5, max_rounds=30):
        self.preferences = preferences
        self.top_n = top_n
        self.max_rounds = max_rounds

    def choose(self, sellers):
        return negotiate_and_choose(
            sellers,
            buyer_preferences=self.preferences,
            top_n=self.top_n,
            max_rounds=self.max_rounds,
        )