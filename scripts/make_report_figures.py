#!/usr/bin/env python3
"""Generate report figures for controllability bound paper.

4 figures:
1. Model comparison: R² by domain for additive, product, separate models
2. Domain-dependent factor dominance: C vs D contribution by domain
3. Blotto transfer test: win rate vs controllability at different D levels
4. Ablation: R² waterfall showing each component's contribution
"""

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(SCRIPT_DIR, "..", "figures")


def load_data():
    base = os.path.join(SCRIPT_DIR, "..", "outputs")
    with open(os.path.join(base, "model_fit_results.json")) as f:
        model_fit = json.load(f)
    with open(os.path.join(base, "blotto_conditions.json")) as f:
        blotto = json.load(f)
    with open(os.path.join(base, "ablation_results.json")) as f:
        ablation = json.load(f)
    return model_fit, blotto, ablation


def fig1_model_comparison(model_fit):
    """Bar chart: R² by domain for 3 models."""
    domains = []
    r2_product = []
    r2_separate = []
    r2_interaction = []

    # Get per-domain from ablation (which has the separate model)
    # model_fit only has additive (=product), multiplicative, interaction
    # Use ablation_results for the full picture
    with open(os.path.join(SCRIPT_DIR, "..", "outputs", "ablation_results.json")) as f:
        ablation = json.load(f)

    domain_labels = {
        "rl_agent": "RL Agents\n(FP-12)",
        "llm_agent": "LLM Agents\n(FP-02)",
        "multi_agent": "Multi-Agent\n(FP-15)",
        "blotto": "Colonel Blotto\n(Transfer)",
    }

    for dom_key in ["rl_agent", "llm_agent", "multi_agent", "blotto"]:
        if dom_key in ablation:
            a = ablation[dom_key]
            domains.append(domain_labels.get(dom_key, dom_key))
            r2_product.append(max(0, a["product_model"]["r2"]))
            r2_separate.append(max(0, a["full_separate"]["r2"]))
            r2_interaction.append(max(0, a["interaction_model"]["r2"]))

    x = np.arange(len(domains))
    width = 0.25

    fig, ax = plt.subplots(figsize=(10, 6))
    bars1 = ax.bar(x - width, r2_product, width, label="Product: C·(1-D)", color="#d62728", alpha=0.85)
    bars2 = ax.bar(x, r2_separate, width, label="Separate: w₁·C + w₂·(1-D)", color="#2ca02c", alpha=0.85)
    bars3 = ax.bar(x + width, r2_interaction, width, label="Interaction: + w₃·C·(1-D)", color="#1f77b4", alpha=0.85)

    ax.set_ylabel("R²", fontsize=13)
    ax.set_title("Model Comparison Across Domains\nSeparate C,D Outperforms Product C·(1-D)", fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(domains, fontsize=11)
    ax.legend(fontsize=11, loc="upper left")
    ax.set_ylim(0, 1.05)
    ax.axhline(y=0.8, color="gray", linestyle="--", alpha=0.5, label="R²=0.8 threshold")
    ax.grid(axis="y", alpha=0.3)

    # Add value labels
    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            if height > 0.02:
                ax.annotate(f"{height:.2f}", xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=9)

    plt.tight_layout()
    path = os.path.join(OUT_DIR, "fig1_model_comparison.png")
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {path}")


def fig2_factor_dominance(ablation):
    """Stacked bar: C contribution vs D contribution by domain."""
    domain_labels = {
        "rl_agent": "RL Agents",
        "llm_agent": "LLM Agents",
        "multi_agent": "Multi-Agent",
        "blotto": "Blotto (Transfer)",
    }

    domains = []
    c_contribs = []
    d_contribs = []

    for dom_key in ["rl_agent", "llm_agent", "multi_agent", "blotto"]:
        if dom_key in ablation:
            a = ablation[dom_key]
            full_r2 = a["full_separate"]["r2"]
            d_only_r2 = a["ablation_remove_C"]["r2"]
            c_only_r2 = a["ablation_remove_D"]["r2"]

            c_contrib = max(0, full_r2 - d_only_r2)
            d_contrib = max(0, full_r2 - c_only_r2)

            domains.append(domain_labels.get(dom_key, dom_key))
            c_contribs.append(c_contrib)
            d_contribs.append(d_contrib)

    x = np.arange(len(domains))
    width = 0.5

    fig, ax = plt.subplots(figsize=(9, 6))
    bars_c = ax.bar(x, c_contribs, width, label="C contribution (controllability)", color="#ff7f0e", alpha=0.85)
    bars_d = ax.bar(x, d_contribs, width, bottom=c_contribs, label="D contribution (observability gap)", color="#9467bd", alpha=0.85)

    ax.set_ylabel("R² Contribution (ablation delta)", fontsize=13)
    ax.set_title("Domain-Dependent Factor Dominance\nSecurity → Observability-Limited  |  Games → Controllability-Limited", fontsize=13)
    ax.set_xticks(x)
    ax.set_xticklabels(domains, fontsize=12)
    ax.legend(fontsize=11)
    ax.grid(axis="y", alpha=0.3)

    # Add dominant label
    for i, (c, d) in enumerate(zip(c_contribs, d_contribs)):
        dominant = "C > D" if c > d else "D > C" if d > c else "C ≈ D"
        ax.annotate(dominant, xy=(i, c + d + 0.02), ha="center", fontsize=11, fontweight="bold",
                    color="#ff7f0e" if c > d else "#9467bd")

    plt.tight_layout()
    path = os.path.join(OUT_DIR, "fig2_factor_dominance.png")
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {path}")


def fig3_blotto_transfer(blotto):
    """Heatmap or line plot: Blotto win rate vs C at different D levels."""
    # Filter to 5-battlefield games for cleaner visualization
    bf5 = [c for c in blotto if c["n_battlefields"] == 5]

    c_levels = sorted(set(c["C"] for c in bf5))
    d_levels = sorted(set(c["D"] for c in bf5))

    fig, ax = plt.subplots(figsize=(9, 6))

    colors = plt.cm.viridis(np.linspace(0.1, 0.9, len(d_levels)))

    for i, d in enumerate(d_levels):
        points = sorted([c for c in bf5 if c["D"] == d], key=lambda x: x["C"])
        cs = [p["C"] for p in points]
        wins = [p["mean_bf_fraction"] for p in points]
        stds = [p["std_win_rate"] for p in points]
        ax.plot(cs, wins, "o-", color=colors[i], label=f"D={d:.1f}", linewidth=2, markersize=8)

    ax.set_xlabel("Attacker Controllability (C)", fontsize=13)
    ax.set_ylabel("Battlefield Fraction Won", fontsize=13)
    ax.set_title("Colonel Blotto Transfer Test (5 Battlefields, 5 Seeds)\nControllability Dominates; Observability Has Weak Effect", fontsize=13)
    ax.legend(title="Defender\nObservability", fontsize=10, title_fontsize=11)
    ax.set_xlim(0.15, 1.05)
    ax.set_ylim(0.1, 0.6)
    ax.axhline(y=0.5, color="gray", linestyle="--", alpha=0.4, label="Equal resources")
    ax.grid(alpha=0.3)

    plt.tight_layout()
    path = os.path.join(OUT_DIR, "fig3_blotto_transfer.png")
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {path}")


def fig4_ablation_waterfall(ablation):
    """Waterfall chart showing R² contribution of each component (all security)."""
    a = ablation.get("all_security", {})
    if not a:
        print("  SKIP: No all_security ablation data")
        return

    full = a["full_separate"]["r2"]
    c_only = a["ablation_remove_D"]["r2"]
    d_only = a["ablation_remove_C"]["r2"]
    product = a["product_model"]["r2"]
    interaction = a["interaction_model"]["r2"]
    naive = 0.0

    # Waterfall: naive → +C → +D → separate → +interaction
    labels = ["Naive\n(mean)", "+C alone", "+D alone", "Separate\n(C + D)", "+Interaction\nterm"]
    values = [naive, c_only, d_only, full, interaction]
    colors_list = ["#cccccc", "#ff7f0e", "#9467bd", "#2ca02c", "#1f77b4"]

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(range(len(labels)), values, color=colors_list, alpha=0.85, edgecolor="black", linewidth=0.5)

    # Add product model as reference line
    ax.axhline(y=product, color="#d62728", linestyle="--", linewidth=2, alpha=0.7)
    ax.annotate(f"Product C·(1-D)\nR²={product:.3f}", xy=(3.5, product + 0.02),
                color="#d62728", fontsize=10, ha="center")

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_ylabel("R²", fontsize=13)
    ax.set_title("Ablation: Component Contributions to Model Fit (All Security Domains, n=24)\nSeparate C,D Beats Product by +0.42 R²", fontsize=13)
    ax.set_ylim(0, 0.85)
    ax.grid(axis="y", alpha=0.3)

    for bar, val in zip(bars, values):
        ax.annotate(f"{val:.3f}", xy=(bar.get_x() + bar.get_width() / 2, val),
                    xytext=(0, 5), textcoords="offset points", ha="center", fontsize=11, fontweight="bold")

    plt.tight_layout()
    path = os.path.join(OUT_DIR, "fig4_ablation_waterfall.png")
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {path}")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print("Generating report figures...")

    model_fit, blotto, ablation = load_data()

    fig1_model_comparison(model_fit)
    fig2_factor_dominance(ablation)
    fig3_blotto_transfer(blotto)
    fig4_ablation_waterfall(ablation)

    print(f"\nAll figures saved to {OUT_DIR}/")
    print(f"  {len(os.listdir(OUT_DIR))} figures generated at 300 DPI")


if __name__ == "__main__":
    main()
