# Hypothesis Registry — Controllability Bound

> **Lock status:** PRE-REGISTERED. Hypotheses below are immutable after lock_commit is set.
> **Lock commit: 8500cc9dc1b7f91a359e9a3bc9f4e167177816d0

---

## H-1: Additive Controllability Bound Fits Across Domains

**Statement:** The additive bound `E[attack_success] ≤ Σ wᵢ · C(cᵢ) · (1 - D(cᵢ))` achieves R² > 0.8 when fit to attack outcome data from ≥3 structurally diverse security domains.

**Prediction:** R² > 0.8 in at least 3 of 4 tested domains (RL agents, LLM agents, multi-agent cascades, strategic games).

**Surprise criteria:** R² < 0.5 in ANY domain would indicate the bound is domain-specific, not general. R² > 0.95 in ALL domains would indicate the bound is unexpectedly tight.

**Falsification:** If R² < 0.5 in 2+ domains, the additive controllability model is insufficient as a general bound.

---

## H-2: Additive Outperforms Multiplicative

**Statement:** The additive bound achieves higher R² than the multiplicative alternative `Π [C(cᵢ) · (1 - D(cᵢ))]^wᵢ` in ≥3 of 4 tested domains.

**Prediction:** Additive R² > Multiplicative R² in at least 3 domains. Based on cascade-benchmark evidence (additive R²=0.992 vs multiplicative R²=-0.06).

**Surprise criteria:** Multiplicative wins in ≥2 domains. Would indicate channel interactions are stronger than assumed.

**Falsification:** If multiplicative R² > additive R² in 3+ domains, the additive decomposition is wrong.

---

## H-3: Controllability Metric Beats Simple Baselines

**Statement:** The multi-channel controllability bound predicts attack success better than (a) naive mean predictor and (b) best single-channel predictor.

**Prediction:** Bound R² exceeds single-feature R² by > 0.1 in ≥3 domains.

**Surprise criteria:** Single-feature predictor matches bound (Δ < 0.05). Would mean one channel dominates all systems — simpler than expected.

**Falsification:** If single-feature predictor R² ≥ bound R² in 3+ domains, multi-channel formalization is unnecessary.

---

## H-4: Game-Theoretic Transfer

**Statement:** The controllability bound, fit on security domain data, predicts game outcomes in a Colonel Blotto game within 15% of observed win rates.

**Prediction:** Bound predictions within 15% of simulated outcomes at each controllability level.

**Surprise criteria:** Within 5% — bound is tighter than expected in a novel domain. OR >30% — bound doesn't transfer outside ML security.

**Falsification:** If prediction error > 30% at all controllability levels, the principle does not generalize to non-ML adversarial systems.

---

## H-5: Bound Tightness Is Informative

**Statement:** The mean tightness ratio (predicted / observed attack success) is between 1.0 and 3.0 across all domains, making the bound practically useful (not trivially loose).

**Prediction:** Mean tightness 1.5-2.5x.

**Surprise criteria:** Tightness < 1.2x (bound is nearly exact — suggests causal, not just correlational). Tightness > 5x (bound is too loose to be useful).

**Falsification:** If tightness > 5x in 3+ domains, the bound is technically correct but practically useless.
