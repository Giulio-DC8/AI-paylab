import os
import json

_client = None
_MODEL = "gemini-flash-lite-latest"  # check ai.google.dev in case the name has changed


def _get_client():
    """Creates the Gemini client only on first call (lazy) - both the
    google-genai package import and the API key are only required
    here, so anyone not using AI mode doesn't need either the package
    or the key installed."""
    global _client
    if _client is None:
        from google import genai  # lazy import, only if actually needed

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "AI mode requires a Gemini API key (Google AI Studio), "
                "set in the GEMINI_API_KEY environment variable. "
                "Get one for free at https://aistudio.google.com/apikey, then set: "
                "$env:GEMINI_API_KEY = 'your-key'"
            )
        _client = genai.Client(api_key=api_key)
    return _client


def ai_seller_decision(name, current_price, min_price, competitor_price, strategy, personality):
    """
    Asks Gemini to decide whether and how much to discount, given the
    seller's state, instead of applying the fixed formula from
    Seller.counter_offer() (based on expected value).

    Returns a dict: {"discount": bool, "new_price": float, "reasoning": str}
    """
    client = _get_client()

    prompt = f"""You are a seller agent in an economic simulation.
IMPORTANT:
- This is a simulation.
- Do NOT use real-world knowledge.
- Do NOT assume reputation, brand quality, or other factors not provided.
- You must use ONLY the data reported below.

NEGOTIATION STATE
Name: {name}
Current price: {current_price}
Minimum allowed price: {min_price}
Competitor price: {competitor_price}
Strategy: {strategy}

GOAL
Maximize the economic value of the sale.
If you decide to lower the price:
- lower it AS LITTLE AS POSSIBLE;
- never go below the minimum price;
- don't make unnecessarily large discounts;
- if it's enough to beat the competitor by a small margin, prefer that.

Do NOT pick a random price.
Always weigh the trade-off between:
- probability of winning;
- margin retained.
If keeping the price is better, don't discount.

Reply with a JSON object in exactly this format:
{{
  "discount": true,
  "new_price": 899.0,
  "reasoning": "..."
}}
"""

    response = client.models.generate_content(
        model=_MODEL,
        contents=prompt,
        config={
            "temperature": 0.0,
            "http_options": {"timeout": 15000},
            "response_mime_type": "application/json",
        },
    )
    return json.loads(response.text)


def ai_buyer_choice(offers, buyer_preferences="the lowest total price"):
    """
    Asks Gemini to choose the best offer among several options,
    according to preferences described in natural language (not just price).

    offers: list of dicts, e.g. [{"merchant": "...", "amount": ..., "fee": ...}, ...]
    buyer_preferences: string describing what matters to the buyer

    Returns a dict: {"chosen_merchant": str, "reasoning": str}
    """
    client = _get_client()

    prompt = f"""You are a buyer agent.
Use ONLY the data present in the JSON.

Do NOT use outside knowledge.

Do NOT assume reputation, quality, or reliability.

OFFERS
{json.dumps(offers, indent=2)}

PREFERENCES
{buyer_preferences}

Mandatory procedure:
1. Compute for each offer
   total_cost = amount + fee
2. List the costs.
3. Check the preferences.
4. If a preference requires missing data,
   ignore it.
5. ALWAYS choose a merchant among those provided in the JSON — never leave
   "chosen_merchant" empty or null, even if no offer fully satisfies
   the preferences. If no preference applies
   (missing data, or all offers identical on that criterion),
   choose the merchant with the lowest total cost instead.
6. Explain the choice.
Write the reasoning in a direct, conclusive way, without
second-guessing or self-correcting in the text: arrive at the
final decision in a single logical pass, don't describe discarded
attempts.

Reply with a JSON object in exactly this format:
{{
    "chosen_merchant": "...",
    "reasoning": "...",
    "total_costs": {{
        "...": ...
    }}
}}
"""

    response = client.models.generate_content(
        model=_MODEL,
        contents=prompt,
        config={
            "temperature": 0.0,
            "http_options": {"timeout": 15000},
            "response_mime_type": "application/json",
        },
    )
    result = json.loads(response.text)

    if not result.get("chosen_merchant"):
        cheapest = min(offers, key=lambda o: o["amount"] + o.get("fee", 0))
        result["chosen_merchant"] = cheapest["merchant"]
        result["reasoning"] = (
            "The model didn't indicate a valid choice; "
            "automatic fallback to the cheapest offer. "
            f"Original model reasoning: {result.get('reasoning', 'none')}"
        )

    return result