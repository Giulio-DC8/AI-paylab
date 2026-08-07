# Negotiation engine

This is the math reference: formulas, calibration, and worked examples. For the protocol at the level of roles, message flow, and guarantees (useful if you're reimplementing it outside Python), see [`protocol-spec.md`](protocol-spec.md).

Sellers don't apply a fixed discount step. At every round, each `Seller` evaluates a range of candidate prices and picks the one that maximizes **expected value**.

## 1. Price gap

For a candidate price $p$ against a competitor price $p_c$:

$$\text{gap}(p) = \frac{p - p_c}{p_c}$$

```
gap = (price - competitor_price) / competitor_price
```

Positive if $p$ is more expensive than the competitor, negative if cheaper, zero if equal.

## 2. Win probability

The seller does not know the buyer's decision rule. Therefore it models the probability of winning through a subjective logistic belief.
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

`skimming` stays confident even when pricier (flatter curve); `penetration` assumes being pricier hurts a lot, so it chases the competitor (steeper curve). Change the targets in `calibrate_strategies()` and these values update automatically,nothing to copy by hand.

## 4. Margin

### Where $p_{\min}$ comes from

$$p_{\min} = p_{\text{start}} \cdot (1 - \text{margin}_{\min})$$

min_price = starting_price * (1 - min_margin)

Fixed once, at `Seller` creation - never recalculated during the negotiation. `min_margin` represents the maximum discount the seller (or its owner) is willing to concede from the listed starting price, decided before the negotiation begins. It is an exogenous constraint, not something derived from probability or expected value: whatever competitive pressure the negotiation applies, the seller never crosses this floor - verified explicitly by `test_seller_never_discounts_below_min_price`.

$$\text{Margin}(p) = p - p_{\min}$$

```
margin = price - min_price
```

$p_{\min}$ is the seller's floor price, fixed at creation. Not real profit, $p_{\min}$ doesn't represent actual cost, just the seller's walk-away point.

## 5. Expected value

$$\text{EV}(p) = P_{\text{win}}(p) \cdot \text{Margin}(p)$$

```
EV(price) = P_win(price) * margin(price)
```

At every round, the seller generates 20 candidate prices between its current price and $p_{\min}$, computes $\text{EV}$ for each plus the "stay put" option, and picks the maximum.

## 6. Full negotiation loop

```
history[0] = starting prices

for round t = 1 to max_rounds:
    best_price = min(price across all sellers)
    any_discount = False

    for each seller with price > best_price:
        seller.counter_offer(best_price)
        # picks argmax over 20 candidates + "stay put",
        # using EV(p) from section 5

    record history[t]
    if no seller discounted this round: break

winner = seller with lowest final price
```

## 7. Rate-based negotiation

The engine is agnostic to what the price represents, the same math works for a total amount (900) or a per-request rate (0.00012), since only the relative gap matters, not the absolute scale.

**Bug found and fixed:** `min_price` and candidate prices were originally rounded to 2 decimal places, which silently collapsed tiny rates to zero (`round(0.00012, 2) == 0.0`), blocking any discount. Fixed by rounding to 8 decimals instead, no change for normal-scale prices.

## 8. `--max-rounds` guidance

The default (5) is enough for 2-3 sellers. With more participants, especially several using `penetration`, negotiation may still be actively converging when the round limit cuts it off. Observed: 15 sellers with 5 rounds left two aggressive sellers still chasing each other; raising to 30 rounds showed they stabilize on their own around round 7, the cutoff, not an unresolved conflict, was the cause.



## Worked example: 4 sellers, round by round

Four sellers:

| Seller | starting_price | min_margin | $p_{\min}$ | strategy |
|---|---|---|---|---|
| A | 1000 | 0.3 | 700 | skimming |
| B | 900 | 0.1 | 810 | standard |
| C | 850 | 0.2 | 680 | penetration |
| D | 950 | 0.15 | 807.5 | standard |

**Round 0:** starting prices, no discounting yet.

**Round 1, step 1,the buyer computes $p_c$:**

$$p_c^{(1)} = \min(1000, 900, 850, 950) = 850 \quad (\text{C's price})$$

C already has the lowest price, so C does nothing this round. A, B, and D must each react, all against the same $p_c = 850$, none of them knows this number came from C specifically.

**Round 1, detailed calculation for B** (starting_price=900, $p_{\min}$=810, standard strategy, $s\approx21.97$):

For candidate $p=855$ (one of the 21 candidates generated in step 8):

$$\text{gap}(855) = \frac{855-850}{850} \approx 0.00588$$

$$P_{\text{win}}(855) = \frac{1}{1+e^{21.97\times0.00588}} \approx 0.468$$

$$\text{Margin}(855) = 855-810 = 45$$

$$V(855) = 0.468 \times 45 \approx 21.05$$

Compared to staying put at 900:

$$\text{gap}(900)\approx0.0588,\quad P_{\text{win}}(900)\approx0.216,\quad \text{Margin}(900)=90$$

$$V(900) \approx 0.216\times90 \approx 19.44$$

855 beats 900 (21.05 > 19.44). After checking the remaining 19 candidates, suppose the best one lands near 856, **B discounts to 856**.

**Round 1 result (same procedure applied to A and D):**

| Seller | Price after round 1 |
|---|---|
| A | 1000 → 960 (far from the market, skimming,discounts cautiously) |
| B | 900 → 856 |
| C | 850 (didn't need to react) |
| D | 950 → 870 |

**Round 2, step 1:**

$$p_c^{(2)} = \min(960, 856, 850, 870) = 850 \quad (\text{still C})$$

C remains the target; A, B, D repeat the whole procedure from their new prices.

**The loop continues** until nobody discounts in an entire round, then:

$$\text{winner} = \arg\min\big(p_A^{(T)},\, p_B^{(T)},\, p_C^{(T)},\, p_D^{(T)}\big)$$

In this scenario, C,which started cheapest and never needed to discount, is very likely to win at 850, unless another seller manages to undercut it.

**The key thing to notice:** every seller runs the *exact same* calculation (steps 2–9), using only its *own* numbers ($p_{\text{current}}$, $p_{\min}$, $s$), nobody ever computes anything "against" a specific named competitor. Everyone computes only against the single number $p_c$ the buyer communicates that round.


## Does the lowest minimum price always win?

Short answer: no. A seller's low $p_{\min}$ only translates into a win if its `strategy` (sensitivity $s$) is steep enough to actually chase the gap down. Two experiments, same question, different outcomes.

### Experiment 1,extreme margin advantage: X wins

| Seller | starting_price | min_margin | $p_{\min}$ | strategy |
|---|---|---|---|---|
| X | 1000 | 0.9 | 100 | skimming |
| Y | 750 | 0.1 | 675 | standard |
| Z | 800 | 0.15 | 680 | standard |
| W | 780 | 0.1 | 702 | penetration |

```
Round 0: X=1000, Y=750, Z=800, W=780
Round 1: X=595.0, Y=750, Z=752.0, W=744.9
Round 2: X=595.0, Y=701.25, Z=708.8, W=714.87
Round 3: X=595.0, Y=701.25, Z=707.36, W=714.87
Winner: X at 595.0
```

X's $p_{\min}$ (100) is so far below everyone else's that even skimming's flat probability curve finds it worthwhile to jump straight to 595 in round 1,the margin available is large enough that a small probability gain still produces a higher $V$ than any cautious alternative. Once at 595, nobody else can get close, so X stops discounting (already near-certain to win) while Y, Z, W settle among themselves.

### Experiment 2,moderate margin advantage: X loses

Same seller X, but with a much less extreme $p_{\min}$ (660 instead of 100), and Z/W starting more expensive:

| Seller | starting_price | min_margin | $p_{\min}$ | strategy |
|---|---|---|---|---|
| X | 1000 | 0.34 | 660.0 | skimming |
| Y | 750 | 0.1 | 675.0 | standard |
| Z | 970 | 0.15 | 824.5 | standard |
| W | 857 | 0.1 | 771.3 | penetration |

```
Round 0: X=1000, Y=750, Z=970, W=857
Round 1: X=796.0, Y=750, Z=860.875, W=788.44
Round 2: X=796.0, Y=750, Z=860.875, W=788.44
Winner: Y at 750
```

X still has the lowest $p_{\min}$ (660) of the four, but loses. `skimming`'s flat sensitivity ($s\approx8.11$) means discounting further barely improves win probability,at 796, the marginal probability gain no longer outweighs the margin given up, so X stops well short of its own floor. A large potential margin is necessary but not sufficient: it only gets used if the seller's sensitivity is steep enough to chase it.

**Takeaway:** whether a low $p_{\min}$ turns into a win depends on the interaction between how large the margin advantage is and how steep the seller's strategy curve is,not on $p_{\min}$ alone.