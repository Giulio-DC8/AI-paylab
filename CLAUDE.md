# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`agent-paylab` is a local, offline sandbox for prototyping the *decision logic* of an AI agent that pays — protocol selection, offer comparison, price negotiation, and cryptographically signed receipts — without touching real payment rails, accounts, or API keys. Every protocol is mocked; there are no network calls except the optional Gemini-based AI negotiation path.

## Commands

```bash
pip install -e .              # install (editable)
pip install -e ".[ai]"        # + google-genai, needed for negotiate-and-choose / ai_demo.py
pip install -e ".[dev]"       # + pytest

pytest tests/ -v               # run all tests (33)
pytest tests/test_negotiation.py -v          # run one test file
pytest tests/test_negotiation.py::test_negotiate_produces_a_coherent_winner -v  # single test

python benchmarks/negotiation_bench.py  # reproduce docs/benchmarks.md

paylab simulate --protocol x402 --merchant Amazon --amount 500
paylab auto --merchant Amazon --amount 500
paylab compare --offers offers.json
paylab negotiate --sellers sellers.json --max-rounds 30 [--lambda-time L]
paylab negotiate-and-choose --sellers sellers_350.json --preferences "..." --top-n 5   # requires GEMINI_API_KEY
paylab stream --protocol lightning_l402 --cost-per-request 0.0001 --request-count 1000
paylab stream --protocol web_monetization --rate-per-second 0.001 --duration-seconds 30
paylab check-access --merchant WeatherAPI --credit-balance 10.0 --request-cost 0.01
```

There is no lint/build step beyond `pytest`.

## Architecture

**`core/cli.py`** is the single entry point (`paylab` console script) — a thin argparse dispatcher with one subcommand per feature, delegating everything to `core/router.py` (`simulate`, `auto`, `compare`), `core/negotiation.py` (`negotiate`), `core/buyer.py` (`negotiate-and-choose`), or the `protocols/*` modules directly (`stream`, `check-access`, which don't fit `router.py`'s dispatch contract — see below).

**`protocols/<name>/mock.py`** — one module per payment protocol, no shared base class. Each exposes a `pay(merchant, amount, budget_limit=1000.0, ...)` (or protocol-specific equivalent) returning a result dict with `transaction_id`, `protocol`, `merchant`, `amount`, `status` (`APPROVED`/`REJECTED`), `reason`, `fee`, `timestamp`, plus protocol-specific fields (`mandate_id`, `agent_token`, `agent_credential`, `zone`, `currency`, `macaroon`, ...). Three protocol families with genuinely different interfaces:
- **Six single-transaction ("one-shot") protocols** (`x402`, `mpp`, `visatap`, `mastercardpay`, `payforcrawl`, `ap2`): fixed `amount`, used by `simulate`/`auto`/`compare`/`negotiate`.
- **Two per-unit/streaming protocols** (`lightning_l402`, `web_monetization`): cost accumulates over requests or time (`cost_per_request × request_count`, `rate_per_second × duration_seconds`); routed only through `paylab stream`, never through `auto`/`compare` (different function signature — no single `amount`).
- **One pre-paid access-control protocol** (`api_key_quota`): no negotiation at all, just a validity/credit/rate-limit check returning realistic HTTP status codes (200/401/403/429); routed only through `paylab check-access`.

`ap2` is exposed in `simulate` but deliberately excluded from `core/router.py`'s `PROTOCOL_FUNCTIONS` (and thus from `auto`/`compare`) — it authorizes a payment (requires `mandate_signed`) rather than executing one, so it doesn't fit the `pay(merchant, amount, budget_limit)` contract the router assumes.

**`core/router.py`** — `choose_and_pay()` tries every protocol in `PROTOCOL_FUNCTIONS` and picks the lowest fee among approved; `choose_best_offer()` compares heterogeneous `{merchant, amount, protocol}` offers by total cost (amount + fee); `simulate(protocol, merchant, amount)` runs one payment on a named protocol (backs `paylab simulate`). `simulate()` covers 6 protocols (including `ap2`) via its own if/elif, deliberately *not* `PROTOCOL_FUNCTIONS` (which only has 5 and excludes `ap2` on purpose — see below) — don't try to unify the two without checking why `ap2` is excluded from one and not the other. Raises `UnsupportedProtocolError` (not `KeyError`/`NameError`) for an unsupported protocol, in both `choose_best_offer()` and `simulate()`.

**`core/negotiation.py`** — the deterministic negotiation engine. `Seller.counter_offer()` doesn't apply a fixed discount step; each round it generates 20 candidate prices between its current price and its own `min_price` floor and picks whichever maximizes **expected value**: `P_win(price) × margin`, where `P_win` is a logistic function of the price gap to the competitor (`estimate_win_probability`). Full derivation, the calibration methodology, and the rate-scale rounding-precision bug are in [`docs/negotiation.md`](docs/negotiation.md) — read it before touching the EV math. Key things not obvious from the code alone:
- Per-strategy sensitivity (`price_elasticity_belief` for `skimming`/`standard`/`penetration`) is *not* hand-picked — it's solved for by `core/calibration.py` via `scipy.optimize.minimize_scalar` against target win-probabilities at a 5% price gap, computed once at import time (`STRATEGY_PRICE_ELASTICITY_BELIEF = calibrate_strategies()`). Change the targets in `calibrate_strategies()` and negotiation behavior updates automatically.
- Prices are rounded to **8 decimals**, not 2 — needed so per-request/per-second rate negotiation (e.g. `0.00012`) doesn't collapse to zero.
- Optional `lambda_time` parameter adds a time-value-of-waiting penalty (`EV(p,t) = P_win·margin − λ·t·(1−P_win)·margin`) that's algebraically zero at the default `lambda_time=0.0`, so it never changes default behavior.
- The engine is agnostic to price scale (total amount vs. per-unit rate) by design — the same `Seller`/`negotiate()` handles both, since only the relative price gap matters. One-shot and rate-based sellers are never mixed in the same negotiation.

**`core/market_protocol.py`** — the stable, typed API layer over `negotiate()`. `MarketProtocol` is a minimal ABC (`name`, `run(sellers, **kwargs)`) meant to let future market mechanisms (a reverse auction, an RFQ, ...) live alongside `NegotiationProtocol` without touching it. `NegotiationProtocol` is a pure wrapper — `.run(sellers, max_rounds=5)` calls `negotiate()` unchanged and returns a `NegotiationResult` dataclass (`.winner`, `.history: list[NegotiationRound]`) instead of the raw dict `negotiate()` itself still returns. `negotiate()`'s dict-returning contract is untouched and will stay that way — this module is additive, not a replacement. See [`docs/protocol-spec.md`](docs/protocol-spec.md) for the protocol-level (roles/message-flow) description this class implements, as opposed to [`docs/negotiation.md`](docs/negotiation.md)'s math.

**`core/ai_agent.py`** / **`core/buyer.py`** — an alternative, LLM-based (Gemini) negotiation path, orthogonal to the deterministic engine above. `negotiate_and_choose()` runs the deterministic engine across *all* sellers first (cheap, scales to hundreds), then hands only the cheapest `top_n` finalists to `ai_buyer_choice()` for a final natural-language-preference-based pick — never calls the LLM once per seller. `Buyer` (same module) is a stateful wrapper around `negotiate_and_choose()` (`Buyer(preferences=..., top_n=5, max_rounds=30).choose(sellers)`) — same delegate, same limitations, just holding the settings instead of passing them every call. The `google-genai` import is lazy (inside `_get_client()`), so nothing outside this AI path requires the package or `GEMINI_API_KEY` to be installed/set; this is why `google-genai` is an optional dependency (`pip install -e ".[ai]"`) rather than a hard one. Not reproducible and not unit-tested (by nature of calling an LLM) — treat as a demo, not something other code should depend on.

**`receipt/`** — every payment result can be turned into a receipt (`create_receipt()`) signed with a real Ed25519 keypair (`cryptography` library, not a bare hash) and checked with `verify_receipt()`. Keys are generated lazily on first use and gitignored (`receipt/private_key.pem`, `receipt/public_key.pem` — both machine-local, never committed). `receipt/keys.py` raises `IncompleteKeyPairError` if only one of the two key files exists, rather than silently regenerating and invalidating every previously-issued receipt.

## Adding a new protocol

1. `protocols/<name>/mock.py` with a `pay(...)` (or equivalent) returning a result dict with at minimum `transaction_id`, `protocol`, `merchant`, `amount`, `status`, `reason`, `fee`, `timestamp` — `amount` is required for `create_receipt()` to work.
2. `protocols/<name>/__init__.py` (empty).
3. Add the package to `[tool.setuptools] packages` in `pyproject.toml` — this has been missed repeatedly when adding protocols; a non-editable `pip install` silently drops the subpackage otherwise.
4. Wire into `core/cli.py` (new subcommand or `--protocol` choice) and, if it fits the `pay(merchant, amount, budget_limit)` contract, into `core/router.py`'s `PROTOCOL_FUNCTIONS`.
5. Add a `tests/test_<name>.py`.
