from core.negotiation import Seller, negotiate
from core.market_protocol import NegotiationProtocol, NegotiationResult, NegotiationRound
from core.router import simulate
from protocols.x402.mock import pay as pay_x402
from protocols.ap2.mock import pay as pay_ap2
from protocols.mpp.mock import pay as pay_mpp
from protocols.visatap.mock import pay as pay_visatap
from protocols.mastercardpay.mock import pay as pay_mastercardpay
from protocols.payforcrawl.mock import pay as pay_payforcrawl


def _make_sellers():
    return [
        Seller(name="A", starting_price=900, min_margin=0.1, strategy="skimming"),
        Seller(name="B", starting_price=950, min_margin=0.15, strategy="penetration"),
    ]


def test_negotiation_protocol_matches_free_function():
    """NegotiationProtocol.run() must be a pure wrapper: same winner and
    the same round-by-round history as calling negotiate() directly on
    an equivalent, freshly-constructed set of sellers."""
    direct_outcome = negotiate(_make_sellers(), max_rounds=10)
    wrapped_result = NegotiationProtocol().run(_make_sellers(), max_rounds=10)

    assert isinstance(wrapped_result, NegotiationResult)
    assert wrapped_result.winner.name == direct_outcome["winner"].name
    assert wrapped_result.winner.current_price == direct_outcome["winner"].current_price

    assert len(wrapped_result.history) == len(direct_outcome["history"])
    for wrapped_round, direct_round in zip(wrapped_result.history, direct_outcome["history"]):
        assert isinstance(wrapped_round, NegotiationRound)
        assert wrapped_round.round == direct_round["round"]
        assert wrapped_round.prices == direct_round["prices"]


def test_simulate_matches_direct_protocol_call():
    """router.simulate() must be a pure dispatcher: for every one-shot
    protocol, it must return the exact same result as calling that
    protocol's pay() function directly, aside from fields that are
    inherently random on every call (transaction_id, timestamp, and
    the protocol-specific token/credential fields)."""
    direct_functions = {
        "x402": pay_x402,
        "ap2": pay_ap2,
        "mpp": pay_mpp,
        "visatap": pay_visatap,
        "mastercardpay": pay_mastercardpay,
        "payforcrawl": pay_payforcrawl,
    }
    volatile_keys = {"transaction_id", "timestamp", "mandate_id", "agent_token", "agent_credential"}

    for protocol, pay_fn in direct_functions.items():
        via_simulate = simulate(protocol=protocol, merchant="TestMerchant", amount=500)
        direct = pay_fn(merchant="TestMerchant", amount=500)

        via_simulate_stable = {k: v for k, v in via_simulate.items() if k not in volatile_keys}
        direct_stable = {k: v for k, v in direct.items() if k not in volatile_keys}
        assert via_simulate_stable == direct_stable, f"mismatch for protocol={protocol}"
