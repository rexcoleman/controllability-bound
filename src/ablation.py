#!/usr/bin/env python3
"""Ablation study and baseline comparisons for controllability bound.

Tests novel component isolation (A5): is the separate C,D decomposition
the active ingredient, or do simpler models suffice?

Ablations:
1. Remove C term (D-only model)
2. Remove D term (C-only model)
3. Product model C·(1-D) vs separate C, (1-D)
4. Additive vs multiplicative structure
5. With vs without interaction terms

Baselines:
- Naive mean predictor
- Best single-feature predictor
- Random predictor
"""

import json
import os

import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_all_data():
    """Load security evidence + Blotto data."""
    with open(os.path.join(SCRIPT_DIR, "..", "outputs", "evidence.json")) as f:
        security = json.load(f)
    with open(os.path.join(SCRIPT_DIR, "..", "outputs", "blotto_conditions.json")) as f:
        blotto = json.load(f)
    return security, blotto


def r_squared(y_true, y_pred):
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0


def ols_fit(X, y):
    beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    return beta, X @ beta


def run_ablation(C, D, y, label):
    """Run all ablation variants on a dataset."""
    n = len(y)
    results = {}

    # Full model: y = w0 + w1*C + w2*(1-D)
    X_full = np.column_stack([np.ones(n), C, 1 - D])
    beta_full, y_pred_full = ols_fit(X_full, y)
    results["full_separate"] = {
        "r2": r_squared(y, y_pred_full),
        "beta": beta_full.tolist(),
        "description": "w0 + w1*C + w2*(1-D)",
    }

    # Ablation 1: Remove C (D-only)
    X_d = np.column_stack([np.ones(n), 1 - D])
    _, y_pred_d = ols_fit(X_d, y)
    results["ablation_remove_C"] = {
        "r2": r_squared(y, y_pred_d),
        "description": "w0 + w2*(1-D) — C removed",
        "delta_from_full": r_squared(y, y_pred_full) - r_squared(y, y_pred_d),
    }

    # Ablation 2: Remove D (C-only)
    X_c = np.column_stack([np.ones(n), C])
    _, y_pred_c = ols_fit(X_c, y)
    results["ablation_remove_D"] = {
        "r2": r_squared(y, y_pred_c),
        "description": "w0 + w1*C — D removed",
        "delta_from_full": r_squared(y, y_pred_full) - r_squared(y, y_pred_c),
    }

    # Ablation 3: Product model C*(1-D)
    X_prod = np.column_stack([np.ones(n), C * (1 - D)])
    _, y_pred_prod = ols_fit(X_prod, y)
    results["product_model"] = {
        "r2": r_squared(y, y_pred_prod),
        "description": "w0 + w1*C*(1-D) — original conjecture",
        "delta_from_full": r_squared(y, y_pred_full) - r_squared(y, y_pred_prod),
    }

    # Ablation 4: Interaction model
    X_int = np.column_stack([np.ones(n), C, 1 - D, C * (1 - D)])
    _, y_pred_int = ols_fit(X_int, y)
    results["interaction_model"] = {
        "r2": r_squared(y, y_pred_int),
        "description": "w0 + w1*C + w2*(1-D) + w3*C*(1-D)",
        "delta_from_full": r_squared(y, y_pred_int) - r_squared(y, y_pred_full),
    }

    # Baseline: naive mean
    results["baseline_naive"] = {
        "r2": 0.0,
        "description": "predict mean(y)",
    }

    # Baseline: random
    rng = np.random.RandomState(42)
    y_rand = rng.uniform(0, 1, n)
    results["baseline_random"] = {
        "r2": r_squared(y, y_rand),
        "description": "random predictions",
    }

    return results


def bootstrap_delta_ci(C, D, y, n_boot=10000, seed=42):
    """Bootstrap CI for R²(separate) - R²(product)."""
    rng = np.random.RandomState(seed)
    n = len(y)
    deltas = []
    for _ in range(n_boot):
        idx = rng.choice(n, n, replace=True)
        Ci, Di, yi = C[idx], D[idx], y[idx]

        X_sep = np.column_stack([np.ones(n), Ci, 1 - Di])
        X_prod = np.column_stack([np.ones(n), Ci * (1 - Di)])

        _, yp_sep = ols_fit(X_sep, yi)
        _, yp_prod = ols_fit(X_prod, yi)

        deltas.append(r_squared(yi, yp_sep) - r_squared(yi, yp_prod))

    deltas = sorted(deltas)
    return deltas[int(0.025 * n_boot)], deltas[int(0.975 * n_boot)]


def main():
    security, blotto = load_all_data()

    print("=" * 70)
    print("  Ablation Study — Novel Component Isolation (A5)")
    print("=" * 70)
    print()

    all_ablations = {}

    # Security domains
    domains = {}
    for e in security:
        dom = e["domain"]
        if dom not in domains:
            domains[dom] = {"C": [], "D": [], "y": []}
        domains[dom]["C"].append(e["C"])
        domains[dom]["D"].append(e["D"])
        domains[dom]["y"].append(e["success"])

    for dom, data in sorted(domains.items()):
        C = np.array(data["C"])
        D = np.array(data["D"])
        y = np.array(data["y"])
        results = run_ablation(C, D, y, dom)
        all_ablations[dom] = results

        print(f"--- {dom} (n={len(y)}) ---")
        for name, r in sorted(results.items(), key=lambda x: -x[1]["r2"]):
            delta = r.get("delta_from_full", "")
            delta_str = f"  (Δ={delta:+.4f})" if isinstance(delta, float) else ""
            print(f"  {r['r2']:>7.4f}  {r['description']}{delta_str}")
        print()

    # All security combined
    C_all = np.array([e["C"] for e in security])
    D_all = np.array([e["D"] for e in security])
    y_all = np.array([e["success"] for e in security])
    results_all = run_ablation(C_all, D_all, y_all, "all_security")
    all_ablations["all_security"] = results_all

    # Bootstrap CI for the key comparison
    ci_lo, ci_hi = bootstrap_delta_ci(C_all, D_all, y_all)

    print(f"--- ALL SECURITY (n={len(y_all)}) ---")
    for name, r in sorted(results_all.items(), key=lambda x: -x[1]["r2"]):
        delta = r.get("delta_from_full", "")
        delta_str = f"  (Δ={delta:+.4f})" if isinstance(delta, float) else ""
        print(f"  {r['r2']:>7.4f}  {r['description']}{delta_str}")
    print(f"\n  Bootstrap 95% CI for R²(separate) - R²(product): [{ci_lo:.4f}, {ci_hi:.4f}]")
    print()

    # Blotto
    C_b = np.array([c["C"] for c in blotto])
    D_b = np.array([c["D"] for c in blotto])
    y_b = np.array([c["mean_bf_fraction"] for c in blotto])
    results_b = run_ablation(C_b, D_b, y_b, "blotto")
    all_ablations["blotto"] = results_b

    ci_lo_b, ci_hi_b = bootstrap_delta_ci(C_b, D_b, y_b)

    print(f"--- BLOTTO (n={len(y_b)}) ---")
    for name, r in sorted(results_b.items(), key=lambda x: -x[1]["r2"]):
        delta = r.get("delta_from_full", "")
        delta_str = f"  (Δ={delta:+.4f})" if isinstance(delta, float) else ""
        print(f"  {r['r2']:>7.4f}  {r['description']}{delta_str}")
    print(f"\n  Bootstrap 95% CI for R²(separate) - R²(product): [{ci_lo_b:.4f}, {ci_hi_b:.4f}]")
    print()

    # Novel component isolation verdict
    print("=" * 70)
    print("  Novel Component Isolation Verdict (A5)")
    print("=" * 70)
    print()
    print("  Question: Is the separate C,D decomposition the active ingredient?")
    print()

    for dom in sorted(all_ablations.keys()):
        res = all_ablations[dom]
        sep = res["full_separate"]["r2"]
        prod = res["product_model"]["r2"]
        c_only = res["ablation_remove_D"]["r2"]
        d_only = res["ablation_remove_C"]["r2"]
        print(f"  {dom}:")
        print(f"    Separate (C + D):  R²={sep:.4f}")
        print(f"    Product (C·(1-D)): R²={prod:.4f}")
        print(f"    C contribution:    R²(full) - R²(D-only) = {sep - d_only:+.4f}")
        print(f"    D contribution:    R²(full) - R²(C-only) = {sep - c_only:+.4f}")
        print(f"    Separation gain:   R²(separate) - R²(product) = {sep - prod:+.4f}")
        dominant = "D (observability)" if d_only > c_only else "C (controllability)"
        print(f"    Dominant factor:   {dominant}")
        print()

    # Save
    def np_clean(obj):
        if isinstance(obj, (np.floating, np.float64)):
            return float(obj)
        if isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        raise TypeError(f"Not serializable: {type(obj)}")

    os.makedirs("outputs", exist_ok=True)
    with open("outputs/ablation_results.json", "w") as f:
        json.dump(all_ablations, f, indent=2, default=np_clean)
    print("Saved to outputs/ablation_results.json")


if __name__ == "__main__":
    main()
