from core.negotiation import Seller, negotiate


def test_lambda_time_zero_matches_original_behavior():
    """At lambda_time=0.0 (default), behavior must be identical to
    negotiation with no time cost - the penalty term is algebraically
    zero by construction."""
    sellers_default = [
        Seller(name="A", starting_price=900, min_margin=0.1, strategy="skimming"),
        Seller(name="B", starting_price=950, min_margin=0.15, strategy="penetration"),
    ]
    sellers_explicit = [
        Seller(name="A", starting_price=900, min_margin=0.1, strategy="skimming", lambda_time=0.0),
        Seller(name="B", starting_price=950, min_margin=0.15, strategy="penetration", lambda_time=0.0),
    ]

    outcome_default = negotiate(sellers_default, max_rounds=10)
    outcome_explicit = negotiate(sellers_explicit, max_rounds=10)

    assert outcome_default["winner"].current_price == outcome_explicit["winner"].current_price


def test_higher_lambda_time_converges_faster():
    """Higher lambda_time should make an uncompetitive seller settle
    in fewer rounds, since the cost of staying overpriced grows
    faster with time."""
    def run_negotiation(lambda_time):
        sellers = [
            Seller(name="A", starting_price=1000, min_margin=0.3, strategy="skimming", lambda_time=lambda_time),
            Seller(name="B", starting_price=700, min_margin=0.1, strategy="skimming", lambda_time=lambda_time),
        ]
        outcome = negotiate(sellers, max_rounds=30)
        return len(outcome["history"]) - 1

    rounds_low_lambda = run_negotiation(lambda_time=0.05)
    rounds_high_lambda = run_negotiation(lambda_time=0.5)

    assert rounds_high_lambda < rounds_low_lambda


def test_lambda_time_never_crosses_minimum_price():
    """Even under strong time pressure, a seller must never go below
    its own minimum price."""
    sellers = [
        Seller(name="A", starting_price=1000, min_margin=0.29, strategy="skimming", lambda_time=0.5),
        Seller(name="B", starting_price=700, min_margin=0.1, strategy="skimming", lambda_time=0.5),
    ]

    outcome = negotiate(sellers, max_rounds=30)

    seller_a = next(s for s in sellers if s.name == "A")
    assert seller_a.current_price >= seller_a.min_price