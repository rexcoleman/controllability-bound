---
title: "Your Security Metrics Are Wrong: Why Controllability and Observability Are Independent Risk Factors"
date: 2026-03-31
author: Rex Coleman
categories: [AI Security, Research]
tags: [controllability, observability, formal-methods, cross-domain]
audience_side: of-ai
sharing_tier: 1_publish
format: research-finding
---

Most security analysis treats attacker controllability and defender observability as a single composite metric. If the attacker controls the channel AND the defender can't see it, the system is vulnerable. Multiply the two together, get a risk score, prioritize accordingly.

I tested this assumption across four security domains. The product model fails.

## What We Expected

I pre-registered a formal bound: attack success is proportional to the product of attacker controllability (C) and the defender's observability gap (1-D). The intuition is clean — attacks succeed when the attacker controls the input AND the defender can't observe it.

I fit the bound to 24 data points across three security domains: reinforcement learning agent attacks, LLM agent injection, and multi-agent cascade propagation. Then I tested it on 25,000 Colonel Blotto games as a transfer test to a non-ML domain.

## What Actually Happened

The product model achieved R²=0.34. Mediocre. A model that just predicts the average attack success rate would have done nearly as well.

But when we separated C and D into independent terms — `attack_success ≈ w₀ + w₁·C + w₂·(1-D)` — the R² jumped to 0.76 in security domains and 0.93 in games.

Controllability and observability aren't multiplicative. They're additive and independent.

## Why This Matters: The Weight Asymmetry

The separation revealed something we didn't predict: the relative importance of C and D flips depending on the domain.

**In security systems, observability dominates.** For RL agents, removing the controllability term (C) from the model barely changes the fit — R² drops by only 0.03. But removing the observability term drops R² by 0.69. Translation: for security architects, adding monitoring to unobserved channels reduces attack success far more than restricting what attackers can control.

**In game-theoretic systems, controllability dominates.** In Colonel Blotto, C alone explains 91% of the variance. Observability explains 2%. The player with more resources wins regardless of information advantage.

This asymmetry has practical consequences. If you're designing a multi-agent system, your first investment should be monitoring the delegation channel (increasing D), not restricting what content agents can pass to each other (decreasing C). Most security architectures do the opposite — they focus on access control (reducing C) when they should focus on observability (increasing D).

## The Architectural Observability Gap

One finding caught us off guard. Multi-agent capability-scoped trust claims an architectural observability of D=0.8 — the capability filter exists and inspects every delegation. But the actual defense effectiveness implies D_effective of roughly 0.1.

The filter exists. It inspects. It passes 90% of malicious content anyway.

This gap between what a defense CLAIMS to observe and what it EFFECTIVELY observes is measurable. And it matters: a security architect who trusts architectural D=0.8 will under-invest in additional monitoring, leaving the system far more vulnerable than the architecture diagram suggests.

## How We Tested This

I pre-registered six hypotheses and three competing models before fitting anything. Here's the key discipline: I locked the operational definitions before seeing any results.

For RL agents, I defined controllability as the perturbation magnitude. Observability was 0 for the observation channel (no monitoring) and 0.5 for rewards (logged during training).

For LLM agents, controllability was the token-level control fraction. The user prompt scores 1.0; the reasoning chain scores 0.5 (indirect control). Observability tracks logging coverage per channel.

For multi-agent cascades, controllability is always 1.0 — the attacker controls the poisoned content regardless of trust model. Observability varies: 0.0 for implicit trust, 1.0 for zero-trust verification.

For Colonel Blotto games, controllability is the troop allocation fraction. Observability is the fraction of opponent battlefields visible before committing.

Two of my six hypotheses were refuted. The product model and the "beats single-feature" claim both failed. Those refutations led to the better model. The pre-registration forced me to test the intuitive answer and discover it was wrong.

## Try It Yourself

The `controllability-scorer` package scores any system's input channels:

```bash
pip install -e .  # from the repo (PyPI release pending)
controllability-scorer quick -c 0.5 -d 0.0 --name "reasoning_chain"
```

Output: `Score: 0.775 (CRITICAL)` — a channel with moderate attacker control but zero defender observability is critical risk, dominated by the observability gap.

Full code, data, and figures: [github.com/rexcoleman/controllability-bound](https://github.com/rexcoleman/controllability-bound)

## What's Next

The additive model captures 76-93% of variance with two terms. The remaining 7-24% is unexplained. In LLM agents specifically, adding interaction terms improves R² by 0.49 — suggesting that in systems with coupled channels, the simple additive model is an approximation.

The open question: is there a tighter, nonlinear bound that captures channel coupling? And does the observability-dominance finding hold in deployed production systems, or only in controlled experiments?

---

## Limitations

- Three security domains from one researcher's portfolio. Selection bias is mitigated by the game-theoretic transfer test.
- Small per-domain sample sizes (5-10 points). Confidence intervals are wide.
- Operationalizing C and D requires judgment. Inter-rater reliability not yet tested.
- Colonel Blotto is simpler than real adversarial systems. Known equilibria, finite actions.
- Linear model. Nonlinear effects may exist in coupled-channel systems.

*Rex Coleman builds tools that secure AI systems from the architecture up. More at [rexcoleman.dev](https://rexcoleman.dev).*
