"""
Reproducible benchmark for core.negotiation.negotiate().

Measures, for a range of seller-pool sizes: wall-clock time, peak
memory, number of rounds to convergence, and average time per round.

Standard library only (time + tracemalloc) - no new project dependency
for what is a one-off measurement script, same convention as
examples/generate_sellers.py.

Run with: python benchmarks/negotiation_bench.py
"""
import random
import sys
import time
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.negotiation import Seller, negotiate

STRATEGIES = ["skimming", "standard", "penetration"]
SELLER_COUNTS = [2, 10, 50, 100, 350]
SEED = 42


def make_sellers(n, seed=SEED):
    rng = random.Random(seed)
    return [
        Seller(
            name=f"Seller_{i:03d}",
            starting_price=round(rng.uniform(800, 1000), 2),
            min_margin=round(rng.uniform(0.05, 0.20), 3),
            strategy=rng.choice(STRATEGIES),
        )
        for i in range(n)
    ]


def bench_one(n):
    sellers = make_sellers(n)

    tracemalloc.start()
    start = time.perf_counter()
    outcome = negotiate(sellers, max_rounds=100)
    elapsed = time.perf_counter() - start
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    rounds = len(outcome["history"]) - 1
    return {
        "n_sellers": n,
        "time_s": elapsed,
        "peak_memory_kb": peak_bytes / 1024,
        "rounds": rounds,
        "time_per_round_ms": (elapsed / rounds * 1000) if rounds else 0.0,
    }


def main():
    results = [bench_one(n) for n in SELLER_COUNTS]

    header = f"{'Sellers':>8} | {'Time (s)':>10} | {'Peak mem (KB)':>14} | {'Rounds':>7} | {'Time/round (ms)':>16}"
    print(header)
    print("-" * len(header))
    for r in results:
        print(
            f"{r['n_sellers']:>8} | {r['time_s']:>10.4f} | {r['peak_memory_kb']:>14.1f} "
            f"| {r['rounds']:>7} | {r['time_per_round_ms']:>16.4f}"
        )

    print()
    print("Markdown table:")
    print()
    print("| Sellers | Time (s) | Peak memory (KB) | Rounds | Time/round (ms) |")
    print("|---|---|---|---|---|")
    for r in results:
        print(
            f"| {r['n_sellers']} | {r['time_s']:.4f} | {r['peak_memory_kb']:.1f} "
            f"| {r['rounds']} | {r['time_per_round_ms']:.4f} |"
        )


if __name__ == "__main__":
    main()
