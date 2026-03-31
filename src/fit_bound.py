#!/usr/bin/env python3
"""Fit 3 competing controllability bound models and compare R² values.

Model 1 (Additive):      E[attack] = Σ wᵢ · C(cᵢ) · (1 - D(cᵢ))
Model 2 (Multiplicative): E[attack] = Π [C(cᵢ) · (1 - D(cᵢ))]^wᵢ
Model 3 (Additive + Interactions): E[attack] = Σ wᵢ·C·(1-D) + Σ γᵢⱼ·C(cᵢ)·C(cⱼ)

Baselines:
- Naive: predict mean attack success
- Single-feature: best of C alone or (1-D) alone
"""

import json
import os
import sys

import numpy as np
from scipy import stats
from scipy.optimize import minimize

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_evidence():
    path = os.path.join(SCRIPT_DIR, "..", "outputs", "evidence.json")
    with open(path) as f:
        return json.load(f)


def prepare_data(evidence, domain=None):
    """Extract C, D, success arrays. Optionally filter by domain."""
    if domain:
        evidence = [e for e in evidence if e["domain"] == domain]
    C = np.array([e["C"] for e in evidence])
    D = np.array([e["D"] for e in evidence])
    y = np.array([e["success"] for e in evidence])
    return C, D, y


def r_squared(y_true, y_pred):
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    if ss_tot == 0:
        return 0.0
    return 1.0 - ss_res / ss_tot


def fit_additive(C, D, y):
    """Model 1: y = w0 + w1 * C * (1 - D). OLS regression."""
    X = C * (1 - D)
    X_design = np.column_stack([np.ones_like(X), X])
    # OLS
    beta, residuals, rank, sv = np.linalg.lstsq(X_design, y, rcond=None)
    y_pred = X_design @ beta
    r2 = r_squared(y, y_pred)
    return {"model": "additive", "beta": beta.tolist(), "r2": r2, "y_pred": y_pred}


def fit_multiplicative(C, D, y):
    """Model 2: y = a * Π [C(cᵢ) · (1 - D(cᵢ))]^w.
    For single-channel data points, this reduces to y = a * [C*(1-D)]^w.
    Fit in log-space where possible."""
    X = C * (1 - D)
    # Avoid log(0) — filter out zero X values
    mask = X > 1e-10
    if mask.sum() < 3:
        return {"model": "multiplicative", "beta": [0, 0], "r2": -1.0, "y_pred": np.zeros_like(y)}

    # Fit: log(y) = log(a) + w * log(X)
    y_safe = np.clip(y[mask], 1e-10, None)
    log_X = np.log(X[mask])
    log_y = np.log(y_safe)
    X_design = np.column_stack([np.ones_like(log_X), log_X])
    beta_log, _, _, _ = np.linalg.lstsq(X_design, log_y, rcond=None)

    # Predict in original space
    y_pred = np.zeros_like(y)
    y_pred[mask] = np.exp(X_design @ beta_log)
    # For zero-X points, predict 0
    r2 = r_squared(y, y_pred)
    return {"model": "multiplicative", "beta": [np.exp(beta_log[0]), beta_log[1]],
            "r2": r2, "y_pred": y_pred}


def fit_interaction(C, D, y):
    """Model 3: y = w0 + w1*C*(1-D) + w2*C² (interaction proxy).
    Since data points are per-channel (not multi-channel systems), the
    pairwise interaction Σ γᵢⱼ·C(cᵢ)·C(cⱼ) reduces to a C² term for
    self-interaction (within-channel non-linearity)."""
    X1 = C * (1 - D)
    X2 = C * C  # Interaction / non-linearity term
    X_design = np.column_stack([np.ones_like(X1), X1, X2])
    beta, _, _, _ = np.linalg.lstsq(X_design, y, rcond=None)
    y_pred = X_design @ beta
    r2 = r_squared(y, y_pred)
    return {"model": "interaction", "beta": beta.tolist(), "r2": r2, "y_pred": y_pred}


def fit_naive(y):
    """Baseline: predict mean."""
    y_pred = np.full_like(y, np.mean(y))
    r2 = 0.0  # By definition
    return {"model": "naive_mean", "r2": r2, "y_pred": y_pred}


def fit_single_feature(C, D, y):
    """Baseline: best single feature (C alone, D alone, or 1-D alone)."""
    results = []

    # C alone
    X = np.column_stack([np.ones_like(C), C])
    beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    y_pred = X @ beta
    results.append(("C_alone", r_squared(y, y_pred), beta.tolist(), y_pred))

    # (1-D) alone
    X = np.column_stack([np.ones_like(D), 1 - D])
    beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    y_pred = X @ beta
    results.append(("1-D_alone", r_squared(y, y_pred), beta.tolist(), y_pred))

    # C*(1-D) alone (same features as additive but labeled as single-feature)
    X_cd = C * (1 - D)
    X = np.column_stack([np.ones_like(X_cd), X_cd])
    beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    y_pred = X @ beta
    results.append(("C*(1-D)_alone", r_squared(y, y_pred), beta.tolist(), y_pred))

    best = max(results, key=lambda x: x[1])
    return {"model": f"single_feature ({best[0]})", "r2": best[1],
            "beta": best[2], "y_pred": best[3], "all_features": {r[0]: r[1] for r in results}}


def bootstrap_r2_ci(C, D, y, fit_fn, n_boot=10000, seed=42):
    """Bootstrap 95% CI for R²."""
    rng = np.random.RandomState(seed)
    n = len(y)
    r2s = []
    for _ in range(n_boot):
        idx = rng.choice(n, n, replace=True)
        result = fit_fn(C[idx], D[idx], y[idx])
        r2s.append(result["r2"])
    r2s = sorted(r2s)
    lo = r2s[int(0.025 * n_boot)]
    hi = r2s[int(0.975 * n_boot)]
    return lo, hi


def permutation_test_r2(C, D, y, fit_fn1, fit_fn2, n_perm=10000, seed=42):
    """Permutation test: is R²(model1) > R²(model2)?"""
    r2_1 = fit_fn1(C, D, y)["r2"]
    r2_2 = fit_fn2(C, D, y)["r2"]
    observed_diff = r2_1 - r2_2

    rng = np.random.RandomState(seed)
    count = 0
    for _ in range(n_perm):
        perm = rng.permutation(len(y))
        y_perm = y[perm]
        diff = fit_fn1(C, D, y_perm)["r2"] - fit_fn2(C, D, y_perm)["r2"]
        if diff >= observed_diff:
            count += 1
    p_value = count / n_perm
    return observed_diff, p_value


def compute_tightness(y_true, y_pred):
    """Tightness ratio: predicted / observed. For a bound, should be >= 1.0."""
    mask = y_true > 0.01  # Avoid division by near-zero
    if mask.sum() == 0:
        return np.nan, np.nan
    ratios = y_pred[mask] / y_true[mask]
    return np.mean(ratios), np.std(ratios)


def fit_all(evidence, domain=None):
    """Fit all models on given data and return results."""
    C, D, y = prepare_data(evidence, domain)
    n = len(y)
    if n < 3:
        return {"domain": domain or "all", "n": n, "error": "insufficient data"}

    label = domain or "all_domains"

    additive = fit_additive(C, D, y)
    multiplicative = fit_multiplicative(C, D, y)
    interaction = fit_interaction(C, D, y)
    naive = fit_naive(y)
    single = fit_single_feature(C, D, y)

    # Bootstrap CIs for additive model
    add_ci_lo, add_ci_hi = bootstrap_r2_ci(C, D, y, fit_additive)

    # Tightness for additive model
    tight_mean, tight_std = compute_tightness(y, additive["y_pred"])

    # Interaction improvement
    interaction_improvement = interaction["r2"] - additive["r2"]

    return {
        "domain": label,
        "n": n,
        "additive_r2": round(additive["r2"], 4),
        "additive_ci": [round(add_ci_lo, 4), round(add_ci_hi, 4)],
        "additive_beta": additive["beta"],
        "multiplicative_r2": round(multiplicative["r2"], 4),
        "interaction_r2": round(interaction["r2"], 4),
        "interaction_improvement": round(interaction_improvement, 4),
        "interaction_beta": interaction["beta"],
        "naive_r2": round(naive["r2"], 4),
        "single_feature_r2": round(single["r2"], 4),
        "single_feature_name": single["model"],
        "single_feature_all": single.get("all_features", {}),
        "tightness_mean": round(tight_mean, 3) if not np.isnan(tight_mean) else None,
        "tightness_std": round(tight_std, 3) if not np.isnan(tight_std) else None,
        "additive_beats_single": additive["r2"] > single["r2"],
        "additive_beats_multiplicative": additive["r2"] > multiplicative["r2"],
    }


def main():
    evidence = load_evidence()
    domains = sorted(set(e["domain"] for e in evidence))

    print("=" * 70)
    print("  Controllability Bound — Model Fitting Results")
    print("=" * 70)
    print()

    all_results = []

    # Per-domain fits
    for domain in domains:
        result = fit_all(evidence, domain)
        all_results.append(result)
        print(f"--- {domain} (n={result['n']}) ---")
        print(f"  Additive R²:       {result['additive_r2']:.4f}  CI: [{result['additive_ci'][0]:.4f}, {result['additive_ci'][1]:.4f}]")
        print(f"  Multiplicative R²: {result['multiplicative_r2']:.4f}")
        print(f"  Interaction R²:    {result['interaction_r2']:.4f}  (improvement: {result['interaction_improvement']:+.4f})")
        print(f"  Naive (mean) R²:   {result['naive_r2']:.4f}")
        print(f"  Single-feature R²: {result['single_feature_r2']:.4f}  ({result['single_feature_name']})")
        if result.get("single_feature_all"):
            for fname, fr2 in result["single_feature_all"].items():
                print(f"    {fname}: {fr2:.4f}")
        print(f"  Tightness:         {result['tightness_mean']} ± {result['tightness_std']}")
        print(f"  Additive > Single: {result['additive_beats_single']}")
        print(f"  Additive > Mult:   {result['additive_beats_multiplicative']}")
        print()

    # Overall fit (all domains combined)
    overall = fit_all(evidence)
    all_results.append(overall)
    print(f"--- ALL DOMAINS (n={overall['n']}) ---")
    print(f"  Additive R²:       {overall['additive_r2']:.4f}  CI: [{overall['additive_ci'][0]:.4f}, {overall['additive_ci'][1]:.4f}]")
    print(f"  Multiplicative R²: {overall['multiplicative_r2']:.4f}")
    print(f"  Interaction R²:    {overall['interaction_r2']:.4f}  (improvement: {overall['interaction_improvement']:+.4f})")
    print(f"  Naive (mean) R²:   {overall['naive_r2']:.4f}")
    print(f"  Single-feature R²: {overall['single_feature_r2']:.4f}  ({overall['single_feature_name']})")
    if overall.get("single_feature_all"):
        for fname, fr2 in overall["single_feature_all"].items():
            print(f"    {fname}: {fr2:.4f}")
    print(f"  Tightness:         {overall['tightness_mean']} ± {overall['tightness_std']}")
    print()

    # Hypothesis verdicts
    print("=" * 70)
    print("  Hypothesis Verdicts (preliminary — before transfer test)")
    print("=" * 70)
    domains_above_08 = sum(1 for r in all_results if r["domain"] != "all_domains" and r["additive_r2"] > 0.8)
    domains_add_beats_mult = sum(1 for r in all_results if r["domain"] != "all_domains" and r["additive_beats_multiplicative"])
    domains_add_beats_single = sum(1 for r in all_results if r["domain"] != "all_domains" and r["additive_beats_single"])

    print(f"  H-1 (R² > 0.8 in 3+ domains): {domains_above_08}/3 domains — {'SUPPORTED' if domains_above_08 >= 3 else 'PARTIAL' if domains_above_08 >= 1 else 'REFUTED'}")
    print(f"  H-2 (Additive > Multiplicative in 3+ domains): {domains_add_beats_mult}/3 — {'SUPPORTED' if domains_add_beats_mult >= 3 else 'PARTIAL'}")
    print(f"  H-3 (Beats single-feature in 3+ domains): {domains_add_beats_single}/3 — {'SUPPORTED' if domains_add_beats_single >= 3 else 'PARTIAL'}")
    print(f"  H-5a (Interaction improvement > 0.05 in any domain):", end=" ")
    interaction_domains = [r["domain"] for r in all_results if r["domain"] != "all_domains" and r["interaction_improvement"] > 0.05]
    print(f"{'YES in ' + ', '.join(interaction_domains) if interaction_domains else 'NO — channel independence holds'}")
    if overall["tightness_mean"]:
        print(f"  H-5 (Tightness 1.0-3.0): {overall['tightness_mean']:.2f} — {'IN RANGE' if 1.0 <= overall['tightness_mean'] <= 3.0 else 'OUT OF RANGE'}")
    print()

    # Save results (strip y_pred arrays to avoid circular ref)
    os.makedirs("outputs", exist_ok=True)
    saveable = []
    for r in all_results:
        s = {k: v for k, v in r.items()}
        # Remove numpy arrays that can't serialize
        for key in list(s.keys()):
            if isinstance(s[key], np.ndarray):
                del s[key]
        saveable.append(s)

    def np_clean(obj):
        if isinstance(obj, (np.floating, np.float64)):
            return float(obj)
        if isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        raise TypeError(f"Not serializable: {type(obj)}")

    with open("outputs/model_fit_results.json", "w") as f:
        json.dump(saveable, f, indent=2, default=np_clean)
    print("Results saved to outputs/model_fit_results.json")


if __name__ == "__main__":
    main()
