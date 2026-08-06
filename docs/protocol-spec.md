# PayLab Protocol Specification

This document describes PayLab's **Expected Value Negotiation Protocol** at the level of roles, messages, and guarantees — independent of Python, so it can be reimplemented in any language. For the underlying formulas, their derivation, and worked numeric examples, see [`negotiation.md`](negotiation.md). For measured performance, see [`benchmarks.md`](benchmarks.md).

## 1. Architecture

Two roles participate in a negotiation:

- **Buyer** — a passive coordinator. It doesn't set prices or negotiate on its own behalf; it runs the protocol loop, broadcasts the current best price each round, and declares a winner when the round terminates. In code: the `negotiate()` loop (wrapped by `NegotiationProtocol`).
- **Seller** — an active participant with private state: a starting price, a floor price (`min_price`) below which it will never go, and a pricing strategy that determines how aggressively it reacts to competition. Each `Seller` decides independently, using only its own numbers and the single price the Buyer broadcasts.

No Seller ever negotiates directly with another Seller, and no Seller knows any other Seller's identity, strategy, or floor price — only the one number the Buyer publishes each round: the current best price in the pool.

This asymmetry (one coordinator, many independent decision-makers, no peer-to-peer information) is what `MarketProtocol` (`core/market_protocol.py`) generalizes: a future `ReverseAuctionProtocol`, `EnglishAuctionProtocol`, `RFQProtocol`, or `DoubleAuctionProtocol` would follow the same "Buyer runs the loop, Sellers react independently" shape, or a deliberately different one — that's the point of the abstraction, see §7.

## 2. Roles in detail

### Buyer

Responsibilities:
1. Hold the pool of Sellers to negotiate.
2. Each round, compute the current best (lowest) price across all Sellers and broadcast only that number.
3. Ask every Seller priced above that number whether it wants to counter-offer.
4. Repeat until a full round passes with no Seller discounting, or a round budget (`max_rounds`) is exhausted.
5. Declare the Seller with the lowest final price as the winner.

The Buyer never inspects a Seller's internal state (floor price, strategy, sensitivity) and never picks a price on a Seller's behalf — it only relays the one number every Seller needs to react.

### Seller

Responsibilities:
1. Hold private state: current price, floor price (fixed at creation, see [`negotiation.md` §4](negotiation.md#4-margin)), and a strategy-derived price sensitivity.
2. On being asked to react to a competitor price, evaluate whether discounting improves its **expected value** — win probability times remaining margin, optionally reduced by a time-cost penalty (see [`negotiation.md` §5–6](negotiation.md#5-expected-value-base-case-no-time-cost)) — compared to holding its current price.
3. Never propose a price below its own floor, under any pressure.
4. Report only whether it discounted (a boolean) — the Buyer doesn't need or receive the Seller's reasoning.

A Seller's decision is a pure function of its own state and the single competitor price it's given. Two Sellers with identical parameters given the same competitor price make identical decisions — there is no hidden randomness in the core protocol (the AI-assisted `Buyer`/`ai_agent` path is a separate, explicitly non-deterministic alternative — see §7 and [`negotiation.md`](negotiation.md)).

## 3. Message flow

```
                          ┌─────────┐
                          │  Buyer  │
                          └────┬────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │  round t = 1, 2, ... until stop condition    │
        │                       │                       │
        │   1. best_price = min(price across Sellers)  │
        │                       │                       │
        │        broadcast best_price to every Seller  │
        │        priced above it (no other data leaks) │
        │            │          │          │            │
        │            ▼          ▼          ▼            │
        │       ┌────────┐ ┌────────┐ ┌────────┐        │
        │       │Seller A│ │Seller B│ │Seller C│  ...    │
        │       └───┬────┘ └───┬────┘ └───┬────┘        │
        │           │          │          │              │
        │   each independently evaluates candidate        │
        │   prices against its OWN floor price and        │
        │   strategy, replies "discounted: yes/no"        │
        │           │          │          │              │
        │            ▼          ▼          ▼            │
        │   2. record every Seller's price for round t   │
        │   3. if nobody discounted this round: STOP      │
        └──────────────────────┼──────────────────────┘
                               │
                   winner = Seller with lowest final price
```

No Seller ever sees another Seller's identity, price, or strategy — only the single `best_price` number, once per round.

## 4. Protocol loop (pseudocode)

```
function negotiate(sellers, max_rounds):
    history = [ record(round=0, prices=current price of every seller) ]

    for t in 1..max_rounds:
        best_price = min(seller.current_price for seller in sellers)
        any_discount = false

        for seller in sellers:
            if seller.current_price > best_price:
                discounted = seller.counter_offer(best_price, round=t)
                any_discount = any_discount or discounted

        history.append(record(round=t, prices=current price of every seller))

        if not any_discount:
            break

    winner = seller with minimum current_price
    return { winner, history }

function seller.counter_offer(competitor_price, round):
    if current_price <= min_price:
        return false   # already at the floor, nothing to evaluate

    best_price = current_price
    best_value = expected_value(current_price, competitor_price, round)

    for each of 20 candidate prices between current_price and min_price:
        value = expected_value(candidate, competitor_price, round)
        if value > best_value:
            best_value, best_price = value, candidate

    if best_price < current_price:
        current_price = best_price
        return true
    return false
```

`expected_value(price, competitor_price, round)` is the economic core of the protocol — see [`negotiation.md`](negotiation.md) for its exact formula, the logistic win-probability model behind it, and how the per-strategy sensitivity is calibrated.

## 5. Properties

These hold for every implementation of this protocol, by construction of the loop above — not just empirically observed in the reference implementation:

- **Floor safety.** No Seller's price is ever set below its own `min_price` in any round, regardless of competition or time pressure. Candidate prices are only ever generated in the closed range `[min_price, current_price]`.
- **Monotonicity.** A Seller's price never increases during a negotiation — it only ever holds or decreases.
- **Bounded rounds.** The loop runs at most `max_rounds` rounds; it may terminate earlier if a full round produces no discounts.
- **Independence.** A Seller's decision each round depends only on its own state and the single `competitor_price` value it receives that round — never on any other Seller's identity or on which Seller currently holds `best_price`.
- **Single-participant no-op.** With exactly one Seller in the pool, `best_price` always equals that Seller's own price, so it's never asked to react — the negotiation ends immediately with that Seller as winner, unchanged.
- **Winner correctness.** The declared winner always has the minimum `current_price` among all Sellers at the end of the loop — by definition, not by search.

## 6. Convergence

"Convergence" here means the loop reaches the early-exit condition (a full round with no discounts) before exhausting `max_rounds`.

- Convergence is **not guaranteed for every parameter combination** — it depends on the interaction between how much margin advantage a Seller has and how steeply its strategy reacts to price gaps (see [`negotiation.md`](negotiation.md)'s two side-by-side experiments where an identical floor-price advantage produces a win in one configuration and a loss in another). A documented case (time-cost penalty with a very small `lambda_time`) fails to converge within 30 rounds in the reference implementation.
- Convergence **has been empirically observed** at the scales this project has tested: 2, 15, and 350 Sellers, and is exercised directly by `tests/test_negotiation.py`'s convergence and hundred-Seller tests (`test_negotiation_converges_for_random_seller_pools`, `test_negotiate_scales_to_hundreds_of_sellers`) and by the reproducible measurements in [`benchmarks.md`](benchmarks.md).
- A caller that needs a hard guarantee should choose `max_rounds` generously and treat "still discounting when the budget runs out" as a valid, observable outcome, not an error — the loop always terminates (it's bounded by construction), it just may terminate without every Seller having settled.

## 7. Extensibility

`core/market_protocol.py` defines `MarketProtocol`, a minimal base every market mechanism implements:

```python
class MarketProtocol(ABC):
    name: str
    def run(self, sellers, **kwargs): ...
```

`NegotiationProtocol` (this document's protocol) is the first and, for now, only concrete implementation. The interface exists so that future mechanisms with a genuinely different message flow can be added as siblings without touching `NegotiationProtocol` or the math it wraps:

- **`ReverseAuctionProtocol`** — sellers submit sealed bids instead of reacting to a broadcast price; no round-by-round reaction loop.
- **`EnglishAuctionProtocol`** — price rises (or falls, for a descending/Dutch variant) publicly until only one bidder remains.
- **`RFQProtocol`** — the buyer solicits quotes for a specific request and picks one, without an iterative discount loop at all.
- **`DoubleAuctionProtocol`** — both buyers and sellers submit prices, matched by an order-book-style mechanism.

None of these are implemented yet. Adding one means: a new class implementing `MarketProtocol.run()`, its own module (mirroring `core/market_protocol.py`'s layout), and its own math reference document (mirroring `negotiation.md`) — without modifying `core/negotiation.py`, `NegotiationProtocol`, or any of the protocols already frozen by this specification.

The `AI-assisted` path (`core/ai_agent.py`, `core/buyer.py`'s `Buyer` class) is not an alternative `MarketProtocol` implementation — it's an orthogonal decision-maker that can sit *after* a `NegotiationProtocol` run (or any future protocol's run) to make a final, natural-language-preference-based pick among the cheapest finalists. It is explicitly non-deterministic and outside the guarantees in §5.
