# agent-paylab

**How do you test an AI agent that needs to pay?**

Today that usually means API keys, merchant accounts, wallets, and sandbox environments, often real money, just to prototype logic. `agent-paylab` lets you build and test that decision logic entirely offline: simulate payment protocols, compare offers, negotiate prices, and generate cryptographically signed receipts, without touching a real payment rail.

```
AI Agent
   │
   ├──────────────────────────┐
   ▼                          ▼               
Compare offers        Focus on one seller    
   │                          │               
   ▼                          ▼               
Negotiate             (skip straight to)       
   │                          │               
   └──────────────────────────┐
                              ▼
      Choose protocol / check access / per-request billing
                              │
                              ▼
                       Mock payment
                             │
                             ▼
                    Signed receipt (Ed25519)
```

## Why this project exists

While exploring agentic commerce protocols (x402, AP2, MPP, and others), it became clear that everyone was building payment *rails* — but almost nothing existed to prototype the *decision logic* of an agent locally: which seller to pick, how to negotiate, when a discount is actually worth it. `agent-paylab` was built to fill that gap.

The protocols are the medium. **The real subject is decision intelligence for agentic commerce** — how an agent picks a seller, negotiates, and proves what it decided, independent of which rail eventually moves the money.

## agent-paylab vs. the real thing

| | Real payment rails | agent-paylab |
|---|---|---|
| Needs accounts | ✅ | ❌ |
| Needs API keys | ✅ | ❌ |
| Spends real money | ✅ | ❌ |
| Sandbox available | Sometimes | Always |
| Cryptographic receipts | Varies | ✅ (Ed25519) |
| Multi-protocol out of the box | ❌ | ✅ (9 protocols) |

## See it in action

```
$ paylab negotiate --sellers sellers.json

--- Negotiation history ---
Round 0: {'Lufthansa': 900, 'Emirates': 950}
Round 1: {'Lufthansa': 900, 'Emirates': 878.75}
Round 2: {'Lufthansa': 900, 'Emirates': 878.75}

--- Winner: Emirates at 878.75 ---
```

Two sellers, two independent pricing strategies, negotiating by weighing expected value at every candidate price — not a fixed discount step. This is the part most payment protocol demos don't show: not *how* an agent pays, but *how it decides who to pay*. Full math and calibration details: [`docs/negotiation.md`](docs/negotiation.md).

`agent-paylab` doesn't compete with x402, AP2, MPP, or any other payment protocol — it's a development tool for the logic that decides *before* any of them get called.

## Install

```bash
git clone <repo-url>
cd agent-paylab
pip install -e .
```

Requires Python 3.11+.

## Quickstart

Simulate a single payment on a specific protocol:
```bash
paylab simulate --protocol x402 --merchant Amazon --amount 500
```

Let the agent pick the cheapest protocol automatically:
```bash
paylab auto --merchant Amazon --amount 500
```

Compare offers from different sellers using different payment methods, and pick the lowest total cost:
```bash
paylab compare --offers offers.json
```
```json
[
  {"merchant": "Lufthansa", "amount": 950, "protocol": "visatap"},
  {"merchant": "Emirates", "amount": 900, "protocol": "x402"}
]
```

Let sellers negotiate against each other by expected value, until nobody can improve further:
```bash
paylab negotiate --sellers sellers.json --max-rounds 30
```
```json
[
  {"name": "Lufthansa", "starting_price": 900, "min_margin": 0.1, "strategy": "skimming"},
  {"name": "Emirates", "starting_price": 950, "min_margin": 0.15, "strategy": "penetration"}
]
```

Negotiate across many sellers, then let an LLM pick the final winner among the top finalists based on stated preferences:
```bash
paylab negotiate-and-choose --sellers sellers_350.json --preferences "prefer stable pricing strategies, avoid aggressive discounters" --top-n 5
```
Requires `GEMINI_API_KEY` set in your environment.

Every payment simulation produces a **receipt signed with Ed25519** (real public/private key cryptography, not a bare hash), tamper with any field after signing, and verification fails.

## Commands

| Command | What it does |
|---|---|
| `paylab simulate --protocol X --merchant M --amount N` | Simulate a single payment on the protocol you choose |
| `paylab auto --merchant M --amount N` | Try all execution protocols, pick the one with the lowest fee |
| `paylab compare --offers file.json` | Compare multiple seller/protocol offers, pick the lowest total cost (price + fee) |
| `paylab negotiate --sellers file.json [--max-rounds N] [--lambda-time L]` | Run a multi-round negotiation between sellers, each maximizing expected value at every round (default: 5 rounds, no time cost) |
| `paylab negotiate-and-choose --sellers file.json --preferences "..." [--top-n N] [--max-rounds N]` | Negotiate across all sellers deterministically, then let an LLM choose among the top N finalists based on natural-language preferences |
| `paylab stream --protocol X --merchant M ...` | Simulate a per-request (Lightning L402) or continuous-streaming (Web Monetization) micropayment |
| `paylab check-access --merchant M ...` | Check API key/quota access (traditional pre-paid credential model — no real-time negotiation, only a validity/credit check) |
| `paylab negotiate --sellers file.json [--max-rounds N] [--lambda-time L | --urgency patient/moderate/urgent]` | Run a multi-round negotiation between sellers, each maximizing expected value at every round (default: 5 rounds, no time cost) |

## Negotiation model

Three documents, three roles:
- [`docs/protocol-spec.md`](docs/protocol-spec.md) — the protocol itself, language-agnostic: Buyer/Seller roles, message flow, properties (floor safety, monotonicity, bounded rounds), convergence, and how future market mechanisms (`ReverseAuctionProtocol`, `EnglishAuctionProtocol`, ...) plug into the same `MarketProtocol` interface.
- [`docs/negotiation.md`](docs/negotiation.md) — the math: the expected-value formula, why it's a logistic function, how `core/calibration.py` derives the parameters with `scipy.optimize` instead of hand-picking them, the numerical precision bug that surfaced when extending this to rate-based (per-request) negotiation, the optional time-value-of-waiting cost (`--lambda-time` or the `--urgency patient/moderate/urgent` shortcut, settable per-seller in JSON), and two documented edge cases (non-monotonic price, floor saturation) worth knowing before assuming "more urgency = better price."
- [`docs/benchmarks.md`](docs/benchmarks.md) — reproducible time/memory/round-count measurements from 2 to 350 sellers.

### Stable API

Besides the CLI, the negotiation engine is usable as a library, at two levels:
- **Raw**: `from core.negotiation import Seller, negotiate` — the free functions, unchanged since before this API layer existed.
- **Wrapped**: `from core.market_protocol import NegotiationProtocol` — `NegotiationProtocol().run(sellers, max_rounds=5)` returns a typed `NegotiationResult` (`.winner`, `.history`) instead of a raw dict. This is the reference implementation of `MarketProtocol`, the interface future market mechanisms will share (see `docs/protocol-spec.md` §7).
- Payments are similarly usable as a library via `core.router.simulate(protocol, merchant, amount)` (the same dispatch `paylab simulate` uses) and the AI-assisted buyer via `core.buyer.Buyer(preferences=...).choose(sellers)`.

None of this changes what `negotiate()`, `Seller`, or the CLI already did — it's an additive, typed layer on top.

## AI-assisted decisions (experimental)

`core/ai_agent.py` (Gemini API) shows an alternative to the deterministic engine: a seller and a buyer that reason about the same kind of decision in natural language instead of computing expected value or comparing raw totals. `core/buyer.py` (`negotiate_and_choose()`) wires this into the main pipeline: it runs the deterministic negotiation across *all* sellers first (free, fast, scales to hundreds), then hands only the top N finalists to the AI for a final decision, instead of calling an LLM once per seller, which would be slow, costly, and unnecessary since the price-based part is already handled deterministically. Run `python examples/ai_demo.py` (requires `GEMINI_API_KEY`) for a standalone look at the seller/buyer reasoning, or use `paylab negotiate-and-choose` for the full pipeline.

**Known limitation:** unlike the deterministic engine, this is not reproducible and not covered by tests. Calling the same scenario multiple times can yield different (though generally still valid) outcomes, and occasionally verbose or self-contradictory reasoning. `temperature=0.0` is set on all calls, which resolved most of this in testing (3/3 clean runs after tuning), plus a code-level fallback that guarantees a valid `chosen_merchant` is always returned even if the model fails to pick one, but full determinism isn't something an LLM call can guarantee the way the math-based engine can. Treat this module as a demo of where the project could go, not as something to depend on.

## Buyer component

`core/buyer.py`'s `negotiate_and_choose(sellers, buyer_preferences, top_n=5, max_rounds=30)` is meant to be imported directly by developers building their own buyer agent, not just used through the CLI wrapper above. `Buyer` (same module) is a thin stateful wrapper around it — `Buyer(preferences=..., top_n=5, max_rounds=30).choose(sellers)` — for callers who'd rather configure once and call repeatedly. Both inherit the same AI-path limitation: non-deterministic, requires `GEMINI_API_KEY`, not covered by automated tests.

## Protocols supported (all mocked)

Six single-transaction ("one-shot") protocols:

| Protocol | What it represents | Notable field |
|---|---|---|
| `x402` | Direct payment rail over HTTP 402 (stablecoin-native) | — |
| `mpp` | Card/fiat rail with pre-authorized sessions | `currency` |
| `visatap` | Agent recognition inside the Visa card network | `agent_token` |
| `mastercardpay` | Agent recognition inside the Mastercard network | `agent_credential` |
| `payforcrawl` | Cloudflare Pay per Crawl — access to content/resources, not e-commerce | `zone` |
| `ap2` | Authorization framework (mandate-based), not an execution rail | `mandate_id` |

Plus two per-unit / continuous-streaming protocols, conceptually different from the six above (no single fixed amount — cost accumulates per request or per second):

| Protocol | What it represents | Command |
|---|---|---|
| `lightning_l402` | Lightning Network L402: per-request micropayments bundling auth + payment via a macaroon token | `paylab stream --protocol lightning_l402 --cost-per-request 0.0001 --request-count 1000` |
| `web_monetization` | W3C Web Monetization / Interledger Protocol: continuous background payment stream while a resource is consumed | `paylab stream --protocol web_monetization --rate-per-second 0.001 --duration-seconds 30` |

Plus one traditional pre-paid access-control model, conceptually different from both categories above (payment already happened out-of-band — the request only checks validity/credit, it never negotiates or decides anything):

| Protocol | What it represents | Command |
|---|---|---|
| `api_key_quota` | Traditional API Key / OAuth model: account and credit set up beforehand; each request just checks key validity, remaining credit, and rate limits (HTTP 200/401/403/429) | `paylab check-access --merchant WeatherAPI --credit-balance 10.0 --request-cost 0.01` |

**Design note:** every mock captures only the core mechanic of the real protocol it represents, not the full specification. `x402`, `mpp`, `visatap`, `mastercardpay`, and `payforcrawl` are treated here as interchangeable execution rails for simplicity; in reality some of them (e.g. Visa card payments) are implemented as *methods within* MPP rather than fully separate protocols. `ap2` is currently exposed as a peer protocol in `simulate` for consistency, even though conceptually it authorizes a payment rather than executing one — it's excluded from `auto` and `compare` for that reason. `lightning_l402` and `web_monetization` are kept separate from `simulate`/`auto`/`compare`/`negotiate` on purpose: those commands assume a single fixed `amount`, while streaming protocols accumulate cost over requests or time — a genuinely different interface, not just another protocol name. A cleaner `paylab authorize` step for `ap2` is planned (see Roadmap).

## Receipts

Every simulated payment, approved or rejected, produces a receipt signed with **Ed25519**:
- `receipt/generator.py` — `create_receipt()` / `verify_receipt()`
- `receipt/keys.py` — key generation and loading (auto-generated on first run; raises `IncompleteKeyPairError` if only one of the two key files is present, instead of silently regenerating and invalidating old receipts)

The private key (`receipt/private_key.pem`) is generated locally on first use and never leaves your machine — it's excluded from version control via `.gitignore`. Only the public key is needed to verify a receipt.

## Project structure

```
agent-paylab/
├── core/
│   ├── cli.py             # command-line entry point (all commands)
│   ├── router.py          # choose_and_pay(), choose_best_offer(), simulate()
│   ├── negotiation.py     # Seller class (expected-value based), negotiate() - frozen reference math
│   ├── market_protocol.py # MarketProtocol base + NegotiationProtocol wrapper, typed results
│   ├── calibration.py     # scipy-based calibration of negotiation parameters
│   ├── buyer.py           # negotiate_and_choose(), Buyer class - deterministic + AI pipeline
│   └── ai_agent.py        # experimental LLM-based decision engine
├── protocols/
│   ├── x402/mock.py
│   ├── ap2/mock.py
│   ├── mpp/mock.py
│   ├── visatap/mock.py
│   ├── mastercardpay/mock.py
│   ├── payforcrawl/mock.py
│   ├── lightning_l402/mock.py     # per-request payments
│   ├── web_monetization/mock.py   # continuous streaming payments
│   └── api_key_quota/mock.py      # traditional pre-paid API key/quota access
├── receipt/
│   ├── generator.py
│   └── keys.py
├── tests/
│   ├── test_receipt.py             # Ed25519 signing/verification
│   ├── test_negotiation.py         # expected-value engine, win probability, Seller, protocol invariants
│   ├── test_market_protocol.py     # NegotiationProtocol/simulate() wrapper-equivalence
│   ├── test_calibration.py         # scipy-based parameter calibration
│   ├── test_router.py              # protocol selection, offer comparison, error handling
│   ├── test_rate_negotiation.py    # negotiation engine at per-request/per-second rate scale
│   ├── test_streaming_protocols.py # lightning_l402, web_monetization
│   ├── test_api_key_quota.py       # api_key_quota (HTTP 200/401/403/429)
│   └── test_time_cost.py           # time-discounted negotiation (lambda_time)
├── examples/
│   ├── generate_sellers.py   # generate random seller pools for scale testing
│   └── ai_demo.py            # standalone ai_agent.py demo
├── benchmarks/
│   └── negotiation_bench.py  # reproducible time/memory/round-count measurements
├── docs/
│   ├── protocol-spec.md      # language-agnostic protocol spec (roles, flow, properties, extensibility)
│   ├── negotiation.md        # math reference (formulas, calibration, worked examples)
│   └── benchmarks.md         # measured results
└── pyproject.toml
```
## Testing

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

35 tests covering receipt signing, the expected-value negotiation engine, parameter calibration, protocol routing/error handling, per-unit/streaming payments, rate-based negotiation, traditional API key/quota access control, time-cost-based negotiation, urgency profiles, and the stable NegotiationProtocol/Buyer/simulate() API surface.

## Roadmap

- Redefine `ap2` as a separate authorization step (`paylab authorize`) that produces a mandate, consumed by `auto`/`compare`/`negotiate`, instead of listing it as a peer execution protocol
- Reflect MPP's real internal structure (Core / Intents / Methods / Extensions) more faithfully, or document the simplification more prominently
- Win probability currently depends only on price gap; could be extended to a feature vector (reputation, delivery time, stock, history) without changing the core expected-value model
- Risk preference: expected value currently assumes risk neutrality (`probability × margin`); a `probability^alpha × margin^beta` formulation would let sellers be modeled as risk-averse, aggressive, or market-share-driven
- Multi-step / non-myopic negotiation (agents that reason about future rounds, not just the current one)
- Cross-negotiation between one-shot and rate-based sellers (e.g. comparing a fixed flight price against a per-request API rate), would require an assumed request/time volume to convert a rate into a comparable total

## License

MIT
