from core.negotiation import Seller, negotiate


def test_negotiate_works_with_per_request_rate_scale():
    """
    The negotiation engine is agnostic to what the price represents:
    it must work identically whether starting_price is a total amount
    (e.g. 900) or a per-request rate (e.g. 0.00015), since the math
    only cares about the relative price gap, not the absolute scale.
    """
    sellers = [
        Seller(name="APIProviderA", starting_price=0.00015, min_margin=0.2, strategy="skimming"),
        Seller(name="APIProviderB", starting_price=0.00012, min_margin=0.15, strategy="penetration"),
    ]

    outcome = negotiate(sellers, max_rounds=10)

    all_rates = [s.current_price for s in sellers]
    assert outcome["winner"].current_price == min(all_rates)
    assert outcome["winner"].current_price > 0  # never negative or zero after negotiation