\# Negotiation engine, the math



Sellers don't apply a fixed discount. At every round, each `Seller` evaluates a range of candidate prices (from its current price down to its own minimum) and picks the one that maximizes \*\*expected value\*\*: `probability\_of\_winning(price) × remaining\_margin(price)`. Win probability is a logistic function of the price gap to the competitor.



\## The formula



estimate\_win\_probability(gap, sensitivity) = 1 / (1 + exp(sensitivity \* gap))





A logistic function, chosen because it naturally gives 0.5 at equal prices and approaches 0 or 1 smoothly as the gap grows  , no hard threshold, no discontinuity.



\## Calibration, not guesswork



Each `strategy` (`skimming`, `standard`, `penetration`) has its own `price\_elasticity\_belief`, how much a seller believes discounting improves its odds. These aren't hand-picked: `core/calibration.py` derives them with `scipy.optimize.minimize\_scalar`, targeting a specific win probability at a 5% price gap:



\- `skimming` → 40% (stays confident even when pricier)

\- `standard` → 25% (middle ground)

\- `penetration` → 10% (assumes being pricier hurts a lot, chases the competitor)



Currently ≈8.11 / 21.97 / 43.94 respectively. Change the targets in `calibrate\_strategies()` and the values used by `negotiate()` update automatically, nothing to copy by hand.



\## Grounded in real pricing theory



Rather than arbitrary rules, this mirrors established pricing strategy (Blythe, \*Fondamenti di Marketing\*, 2013, ch. 7; LIUC pricing strategy lecture notes): `skimming` mirrors market-skimming (patient, protects margin), `penetration` mirrors penetration pricing (aggressive, chases market share , at the real-world risk of a price war if a competitor matches it).



\## Scale and precision



Tested with 2, 15, and 350 sellers (`examples/generate\_sellers.py`), converging without performance issues (350 sellers settle around round 10). The engine is also agnostic to what the price represents  , the same math works for a total amount (900) or a per-request rate (0.00012), since only the relative gap matters, not the absolute scale. One real bug surfaced at rate scale: `min\_price` and candidate prices were rounded to 2 decimals, silently collapsing tiny rates to zero  , fixed by rounding to 8 decimals instead.



\## A note on `--max-rounds`



The default (5) is enough for small scenarios (2-3 sellers), but with more participants  , especially several using `penetration`  , the negotiation may still be actively converging when the round limit cuts it off. At 15 sellers with 5 rounds, two aggressive sellers were still chasing each other's price down; raising `--max-rounds` to 30 showed they stabilize on their own around round 7  , the cutoff, not an unresolved conflict, was why it looked unfinished at the default.

