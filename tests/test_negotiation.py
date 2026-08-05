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