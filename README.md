# AI-paylab 

**Agent-paylab is a local sandbox for prototyping how AI agents pay.** Simulate, compare, and negotiate payments across multiple agentic payment protocols, no real accounts, no API keys, no network calls.

## See it in action

$ paylab negotiate --sellers sellers.json

--- Negotiation history ---
Round 0: {'Lufthansa': 900, 'Emirates': 950}
Round 1: {'Lufthansa': 900, 'Emirates': 878.75}
Round 2: {'Lufthansa': 900, 'Emirates': 878.75}

--- Winner: Emirates at 878.75 ---

Two sellers, two independent pricing strategies, negotiating by weighing expected value, probability of winning × remaining margin, at every candidate price, instead of applying a fixed discount step. Tested up to 350 sellers negotiating at once (see below). This is the part most payment protocol demos don't show: not *how* an agent pays, but *how it decides who to pay*.

`agent-paylab` doesn't compete with x402, AP2, MPP, or any other payment protocol. It's a development tool: a place to prototype the *logic* of an agent that pays, protocol selection, offer comparison, price negotiation, tamper-evident receipts, before wiring anything to a real rail.

## Why

Agentic payment protocols are still fragmented and evolving fast. Testing an agent's payment logic against real infrastructure means real accounts, real keys, and real (if small) money. `agent-paylab` removes that friction entirely, every protocol is mocked, every transaction is local, every receipt is cryptographically real.

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
| `paylab negotiate --sellers file.json [--max-rounds N]` | Run a multi-round negotiation between sellers, each maximizing expected value at every round (default: 5 rounds) |
| `paylab negotiate-and-choose --sellers file.json --preferences "..." [--top-n N] [--max-rounds N]` | Negotiate across all sellers deterministically, then let an LLM choose among the top N finalists based on natural-language preferences |

## Negotiation model

Sellers don't apply a fixed discount. At every round, each `Seller` evaluates a range of candidate prices (from its current price down to its own minimum) and picks the one that maximizes **expected value**: `probability_of_winning(price) × remaining_margin(price)`. Win probability is a logistic function of the price gap to the competitor.

Each `strategy` (`skimming`, `standard`, `penetration`) has its own `price_elasticity_belief`, how much a seller believes discounting improves its odds. These aren't hand-picked: `core/calibration.py` derives them with `scipy.optimize`, targeting a specific win probability at a 5% price gap (skimming stays confident even when pricier; penetration assumes being pricier hurts a lot, so it chases the competitor). Change the targets in `calibrate_strategies()` and the values used by `negotiate()` update automatically — nothing to copy by hand.

Under the hood: `estimate_win_probability(gap, sensitivity) = 1 / (1 + exp(sensitivity * gap))`
— a logistic function, chosen because it naturally gives 0.5 at equal prices and approaches
0 or 1 smoothly as the gap grows. `calibrate_strategies()` inverts this: given a target win
probability at a 5% gap (skimming=40%, standard=25%, penetration=10%), it uses
`scipy.optimize.minimize_scalar` to find the `sensitivity` value that produces it, currently
≈8.11 / 21.97 / 43.94 respectively.

Grounded in real pricing theory (Blythe, *Fondamenti di Marketing*, 2013, ch. 7; LIUC pricing strategy lecture notes) rather than arbitrary rules: `skimming` mirrors market-skimming (patient, protects margin), `penetration` mirrors penetration pricing (aggressive, chases market share, at the real-world risk of a price war if a competitor matches it).

**Scale-tested:** negotiation was tested with 2, 15, and 350 sellers (`examples/generate_sellers.py` generates random seller pools with a fixed seed for reproducibility). It scales without performance issues, 350 sellers converge naturally around round 10, with no code changes needed.

**A note on `--max-rounds`:** the default (5) is enough for small scenarios (2-3 sellers), but with more participants — especially several using `"penetration"` — the negotiation may still be actively converging when the round limit cuts it off. At 15 sellers with 5 rounds, two aggressive sellers were still chasing each other's price down; raising `--max-rounds` to 30 showed they stabilize on their own around round 7 (a genuine price war settling, once neither can improve further), the cutoff, not an unresolved conflict, was why it looked unfinished at the default.

## AI-assisted decisions (experimental)

`core/ai_agent.py` (Gemini API) shows an alternative to the deterministic engine: a seller and a buyer that reason about the same kind of decision in natural language instead of computing expected value or comparing raw totals. `core/buyer.py` (`negotiate_and_choose()`) wires this into the main pipeline: it runs the deterministic negotiation across *all* sellers first (free, fast, scales to hundreds), then hands only the top N finalists to the AI for a final decision — instead of calling an LLM once per seller, which would be slow, costly, and unnecessary since the price-based part is already handled deterministically. Run `python examples/ai_demo.py` (requires `GEMINI_API_KEY`) for a standalone look at the seller/buyer reasoning, or use `paylab negotiate-and-choose` for the full pipeline.

**Known limitation:** unlike the deterministic engine, this is not reproducible and not covered by tests. Calling the same scenario multiple times can yield different (though generally still valid) outcomes, and occasionally verbose or self-contradictory reasoning. `temperature=0.0` is set on all calls, which resolved most of this in testing (3/3 clean runs after tuning), plus a code-level fallback that guarantees a valid `chosen_merchant` is always returned even if the model fails to pick one, but full determinism isn't something an LLM call can guarantee the way the math-based engine can. Treat this module as a demo of where the project could go, not as something to depend on.

## Buyer component

`core/buyer.py`'s `negotiate_and_choose(sellers, buyer_preferences, top_n=5, max_rounds=30)` is meant to be imported directly by developers building their own buyer agent, not just used through the CLI wrapper above.

## Protocols supported (all mocked)

| Protocol | What it represents | Notable field |
|---|---|---|
| `x402` | Direct payment rail over HTTP 402 (stablecoin-native) | — |
| `mpp` | Card/fiat rail with pre-authorized sessions | `currency` |
| `visatap` | Agent recognition inside the Visa card network | `agent_token` |
| `mastercardpay` | Agent recognition inside the Mastercard network | `agent_credential` |
| `payforcrawl` | Cloudflare Pay per Crawl — access to content/resources, not e-commerce | `zone` |
| `ap2` | Authorization framework (mandate-based), not an execution rail | `mandate_id` |

**Design note:** every mock captures only the core mechanic of the real protocol it represents, not the full specification. `x402`, `mpp`, `visatap`, `mastercardpay`, and `payforcrawl` are treated here as interchangeable execution rails for simplicity; in reality some of them (e.g. Visa card payments) are implemented as *methods within* MPP rather than fully separate protocols. `ap2` is currently exposed as a peer protocol in `simulate` for consistency, even though conceptually it authorizes a payment rather than executing one, it's excluded from `auto` and `compare` for that reason. A cleaner `paylab authorize` step is planned (see Roadmap).

## Receipts

Every simulated payment, approved or rejected, produces a receipt signed with **Ed25519**:
- `receipt/generator.py` — `create_receipt()` / `verify_receipt()`
- `receipt/keys.py` — key generation and loading (auto-generated on first run; raises `IncompleteKeyPairError` if only one of the two key files is present, instead of silently regenerating and invalidating old receipts)

The private key (`receipt/private_key.pem`) is generated locally on first use and never leaves your machine, it's excluded from version control via `.gitignore`. Only the public key is needed to verify a receipt.

## Project structure

```
agent-paylab/
├── core/
│   ├── cli.py            # command-line entry point (all commands)
│   ├── router.py         # choose_and_pay(), choose_best_offer()
│   ├── negotiation.py    # Seller class (expected-value based), negotiate()
│   ├── calibration.py    # scipy-based calibration of negotiation parameters
│   ├── buyer.py          # negotiate_and_choose() - deterministic + AI pipeline
│   └── ai_agent.py       # experimental LLM-based decision engine
├── protocols/
│   ├── x402/mock.py
│   ├── ap2/mock.py
│   ├── mpp/mock.py
│   ├── visatap/mock.py
│   ├── mastercardpay/mock.py
│   └── payforcrawl/mock.py
├── receipt/
│   ├── generator.py
│   └── keys.py
├── tests/
│   ├── test_receipt.py       # Ed25519 signing/verification
│   ├── test_negotiation.py   # expected-value engine, win probability, Seller
│   ├── test_calibration.py   # scipy-based parameter calibration
│   └── test_router.py        # protocol selection, offer comparison, error handling
├── examples/
│   ├── generate_sellers.py   # generate random seller pools for scale testing
│   └── ai_demo.py            # standalone ai_agent.py demo
└── pyproject.toml
```
## Testing

```bash
pip install pytest
pytest tests/ -v
```

13 tests covering receipt signing, the expected-value negotiation engine, parameter calibration, and protocol routing/error handling.
## Roadmap

- Redefine `ap2` as a separate authorization step (`paylab authorize`) that produces a mandate, consumed by `auto`/`compare`/`negotiate`, instead of listing it as a peer execution protocol
- Reflect MPP's real internal structure (Core / Intents / Methods / Extensions) more faithfully, or document the simplification more prominently
- Win probability currently depends only on price gap; could be extended to a feature vector (reputation, delivery time, stock, history) without changing the core expected-value model
- Risk preference: expected value currently assumes risk neutrality (`probability × margin`); a `probability^alpha × margin^beta` formulation would let sellers be modeled as risk-averse, aggressive, or market-share-driven
- Multi-step / non-myopic negotiation (agents that reason about future rounds, not just the current one)
- Time-value of waiting (a seller might prefer a smaller profit now over a larger one later)

## License

MIT
