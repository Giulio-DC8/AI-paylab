# Negotiation engine 

Sellers don't apply a fixed discount step. At every round, each `Seller` evaluates a range of candidate prices and picks the one that maximizes **expected value**.

## 1. Price gap

For a candidate price $p$ against a competitor price $p_c$:

$$\text{gap}(p) = \frac{p - p_c}{p_c}$$

```
gap = (price - competitor_price) / competitor_price
```

Positive if $p$ is more expensive than the competitor, negative if cheaper, zero if equal.

## 2. Win probability

A logistic function of the gap:

$$P_{\text{win}}(p) = \frac{1}{1 + e^{s \cdot \text{gap}(p)}}$$

```
P_win(p) = 1 / (1 + exp(sensitivity * gap))
```

where $s$ is the seller's `price_elasticity_belief`. Properties:

- $P_{\text{win}} = 0.5$ when $\text{gap} = 0$ (equal price)
- $P_{\text{win}} \to 1$ as $\text{gap} \to -\infty$ (much cheaper)
- $P_{\text{win}} \to 0$ as $\text{gap} \to +\infty$ (much pricier)
- Smooth, continuous, no discontinuity

**Numerical stability:** for $|s \cdot \text{gap}| > 700$, the exponential is clamped to $P_{\text{win}}=0$ or $1$ directly, avoiding `OverflowError` on extreme gaps (e.g. a price 1000x the competitor's).

## 3. Calibrating sensitivity $s$

$s$ is not hand-picked. `core/calibration.py` solves for it:

$$s^* = \underset{s}{\arg\min} \left( P_{\text{win}}(\text{gap}=0.05,\, s) - P_{\text{target}} \right)^2$$

using `scipy.optimize.minimize_scalar`, with design targets at a 5% price gap:

| Strategy | $P_{\text{target}}$ | Resulting $s$ |
|---|---|---|
| `skimming` | 0.40 | ≈8.11 |
| `standard` | 0.25 | ≈21.97 |
| `penetration` | 0.10 | ≈43.94 |

`skimming` stays confident even when pricier (flatter curve); `penetration` assumes being pricier hurts a lot, so it chases the competitor (steeper curve). Change the targets in `calibrate_strategies()` and these values update automatically — nothing to copy by hand.

## 4. Margin

# Where $p_{\min}$ comes from

$$p_{\text{min}} = p_{\text{starting}} \dot (1 - \text{min\_margin})$$

min_price = starting_price * (1 - min_margin)

Fixed once, at `Seller` creation - never recalculated during the negotiation. `min_margin` represents the maximum discount the seller (or its owner) is willing to concede from the listed starting price, decided before the negotiation begins. It is an exogenous constraint, not something derived from probability or expected value: whatever pressure the negotiation applies (competition, time cost via `lambda_time`), the seller never crosses this floor - verified explicitly by `test_seller_never_discounts_below_min_price` and `test_lambda_time_never_crosses_minimum_price`.

$$\text{Margin}(p) = p - p_{\min}$$

```
margin = price - min_price
```

$p_{\min}$ is the seller's floor price, fixed at creation. Not real profit — $p_{\min}$ doesn't represent actual cost, just the seller's walk-away point.

## 5. Expected value (base case, no time cost)

$$\text{EV}(p) = P_{\text{win}}(p) \cdot \text{Margin}(p)$$

```
EV(price) = P_win(price) * margin(price)
```

At every round, the seller generates 20 candidate prices between its current price and $p_{\min}$, computes $\text{EV}$ for each plus the "stay put" option, and picks the maximum.

## 6. Time-value of waiting (optional)

By default there's no cost to continuing to negotiate. With `lambda_time` ($\lambda$) set above 0:

$$\underbrace{\text{EV}(p, t)}_{\text{expected value}} = \underbrace{P_{\text{win}}(p) \cdot \text{Margin}(p)}_{\text{utile atteso}} - \underbrace{\lambda \cdot t \cdot \big(1 - P_{\text{win}}(p)\big) \cdot \text{Margin}(p)}_{\text{costo di rimanere fuori mercato al round } t}$$

```
EV(price, round) = [P_win * margin]              <- utile atteso
                 - [lambda_time * round * (1 - P_win) * margin]   <- costo di rimanere fuori mercato al round t
```

where $t$ is the current round number. The penalty term is proportional to **how far the price is from the market** ($1-P_{\text{win}}$), not to time alone:

- Price near the competitor's ($P_{\text{win}} \approx 1$) → penalty ≈ 0, costs almost nothing to hold
- Price far from the market ($P_{\text{win}} \approx 0$) → penalty grows every round, increasingly expensive to maintain

**Why $\lambda=0$ is exactly backward-compatible:** the penalty term is multiplied by $\lambda$, so at $\lambda=0$ it is algebraically zero for every candidate — not just empirically close to the old behavior, but identical by construction.

**Why this formulation works** (unlike three earlier attempts that didn't): the penalty depends on $P_{\text{win}}(p)$, which varies per candidate price — so it doesn't scale every option by the same constant. A uniform scaling (tried first) never changes which candidate has the highest value; this formulation can.

### Observed calibration ($p_{\text{start}}=1000$, $p_{\min}=700$ for competitor, seller starts at 1000 vs. competitor at 700)

| $\lambda$ | Rounds to converge | Final price |
|---|---|---|
| 0.02 | doesn't converge in 30 rounds | ~721 (still discounting) |
| 0.05 | 20 | 700.0 |
| 0.10 | 10 | 700.0 |
| 0.50 | 2 | 700.0 |

**Safety check:** even at $\lambda=0.5$, a seller with $p_{\min}=710$ (unreachable, above the competitor's 700) stops exactly at 710 and never crosses it — the floor constraint holds regardless of time pressure.

## 7. Full negotiation loop

```
history[0] = starting prices

for round t = 1 to max_rounds:
    best_price = min(price across all sellers)
    any_discount = False

    for each seller with price > best_price:
        seller.counter_offer(best_price, round_number=t)
        # picks argmax over 20 candidates + "stay put",
        # using EV(p, t) from section 5 or 6

    record history[t]
    if no seller discounted this round: break

winner = seller with lowest final price
```

## 8. Rate-based negotiation

The engine is agnostic to what the price represents — the same math works for a total amount (900) or a per-request rate (0.00012), since only the relative gap matters, not the absolute scale.

**Bug found and fixed:** `min_price` and candidate prices were originally rounded to 2 decimal places, which silently collapsed tiny rates to zero (`round(0.00012, 2) == 0.0`), blocking any discount. Fixed by rounding to 8 decimals instead — no change for normal-scale prices.

## 9. `--max-rounds` guidance

The default (5) is enough for 2-3 sellers. With more participants — especially several using `penetration` — negotiation may still be actively converging when the round limit cuts it off. Observed: 15 sellers with 5 rounds left two aggressive sellers still chasing each other; raising to 30 rounds showed they stabilize on their own around round 7 — the cutoff, not an unresolved conflict, was the cause.