# Decision Log — Controllability Bound

| Date | Decision | Type | Rationale |
|---|---|---|---|
| 2026-03-31 | Focus on 3-4 primary domains + 1 transfer test, not all 7 | SCOPE | Depth over breadth. Rigorous validation in 4 domains scores higher than loose claims across 7. |
| 2026-03-31 | Game-theoretic domain for transfer test (Colonel Blotto) | DESIGN | CPU-feasible, genuinely non-ML, known equilibria for comparison, tests principle at most abstract level. |
| 2026-03-31 | Additive bound as primary, multiplicative as competing model | DESIGN | Cascade-benchmark evidence (R²=0.992 vs -0.06) strongly favors additive. Pre-registering multiplicative as alternative prevents confirmation bias. |
