"""
Scaffolding for PayLab's market-protocol family.

MarketProtocol is the abstract base every market mechanism implements:
NegotiationProtocol today (the reference implementation), and in the
future siblings such as ReverseAuctionProtocol, EnglishAuctionProtocol,
RFQProtocol, or DoubleAuctionProtocol.

NegotiationProtocol wraps core.negotiation.negotiate() unchanged - it
adds no logic of its own, only a typed result. The math lives entirely
in core/negotiation.py (see docs/negotiation.md); this module never
recomputes or alters it.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass

from core.negotiation import Seller, negotiate


@dataclass
class NegotiationRound:
    """One entry of negotiation history: the round number and every seller's price at that point."""
    round: int
    prices: dict


@dataclass
class NegotiationResult:
    """Typed result of a protocol run: the winning Seller and the full round-by-round history."""
    winner: Seller
    history: list[NegotiationRound]


class MarketProtocol(ABC):
    """
    Base class for a market mechanism run between a Buyer and a pool of Sellers.

    Every mechanism implements the same `run(sellers, **kwargs)` interface,
    so different protocols can be swapped or compared without changing
    calling code.
    """
    name: str = "market_protocol"

    @abstractmethod
    def run(self, sellers, **kwargs):
        """Runs the mechanism against `sellers` and returns its result."""
        raise NotImplementedError


class NegotiationProtocol(MarketProtocol):
    """
    PayLab's Expected Value Negotiation Protocol - the reference
    implementation of MarketProtocol.

    See docs/protocol-spec.md for the protocol description (roles,
    message flow, properties) and docs/negotiation.md for the math.
    """
    name = "negotiation"

    def run(self, sellers: list[Seller], max_rounds: int = 5) -> NegotiationResult:
        outcome = negotiate(sellers, max_rounds=max_rounds)
        history = [NegotiationRound(round=r["round"], prices=r["prices"]) for r in outcome["history"]]
        return NegotiationResult(winner=outcome["winner"], history=history)
