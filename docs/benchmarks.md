# Benchmarks

Reproducible performance measurements for `core.negotiation.negotiate()` — the reference `NegotiationProtocol` implementation. Methodology and how to reproduce below.

## Results

| Sellers | Time (s) | Peak memory (KB) | Rounds | Time/round (ms) |
|---|---|---|---|---|
| 2 | 0.0174 | 0.7 | 2 | 8.6862 |
| 10 | 0.0053 | 1.5 | 3 | 1.7788 |
| 50 | 0.0437 | 21.5 | 9 | 4.8571 |
| 100 | 0.1038 | 53.9 | 12 | 8.6497 |
| 350 | 0.2953 | 184.3 | 10 | 29.5349 |

Measured with Python 3.13.9, Windows/AMD64, single run (see "Notes" below for why time/round isn't strictly monotonic).

## Methodology

- Script: [`benchmarks/negotiation_bench.py`](../benchmarks/negotiation_bench.py). Standard library only — `time.perf_counter()` for wall-clock time, `tracemalloc` for peak memory during the `negotiate()` call — no benchmarking dependency added to the project.
- Seller pools are generated with the same field ranges and a fixed seed (42) as [`examples/generate_sellers.py`](../examples/generate_sellers.py): `starting_price` uniform in [800, 1000], `min_margin` uniform in [0.05, 0.20], `strategy` uniform over `skimming`/`standard`/`penetration`.
- `max_rounds=100` for every size — generous enough that "rounds" in the table reflects actual convergence, not a round-budget cutoff (confirmed: every row's `rounds` is well under 100).
- Reproduce: `python benchmarks/negotiation_bench.py` from the repo root.

## Notes

- **Rounds don't grow linearly with seller count** (9 rounds at 50 sellers, 12 at 100, but only 10 at 350) — this depends on the specific random draw of prices/strategies/margins for that pool, not on pool size directly. This matches what [`negotiation.md`](negotiation.md) §9 already documents: convergence speed is governed by the margin-advantage/strategy-sensitivity interaction of the specific sellers involved, not by N alone.
- **Time/round is not strictly increasing with N either** — per-round cost scales with N (every seller above `best_price` re-evaluates 20 candidates), but total time also depends on how many rounds actually ran, so the two effects interact. The relationship that does hold cleanly: **peak memory scales linearly with N** (roughly 0.5 KB/seller), consistent with `negotiate()` holding one `Seller` object and one history entry per seller per round, with no hidden quadratic-in-N data structure.
- These numbers characterize the reference implementation on one machine; they're meant to establish "this doesn't fall over at hundreds of sellers" and give a reproducible baseline to compare future changes against — not a formal performance guarantee.
