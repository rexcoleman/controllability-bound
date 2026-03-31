"""Controllability Scorer — predict defense difficulty from channel decomposition.

Score system vulnerability using the additive controllability-observability
decomposition: E[attack_success] ≈ w₀ + w₁·C + w₂·(1-D)

Where:
  C ∈ [0,1]: attacker controllability of input channel
  D ∈ [0,1]: defender observability of input channel
  w₀, w₁, w₂: domain-dependent weights (fitted or default)

Key finding: C and D contribute additively and independently, NOT as a
product C·(1-D). The dominant factor is domain-dependent:
  - Security systems: observability gaps dominate (w₂ >> w₁)
  - Game-theoretic systems: controllability dominates (w₁ >> w₂)
"""

__version__ = "0.1.0"

from controllability_scorer.scorer import (
    Channel,
    SystemSpec,
    score_system,
    rank_channels,
)
