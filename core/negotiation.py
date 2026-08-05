import math
from core.calibration import calibrate_strategies


def estimate_win_probability(price, competitor_price, sensitivity=5.0):
    """
    Estimates the probability of winning the negotiation at a given
    price, relative to the competitor's price. Logistic function: if
    the price is below the competitor's, probability is high (close
    to 1); if above, probability is low (close to 0).

    sensitivity: how strongly probability reacts to the price gap.
    Higher value = steeper curve (small discounts matter more).

    Numerically stable even for extreme price gaps: without this
    guard, math.exp() would raise OverflowError for very large
    exponents (e.g. a price 1000x higher than the competitor's).
    """
    gap = (price - competitor_price) / competitor_price
    exponent = sensitivity * gap

    if exponent > 700:
        return 0.0  # competitor is vastly cheaper: winning is nearly impossible
    if exponent < -700:
        return 1.0  # competitor is vastly more expensive: winning is nearly certain

    return 1 / (1 + math.exp(exponent))


def expected_value(price, competitor_price, min_price, sensitivity):
    """
    Expected value of offering a given price: probability of winning
    at that price, multiplied by the remaining margin (how far above
    the seller's own minimum acceptable price - not real profit,
    since min_price doesn't represent actual cost).
    """
    probability = estimate_win_probability(price, competitor_price, sensitivity)
    margin = price - min_price
    return probability * margin


# Computed automatically by core/calibration.py instead of being
# hand-picked - at a 5% price gap, these produce win probabilities of
# roughly 40%/25%/10% respectively (skimming stays confident even
# when pricier, penetration fears being pricier a lot and therefore
# chases the price). If you change the targets in
# calibrate_strategies(), these values update automatically on next
# run - nothing to copy by hand.
STRATEGY_PRICE_ELASTICITY_BELIEF = calibrate_strategies()


class Seller:
    """
    Represents a seller that decides whether to discount by comparing
    the expected value (win probability x remaining margin) of its
    current price against a range of discounted candidate prices,
    instead of applying a fixed discount regardless of context.

    strategy: "skimming" (patient, protects margin),
              "standard" (middle ground, default),
              "penetration" (chases the price, prioritizes winning)
    """

    def __init__(self, name, starting_price, min_margin=0.1, strategy="standard"):
        self.name = name
        self.current_price = starting_price
        self.min_price = round(starting_price * (1 - min_margin), 8)
        self.strategy = strategy
        self.price_elasticity_belief = STRATEGY_PRICE_ELASTICITY_BELIEF.get(strategy, 5.0)

    def counter_offer(self, competitor_price):
        """
        Evaluates a set of candidate prices (from the current price
        down to the seller's own minimum) and picks the one with the
        highest expected value. Only discounts if a candidate price
        improves on staying put. Returns True if it discounted, False
        otherwise.
        """
        if self.current_price <= self.min_price:
            return False  # already at the minimum, nothing to evaluate

        current_ev = expected_value(
            self.current_price, competitor_price, self.min_price, self.price_elasticity_belief
        )

        best_price = self.current_price
        best_ev = current_ev

        steps = 20
        price_range = self.current_price - self.min_price
        for i in range(1, steps + 1):
            candidate = round(self.current_price - price_range * i / steps, 8)
            candidate_ev = expected_value(
                candidate, competitor_price, self.min_price, self.price_elasticity_belief
            )
            if candidate_ev > best_ev:
                best_ev = candidate_ev
                best_price = candidate

        if best_price < self.current_price:
            self.current_price = best_price
            return True
        return False


def negotiate(sellers, max_rounds=5):
    """
    Has multiple sellers negotiate against each other: each round,
    whoever doesn't have the lowest price evaluates whether to
    discount based on expected value. Stops when nobody discounts
    anymore, or after max_rounds rounds.

    Returns:
        dict with "winner" and "history" (starting at round 0 =
        starting prices, before any discounting).
    """
    history = [{
        "round": 0,
        "prices": {s.name: s.current_price for s in sellers},
    }]

    for round_num in range(1, max_rounds + 1):
        best_price = min(s.current_price for s in sellers)
        any_discount = False

        for seller in sellers:
            if seller.current_price > best_price:
                discounted = seller.counter_offer(best_price)
                any_discount = any_discount or discounted

        history.append({
            "round": round_num,
            "prices": {s.name: s.current_price for s in sellers},
        })

        if not any_discount:
            break

    winner = min(sellers, key=lambda s: s.current_price)

    return {
        "winner": winner,
        "history": history,
    }