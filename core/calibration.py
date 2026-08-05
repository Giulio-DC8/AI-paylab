import math
from scipy.optimize import minimize_scalar


def win_probability(gap, sensitivity):
    """
    Same logistic function used in negotiation.py:
    probability of winning given a price gap and a sensitivity
    (price_elasticity_belief).
    """
    return 1 / (1 + math.exp(sensitivity * gap))


def find_price_elasticity_belief(target_gap, target_probability):
    """
    Finds the price_elasticity_belief value that produces the target
    probability at a given price gap, minimizing the squared error
    between the obtained probability and the desired one.

    Parameters:
        target_gap (float): reference price gap (e.g. 0.05 = 5%)
        target_probability (float): desired win probability at that
            gap (e.g. 0.30 = 30%)

    Returns:
        float: the calibrated price_elasticity_belief value
    """
    def error(sensitivity):
        return (win_probability(target_gap, sensitivity) - target_probability) ** 2

    result = minimize_scalar(error, bounds=(0.1, 100), method="bounded")
    return round(result.x, 2)


def calibrate_strategies(target_gap=0.05):
    """
    Calibrates the three price_elasticity_belief values for the
    skimming/standard/penetration strategies, based on win
    probability targets at a reference price gap.

    Design targets:
        skimming    -> 40% win probability (stays confident even when pricier)
        standard    -> 25% (middle ground)
        penetration -> 10% (fears being pricier a lot, chases the competitor)

    Returns:
        dict: {"skimming": ..., "standard": ..., "penetration": ...}
    """
    targets = {
        "skimming": 0.40,
        "standard": 0.25,
        "penetration": 0.10,
    }

    return {
        strategy: find_price_elasticity_belief(target_gap, target_probability)
        for strategy, target_probability in targets.items()
    }


if __name__ == "__main__":
    calibrated = calibrate_strategies()
    print("Calibrated values (at a 5% price gap):")
    for strategy, value in calibrated.items():
        print(f"  {strategy}: {value}")