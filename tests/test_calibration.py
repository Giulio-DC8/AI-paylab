from core.calibration import calibrate_strategies, win_probability


def test_calibrated_values_produce_target_probabilities():
    """Each calibrated value must produce, at a 5% price gap, a
    probability close to its declared design target
    (skimming=40%, standard=25%, penetration=10%)."""
    calibrated = calibrate_strategies(target_gap=0.05)

    targets = {
        "skimming": 0.40,
        "standard": 0.25,
        "penetration": 0.10,
    }

    for strategy, target_probability in targets.items():
        sensitivity = calibrated[strategy]
        actual_probability = win_probability(0.05, sensitivity)
        assert abs(actual_probability - target_probability) < 0.01


def test_skimming_is_less_sensitive_than_penetration():
    """Skimming must have a lower price sensitivity than penetration
    (flatter curve, less reactive to the gap)."""
    calibrated = calibrate_strategies()

    assert calibrated["skimming"] < calibrated["standard"] < calibrated["penetration"]