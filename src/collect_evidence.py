#!/usr/bin/env python3
"""Collect controllability evidence from existing project data.

Operational definitions of C and D are LOCKED per EXPERIMENTAL_DESIGN.md.
Do NOT change these values after seeing fit results.

Each data point: (channel_name, domain, C, D, observed_attack_success)
"""

import json
import os

# ─── Domain 1: RL Agent Vulnerability (FP-12) ────────────────────────
# C = perturbation magnitude (epsilon) or corruption rate
# D = 0.0 for observation (no monitoring), 0.5 for reward (logged during training)

RL_DATA = [
    # Observation perturbation — Gaussian
    # C = epsilon, D = 0.0 (no per-step monitoring)
    # Success = policy divergence fraction (from FINDINGS: 28-34% at eps=0.01)
    {"channel": "obs_gaussian_001", "domain": "rl_agent", "C": 0.01, "D": 0.0,
     "success": 0.31, "source": "FP-12 obs_perturb gaussian eps=0.01 mean(access_ctrl, tool_sel)"},
    {"channel": "obs_gaussian_005", "domain": "rl_agent", "C": 0.05, "D": 0.0,
     "success": 0.38, "source": "FP-12 obs_perturb gaussian eps=0.05"},
    {"channel": "obs_gaussian_010", "domain": "rl_agent", "C": 0.10, "D": 0.0,
     "success": 0.44, "source": "FP-12 obs_perturb gaussian eps=0.10"},
    {"channel": "obs_gaussian_020", "domain": "rl_agent", "C": 0.20, "D": 0.0,
     "success": 0.52, "source": "FP-12 obs_perturb gaussian eps=0.20"},

    # Observation perturbation — Targeted flip
    # C = N_targeted / N_features = 2/5 = 0.40 (tool_selection)
    {"channel": "obs_targeted_001", "domain": "rl_agent", "C": 0.40, "D": 0.0,
     "success": 0.40, "source": "FP-12 obs_perturb targeted_flip eps=0.01"},
    {"channel": "obs_targeted_010", "domain": "rl_agent", "C": 0.40, "D": 0.0,
     "success": 0.55, "source": "FP-12 obs_perturb targeted_flip eps=0.10"},

    # Reward poisoning
    # C = corruption_rate, D = 0.5 (reward signal logged during training)
    {"channel": "reward_001", "domain": "rl_agent", "C": 0.01, "D": 0.5,
     "success": 0.002, "source": "FP-12 reward_poison rate=0.01"},
    {"channel": "reward_005", "domain": "rl_agent", "C": 0.05, "D": 0.5,
     "success": 0.005, "source": "FP-12 reward_poison rate=0.05"},
    {"channel": "reward_010", "domain": "rl_agent", "C": 0.10, "D": 0.5,
     "success": 0.010, "source": "FP-12 reward_poison rate=0.10"},
    {"channel": "reward_020", "domain": "rl_agent", "C": 0.20, "D": 0.5,
     "success": 0.016, "source": "FP-12 reward_poison rate=0.20"},
]

# ─── Domain 2: LLM Agent Red-Team (FP-02) ────────────────────────────
# C = token-level control fraction, D = logging/gating coverage

LLM_AGENT_DATA = [
    # User prompt: C=1.0 (all tokens attacker-chosen), D=1.0 (directly logged)
    {"channel": "user_prompt", "domain": "llm_agent", "C": 1.0, "D": 1.0,
     "success": 0.87, "source": "FP-02 direct injection mean(3 seeds)"},

    # Tool parameters: C=1.0 (full param control), D=0.8 (logged + validated)
    {"channel": "tool_params", "domain": "llm_agent", "C": 1.0, "D": 0.8,
     "success": 0.75, "source": "FP-02 tool permission violation"},

    # Reasoning chain: C=0.5 (indirect reliable control), D=0.0 (internal state)
    {"channel": "reasoning_chain", "domain": "llm_agent", "C": 0.5, "D": 0.0,
     "success": 1.00, "source": "FP-02 reasoning chain hijacking"},

    # Conversation history: C=0.7 (requires prior window), D=0.6 (auditable)
    {"channel": "conv_history", "domain": "llm_agent", "C": 0.7, "D": 0.6,
     "success": 0.67, "source": "FP-02 memory/context poisoning"},

    # Tool outputs: C=0.5 (partial), D=0.5 (logged but opaque)
    {"channel": "tool_outputs", "domain": "llm_agent", "C": 0.5, "D": 0.5,
     "success": 0.25, "source": "FP-02 indirect injection via tool outputs"},
]

# ─── Domain 3: Multi-Agent Cascades (FP-15) ──────────────────────────
# Option B confirmed: C = content controllability (always 1.0), D = gate coverage

MULTI_AGENT_DATA = [
    # Implicit trust: C=1.0 (attacker controls content), D=0.0 (no verification)
    {"channel": "delegation_implicit", "domain": "multi_agent", "C": 1.0, "D": 0.0,
     "success": 0.974, "source": "FP-15 implicit trust poison rate (5 seeds)"},

    # Capability-scoped: C=1.0, D=0.8 (architectural — filter exists)
    {"channel": "delegation_capability", "domain": "multi_agent", "C": 1.0, "D": 0.8,
     "success": 0.908, "source": "FP-15 capability-scoped poison rate (5 seeds)"},

    # Zero-trust P_verify=0.8: C=1.0, D=1.0 (every delegation verified)
    {"channel": "delegation_zerotrust_08", "domain": "multi_agent", "C": 1.0, "D": 1.0,
     "success": 0.583, "source": "FP-15 zero-trust P_verify=0.8 poison rate (5 seeds)"},

    # Zero-trust at different P_verify levels (sensitivity analysis from FP-15)
    {"channel": "delegation_zerotrust_06", "domain": "multi_agent", "C": 1.0, "D": 0.75,
     "success": 0.771, "source": "FP-15 zero-trust P_verify=0.6"},
    {"channel": "delegation_zerotrust_03", "domain": "multi_agent", "C": 1.0, "D": 0.375,
     "success": 0.911, "source": "FP-15 zero-trust P_verify=0.3"},
    {"channel": "delegation_zerotrust_10", "domain": "multi_agent", "C": 1.0, "D": 1.0,
     "success": 0.207, "source": "FP-15 zero-trust P_verify=1.0 (perfect verification)"},

    # Topology variations (hierarchical vs flat vs star at two-of-three constraint)
    {"channel": "topo_hierarchical", "domain": "multi_agent", "C": 1.0, "D": 0.9,
     "success": 0.639, "source": "FP-15 two-of-three hierarchical"},
    {"channel": "topo_star", "domain": "multi_agent", "C": 1.0, "D": 0.9,
     "success": 0.569, "source": "FP-15 two-of-three star"},
    {"channel": "topo_flat", "domain": "multi_agent", "C": 1.0, "D": 0.9,
     "success": 0.517, "source": "FP-15 two-of-three flat"},
]


def collect_all():
    """Return all evidence as a list of dicts."""
    return RL_DATA + LLM_AGENT_DATA + MULTI_AGENT_DATA


def save_evidence(output_dir="outputs"):
    """Save evidence to JSON for reproducibility."""
    os.makedirs(output_dir, exist_ok=True)
    data = collect_all()
    path = os.path.join(output_dir, "evidence.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved {len(data)} data points to {path}")

    # Summary by domain
    domains = {}
    for d in data:
        dom = d["domain"]
        if dom not in domains:
            domains[dom] = []
        domains[dom].append(d)

    for dom, points in sorted(domains.items()):
        print(f"  {dom}: {len(points)} data points")

    return data


if __name__ == "__main__":
    save_evidence()
