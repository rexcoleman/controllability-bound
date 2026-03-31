"""Core scoring module for controllability-observability decomposition."""

from dataclasses import dataclass, field
from typing import Optional

import numpy as np


# Default weights from cross-domain fit (all_security, n=24)
# y = w0 + w1*C + w2*(1-D)
DEFAULT_WEIGHTS = {
    "intercept": -0.15,
    "controllability": 0.55,
    "observability_gap": 0.65,
}

# Domain-specific weights (from ablation study)
DOMAIN_WEIGHTS = {
    "security_general": {"intercept": -0.15, "controllability": 0.55, "observability_gap": 0.65},
    "rl_agent": {"intercept": -0.03, "controllability": 0.10, "observability_gap": 0.55},
    "llm_agent": {"intercept": 0.10, "controllability": 0.60, "observability_gap": 0.45},
    "multi_agent": {"intercept": 0.20, "controllability": 0.00, "observability_gap": 0.80},
    "game_theoretic": {"intercept": 0.05, "controllability": 0.44, "observability_gap": 0.07},
}


@dataclass
class Channel:
    """An input channel in a system.

    Args:
        name: Human-readable channel identifier
        controllability: C ∈ [0,1] — fraction of channel input space attacker can control
        observability: D ∈ [0,1] — fraction of channel state visible to defender
        description: Optional explanation of how C and D were measured
    """
    name: str
    controllability: float
    observability: float
    description: str = ""

    def __post_init__(self):
        if not 0 <= self.controllability <= 1:
            raise ValueError(f"Controllability must be in [0,1], got {self.controllability}")
        if not 0 <= self.observability <= 1:
            raise ValueError(f"Observability must be in [0,1], got {self.observability}")

    @property
    def vulnerability_score(self) -> float:
        """Per-channel vulnerability: higher = more vulnerable."""
        return self.controllability * (1 - self.observability)

    @property
    def separate_score(self) -> float:
        """Additive decomposition score (no product assumption)."""
        w = DEFAULT_WEIGHTS
        return w["controllability"] * self.controllability + w["observability_gap"] * (1 - self.observability)


@dataclass
class SystemSpec:
    """Specification of a system's input channels.

    Args:
        name: System identifier
        channels: List of Channel objects
        domain: Optional domain hint for weight selection
    """
    name: str
    channels: list = field(default_factory=list)
    domain: Optional[str] = None

    def add_channel(self, name: str, controllability: float, observability: float,
                    description: str = "") -> "SystemSpec":
        self.channels.append(Channel(name, controllability, observability, description))
        return self


def score_system(spec: SystemSpec, model: str = "separate") -> dict:
    """Score a system's overall vulnerability.

    Args:
        spec: SystemSpec with channels defined
        model: "separate" (recommended) or "product" (original conjecture)

    Returns:
        dict with overall_score, channel_scores, dominant_factor, weights_used
    """
    if not spec.channels:
        raise ValueError("System has no channels defined")

    weights = DOMAIN_WEIGHTS.get(spec.domain, DEFAULT_WEIGHTS)
    n = len(spec.channels)

    channel_scores = []
    for ch in spec.channels:
        if model == "separate":
            score = (weights["intercept"] / n
                     + weights["controllability"] * ch.controllability
                     + weights["observability_gap"] * (1 - ch.observability))
        else:  # product
            score = ch.controllability * (1 - ch.observability)
        channel_scores.append({
            "name": ch.name,
            "C": ch.controllability,
            "D": ch.observability,
            "score": round(max(0, min(1, score)), 4),
            "risk_level": _risk_level(score),
        })

    overall = np.mean([cs["score"] for cs in channel_scores])

    # Determine dominant factor
    c_contrib = weights["controllability"] * np.mean([ch.controllability for ch in spec.channels])
    d_contrib = weights["observability_gap"] * np.mean([1 - ch.observability for ch in spec.channels])
    dominant = "controllability" if c_contrib > d_contrib else "observability_gap"

    return {
        "system": spec.name,
        "model": model,
        "domain": spec.domain or "general",
        "overall_score": round(float(max(0, min(1, overall))), 4),
        "overall_risk": _risk_level(overall),
        "dominant_factor": dominant,
        "c_contribution": round(float(c_contrib), 4),
        "d_contribution": round(float(d_contrib), 4),
        "weights_used": weights,
        "channels": sorted(channel_scores, key=lambda x: -x["score"]),
        "recommendation": _recommendation(channel_scores),
    }


def rank_channels(spec: SystemSpec) -> list:
    """Rank channels by vulnerability (highest risk first).

    Returns list of (channel_name, score, recommendation) tuples.
    """
    result = score_system(spec)
    ranked = []
    for ch in result["channels"]:
        rec = ""
        if ch["D"] < 0.3:
            rec = "PRIORITY: Add monitoring — low observability is the primary risk"
        elif ch["C"] > 0.7 and ch["D"] < 0.6:
            rec = "HIGH: High controllability + moderate observability gap"
        elif ch["score"] < 0.2:
            rec = "LOW: Acceptable risk level"
        else:
            rec = "MODERATE: Monitor and review"
        ranked.append((ch["name"], ch["score"], rec))
    return ranked


def _risk_level(score: float) -> str:
    if score >= 0.7:
        return "CRITICAL"
    elif score >= 0.5:
        return "HIGH"
    elif score >= 0.3:
        return "MODERATE"
    else:
        return "LOW"


def _recommendation(channel_scores: list) -> str:
    critical = [c for c in channel_scores if c["risk_level"] == "CRITICAL"]
    high = [c for c in channel_scores if c["risk_level"] == "HIGH"]
    low_d = [c for c in channel_scores if c["D"] < 0.3]

    parts = []
    if critical:
        parts.append(f"CRITICAL: {len(critical)} channel(s) at critical risk — "
                     f"prioritize {critical[0]['name']}")
    if low_d:
        parts.append(f"Add monitoring to {len(low_d)} low-observability channel(s): "
                     + ", ".join(c["name"] for c in low_d))
    if not parts:
        parts.append("No critical risks identified. Review moderate channels periodically.")
    return "; ".join(parts)
