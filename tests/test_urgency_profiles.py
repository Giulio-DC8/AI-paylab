from core.negotiation import Seller, negotiate
from core.cli import LAMBDA_TIME_PROFILES


def test_urgency_profiles_map_to_expected_lambda_values():
    assert LAMBDA_TIME_PROFILES["patient"] == 0.0
    assert LAMBDA_TIME_PROFILES["moderate"] == 0.1
    assert LAMBDA_TIME_PROFILES["urgent"] == 0.5


def test_mixed_lambda_time_sellers_each_use_their_own_value():
    """Sellers with an explicit lambda_time must each behave according
    to their own value, not a single global one."""
    patient = Seller(name="Patient", starting_price=1000, min_margin=0.3, strategy="skimming", lambda_time=0.0)
    urgent = Seller(name="Urgent", starting_price=1000, min_margin=0.3, strategy="skimming", lambda_time=0.8)

    outcome = negotiate([patient, urgent, Seller(name="Target", starting_price=700, min_margin=0.05)], max_rounds=20)

    assert patient.current_price != urgent.current_price