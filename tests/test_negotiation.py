import random

from core.negotiation import Seller, negotiate, estimate_win_probability


def test_win_probability_is_fifty_percent_at_zero_gap():
    """At an equal price to the competitor, win probability must be 50%."""
    probability = estimate_win_probability(price=900, competitor_price=900, sensitivity=20)
    assert abs(probability - 0.5) < 0.001


def test_win_probability_decreases_as_price_increases():
    """The pricier a seller is relative to the competitor, the lower
    its estimated win probability must be."""
    prob_cheaper = estimate_win_probability(price=850, competitor_price=900, sensitivity=20)
    prob_pricier = estimate_win_probability(price=950, competitor_price=900, sensitivity=20)

    assert prob_cheaper > 0.5
    assert prob_pricier < 0.5
    assert prob_cheaper > prob_pricier


def test_seller_never_discounts_below_min_price():
    """A seller must never offer a price below its own minimum,
    regardless of the competitor's price."""
    seller = Seller(name="TestSeller", starting_price=1000, min_margin=0.1, strategy="penetration")

    # Unrealistically cheap competitor, to force the maximum possible discount
    seller.counter_offer(competitor_price=1)

    assert seller.current_price >= seller.min_price


def test_negotiate_produces_a_coherent_winner():
    """In a simple two-seller case, the winner must have the lowest
    final price among all sellers."""
    sellers = [
        Seller(name="A", starting_price=900, min_margin=0.1, strategy="skimming"),
        Seller(name="B", starting_price=950, min_margin=0.15, strategy="penetration"),
    ]

    outcome = negotiate(sellers, max_rounds=10)

    all_prices = [s.current_price for s in sellers]
    assert outcome["winner"].current_price == min(all_prices)


def test_negotiate_history_starts_at_round_zero_with_starting_prices():
    """The first history entry must represent the starting prices,
    before any discounting."""
    sellers = [
        Seller(name="A", starting_price=900, min_margin=0.1, strategy="standard"),
        Seller(name="B", starting_price=950, min_margin=0.1, strategy="standard"),
    ]

    outcome = negotiate(sellers, max_rounds=5)

    assert outcome["history"][0]["round"] == 0
    assert outcome["history"][0]["prices"] == {"A": 900, "B": 950}


def test_single_seller_negotiation_is_a_noop():
    """A single Seller has no competitor to react to: negotiate() must
    return it as the winner at its unchanged starting price, without
    ever discounting."""
    seller = Seller(name="Solo", starting_price=1000, min_margin=0.2, strategy="standard")

    outcome = negotiate([seller], max_rounds=10)

    assert outcome["winner"] is seller
    assert outcome["winner"].current_price == 1000
    assert all(round_info["prices"]["Solo"] == 1000 for round_info in outcome["history"])


def test_negotiation_converges_for_random_seller_pools():
    """For randomly generated seller pools (fixed seeds, for
    reproducibility), negotiation must settle - stop discounting -
    well before a generous round budget is exhausted, not just for
    the hand-picked two-seller scenarios above."""
    strategies = ["skimming", "standard", "penetration"]
    max_rounds = 100

    for seed in (1, 2, 3):
        rng = random.Random(seed)
        sellers = [
            Seller(
                name=f"Seller_{i}",
                starting_price=round(rng.uniform(800, 1000), 2),
                min_margin=round(rng.uniform(0.05, 0.20), 3),
                strategy=rng.choice(strategies),
            )
            for i in range(30)
        ]

        outcome = negotiate(sellers, max_rounds=max_rounds)

        rounds_used = len(outcome["history"]) - 1
        assert rounds_used < max_rounds, (
            f"seed={seed}: still discounting after {max_rounds} rounds - did not converge"
        )


def test_negotiate_scales_to_hundreds_of_sellers():
    """The engine must handle hundreds of sellers without errors and
    still produce a coherent winner, matching the scale already
    exercised manually via examples/generate_sellers.py (same field
    ranges and seed)."""
    strategies = ["skimming", "standard", "penetration"]
    rng = random.Random(42)
    sellers = [
        Seller(
            name=f"Seller_{i:03d}",
            starting_price=round(rng.uniform(800, 1000), 2),
            min_margin=round(rng.uniform(0.05, 0.20), 3),
            strategy=rng.choice(strategies),
        )
        for i in range(350)
    ]

    outcome = negotiate(sellers, max_rounds=30)

    all_prices = [s.current_price for s in sellers]
    assert outcome["winner"].current_price == min(all_prices)