"""
Demo: compares the deterministic negotiation engine
(core/negotiation.py, expected value) against a language-model-based
engine (core/ai_agent.py) on the same scenario.

Requires the GEMINI_API_KEY environment variable to be set.
Run with: python examples/ai_demo.py
"""

from core.ai_agent import ai_seller_decision, ai_buyer_choice

print("=" * 60)
print("DEMO: AI engine (Gemini) vs deterministic engine")
print("=" * 60)

print("\n--- Scenario: Lufthansa vs Emirates ---\n")

# 1. A single seller's decision, with natural-language reasoning
print(">>> ai_seller_decision(): Lufthansa evaluates whether to discount\n")

decision = ai_seller_decision(
    name="Lufthansa",
    current_price=950,
    min_price=855,
    competitor_price=900,
    strategy="skimming",
    personality="analytical",
)

print(f"Discounts:     {decision['discount']}")
print(f"New price:     {decision['new_price']}")
print(f"Reasoning:     {decision['reasoning']}")

# 2. A buyer choosing between multiple offers, with preferences described in words
print("\n" + "-" * 60)
print(">>> ai_buyer_choice(): a company chooses between two offers\n")

offers = [
    {
        "merchant": "Lufthansa",
        "amount": decision["new_price"],
        "fee": 14.25,
    },
    {
        "merchant": "Emirates",
        "amount": 900,
        "fee": 9.0,
    },
]
choice = ai_buyer_choice(
    offers,
    buyer_preferences=(
        "we prefer a reliable supplier with a good reputation "
        "even if it costs slightly more, but we don't want to pay "
        "more than 5% above the cheapest offer"
    ),
)

print(f"Offer chosen:  {choice['chosen_merchant']}")
print(f"Reasoning:     {choice['reasoning']}")

print("\n" + "=" * 60)
print("Note: unlike the deterministic engine (negotiate()), this")
print("decision isn't reproducible, has a per-call cost, and isn't")
print("covered by automated tests.")
print("=" * 60)