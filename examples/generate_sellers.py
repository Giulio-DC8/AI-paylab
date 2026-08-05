import json
import random

random.seed(42)  # so the result is reproducible every time you run it

strategies = ["skimming", "standard", "penetration"]
sellers = []

for i in range(350):
    sellers.append({
        "name": f"Seller_{i:03d}",
        "starting_price": round(random.uniform(800, 1000), 2),
        "min_margin": round(random.uniform(0.05, 0.20), 3),
        "strategy": random.choice(strategies),
    })

with open("sellers_350.json", "w") as f:
    json.dump(sellers, f, indent=2)

print(f"Generated {len(sellers)} sellers in sellers_350.json")