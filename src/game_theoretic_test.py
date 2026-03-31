#!/usr/bin/env python3
"""Colonel Blotto game — transfer test for controllability bound.

Tests whether the additive controllability bound, derived from security domains,
predicts outcomes in a game-theoretic setting.

Controllability mapping:
  - C = troops_available / max_troops (resource allocation freedom)
  - D = observed_battlefields / total_battlefields (information about opponent)
  - Success = win rate over many games

We simulate games at 50 conditions (5 C levels × 5 D levels × 2 game sizes)
with 100 games per condition = 5,000 total games.
"""

import json
import os

import numpy as np


def colonel_blotto_game(
    n_battlefields, troops_a, troops_b, info_a=0.0, info_b=0.0, rng=None
):
    """Simulate one Colonel Blotto game.

    Args:
        n_battlefields: number of battlefields
        troops_a, troops_b: total troops for each player
        info_a: fraction of B's allocation visible to A before committing (D for A)
        info_b: fraction of A's allocation visible to B before committing (D for B)
        rng: numpy random state

    Returns:
        (wins_a, wins_b, draws) — count of battlefields won by each
    """
    if rng is None:
        rng = np.random.RandomState()

    # Player B allocates first (or simultaneously if no info)
    # Allocation: Dirichlet-distributed (random mixed strategy)
    alloc_b_raw = rng.dirichlet(np.ones(n_battlefields)) * troops_b

    # Player A observes info_a fraction of B's allocation
    n_observed = int(info_a * n_battlefields)
    observed_indices = rng.choice(n_battlefields, size=n_observed, replace=False) if n_observed > 0 else []

    # Player A allocates: if they observe some battlefields, they can
    # concentrate on unobserved ones (rational response)
    if n_observed > 0 and n_observed < n_battlefields:
        # Rational strategy: match observed battlefields + 1, concentrate remaining on unobserved
        alloc_a = np.zeros(n_battlefields)
        troops_used = 0.0
        for idx in observed_indices:
            # Match B's allocation + small margin (if affordable)
            match_troops = min(alloc_b_raw[idx] + 0.1, troops_a * 0.3 / max(n_observed, 1))
            alloc_a[idx] = match_troops
            troops_used += match_troops

        remaining = troops_a - troops_used
        unobserved = [i for i in range(n_battlefields) if i not in observed_indices]
        if unobserved and remaining > 0:
            # Spread remaining troops across unobserved battlefields
            alloc_unobs = rng.dirichlet(np.ones(len(unobserved))) * remaining
            for i, idx in enumerate(unobserved):
                alloc_a[idx] = alloc_unobs[i]
    else:
        # No info: random allocation
        alloc_a = rng.dirichlet(np.ones(n_battlefields)) * troops_a

    # Player B also gets info about A (for symmetry)
    # For simplicity, B doesn't adjust (B allocates first)

    # Count wins
    wins_a = np.sum(alloc_a > alloc_b_raw)
    wins_b = np.sum(alloc_b_raw > alloc_a)
    draws = n_battlefields - wins_a - wins_b

    return int(wins_a), int(wins_b), int(draws)


def simulate_condition(n_battlefields, c_level, d_level, n_games=100, seed=42):
    """Run n_games at a specific controllability/observability level.

    Args:
        n_battlefields: game size
        c_level: attacker controllability = troops_a / max_troops (0.2 to 1.0)
        d_level: defender observability = observed_battlefields / total (0.0 to 0.8)
        n_games: games per condition
        seed: random seed

    Returns:
        dict with win_rate, avg_battlefields_won, etc.
    """
    rng = np.random.RandomState(seed)
    max_troops = 100

    # Attacker (Player A) has C * max_troops
    troops_a = c_level * max_troops
    # Defender (Player B) always has max_troops (disadvantaged attacker tests bound)
    troops_b = max_troops

    # Observability: attacker sees D fraction of defender's allocation
    info_a = d_level

    total_wins_a = 0
    total_bf_won_a = 0

    for _ in range(n_games):
        wa, wb, d = colonel_blotto_game(
            n_battlefields, troops_a, troops_b, info_a=info_a, info_b=0.0, rng=rng
        )
        total_bf_won_a += wa
        if wa > wb:
            total_wins_a += 1

    win_rate = total_wins_a / n_games
    avg_bf_won = total_bf_won_a / (n_games * n_battlefields)

    return {
        "n_battlefields": n_battlefields,
        "C": c_level,
        "D": d_level,
        "troops_a": troops_a,
        "troops_b": troops_b,
        "n_games": n_games,
        "win_rate": round(win_rate, 4),
        "avg_battlefield_fraction_won": round(avg_bf_won, 4),
        "seed": seed,
    }


def run_transfer_test(n_games=100, seeds=5):
    """Run full transfer test: 50 conditions × seeds."""
    c_levels = [0.2, 0.4, 0.6, 0.8, 1.0]
    d_levels = [0.0, 0.2, 0.4, 0.6, 0.8]
    game_sizes = [5, 10]  # 5 and 10 battlefields

    all_results = []
    conditions = []

    for n_bf in game_sizes:
        for c in c_levels:
            for d in d_levels:
                # Run across seeds and average
                seed_results = []
                for s in range(seeds):
                    result = simulate_condition(n_bf, c, d, n_games=n_games, seed=42 + s)
                    seed_results.append(result)
                    all_results.append(result)

                # Aggregate across seeds
                mean_win = np.mean([r["win_rate"] for r in seed_results])
                std_win = np.std([r["win_rate"] for r in seed_results])
                mean_bf = np.mean([r["avg_battlefield_fraction_won"] for r in seed_results])

                conditions.append({
                    "n_battlefields": n_bf,
                    "C": c,
                    "D": d,
                    "mean_win_rate": round(float(mean_win), 4),
                    "std_win_rate": round(float(std_win), 4),
                    "mean_bf_fraction": round(float(mean_bf), 4),
                    "n_seeds": seeds,
                    "games_per_seed": n_games,
                })

    return conditions, all_results


def fit_bound_on_blotto(conditions):
    """Fit the additive bound to Blotto outcomes and compare models."""
    C = np.array([c["C"] for c in conditions])
    D = np.array([c["D"] for c in conditions])
    # Use battlefield fraction won as the "attack success" metric
    # (more continuous than win_rate which is binary per game)
    y = np.array([c["mean_bf_fraction"] for c in conditions])

    def r_squared(y_true, y_pred):
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        return 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    # Model 1: Additive — y = w0 + w1 * C * (1-D)
    X1 = np.column_stack([np.ones_like(C), C * (1 - D)])
    beta1, _, _, _ = np.linalg.lstsq(X1, y, rcond=None)
    y_pred1 = X1 @ beta1
    r2_add = r_squared(y, y_pred1)

    # Model 2: Multiplicative (log-space)
    X_cd = C * (1 - D)
    mask = X_cd > 1e-10
    y_safe = np.clip(y[mask], 1e-10, None)
    X2 = np.column_stack([np.ones(mask.sum()), np.log(X_cd[mask])])
    beta2, _, _, _ = np.linalg.lstsq(X2, np.log(y_safe), rcond=None)
    y_pred2 = np.zeros_like(y)
    y_pred2[mask] = np.exp(X2 @ beta2)
    r2_mult = r_squared(y, y_pred2)

    # Model 3: Additive + Interaction
    X3 = np.column_stack([np.ones_like(C), C * (1 - D), C * C])
    beta3, _, _, _ = np.linalg.lstsq(X3, y, rcond=None)
    y_pred3 = X3 @ beta3
    r2_int = r_squared(y, y_pred3)

    # Baselines
    r2_naive = 0.0

    # Single features
    for name, feat in [("C_alone", C), ("1-D_alone", 1 - D), ("C*(1-D)", C * (1 - D))]:
        Xf = np.column_stack([np.ones_like(feat), feat])
        bf, _, _, _ = np.linalg.lstsq(Xf, y, rcond=None)
        r2f = r_squared(y, Xf @ bf)
        print(f"    {name}: R² = {r2f:.4f}")

    # Two-feature model: C and D separately
    X_sep = np.column_stack([np.ones_like(C), C, 1 - D])
    beta_sep, _, _, _ = np.linalg.lstsq(X_sep, y, rcond=None)
    y_pred_sep = X_sep @ beta_sep
    r2_sep = r_squared(y, y_pred_sep)

    # Tightness
    tight_mask = y > 0.01
    tightness = np.mean(y_pred1[tight_mask] / y[tight_mask])

    # Prediction error (H-4: within 15% of observed)
    abs_errors = np.abs(y_pred1 - y)
    rel_errors = abs_errors[tight_mask] / y[tight_mask]
    mean_abs_error = float(np.mean(abs_errors))
    mean_rel_error = float(np.mean(rel_errors))
    within_15pct = float(np.mean(rel_errors < 0.15))

    return {
        "additive_r2": round(float(r2_add), 4),
        "multiplicative_r2": round(float(r2_mult), 4),
        "interaction_r2": round(float(r2_int), 4),
        "interaction_improvement": round(float(r2_int - r2_add), 4),
        "separate_CD_r2": round(float(r2_sep), 4),
        "additive_beta": [round(float(b), 4) for b in beta1],
        "separate_beta": [round(float(b), 4) for b in beta_sep],
        "tightness": round(float(tightness), 3),
        "mean_abs_error": round(mean_abs_error, 4),
        "mean_rel_error": round(mean_rel_error, 4),
        "fraction_within_15pct": round(within_15pct, 4),
        "n_conditions": len(conditions),
    }


def main():
    print("=" * 70)
    print("  Colonel Blotto Transfer Test")
    print("=" * 70)
    print()

    print("Running 5,000 games (50 conditions × 100 games × 5 seeds)...")
    conditions, all_results = run_transfer_test(n_games=100, seeds=5)
    total_games = len(all_results) * 100
    print(f"  Completed: {len(conditions)} conditions, {total_games:,} total games")
    print()

    # Print condition table
    print("--- Condition Results (mean across seeds) ---")
    print(f"  {'BF':>3} {'C':>5} {'D':>5} {'Win%':>7} {'±':>6} {'BF_frac':>8}")
    for c in conditions:
        print(f"  {c['n_battlefields']:>3} {c['C']:>5.1f} {c['D']:>5.1f} "
              f"{c['mean_win_rate']:>7.3f} {c['std_win_rate']:>6.3f} {c['mean_bf_fraction']:>8.4f}")
    print()

    # Fit bound
    print("--- Bound Fit on Blotto Data ---")
    fit = fit_bound_on_blotto(conditions)
    print(f"  Additive R²:       {fit['additive_r2']:.4f}")
    print(f"  Multiplicative R²: {fit['multiplicative_r2']:.4f}")
    print(f"  Interaction R²:    {fit['interaction_r2']:.4f} (improvement: {fit['interaction_improvement']:+.4f})")
    print(f"  Separate C,D R²:   {fit['separate_CD_r2']:.4f}")
    print(f"  Additive beta:     intercept={fit['additive_beta'][0]:.4f}, slope={fit['additive_beta'][1]:.4f}")
    print(f"  Separate beta:     intercept={fit['separate_beta'][0]:.4f}, C={fit['separate_beta'][1]:.4f}, (1-D)={fit['separate_beta'][2]:.4f}")
    print(f"  Tightness:         {fit['tightness']:.3f}")
    print(f"  Mean abs error:    {fit['mean_abs_error']:.4f}")
    print(f"  Mean rel error:    {fit['mean_rel_error']:.4f}")
    print(f"  Within 15%:        {fit['fraction_within_15pct']:.1%}")
    print()

    # H-4 verdict
    print("--- H-4 Verdict (Game-Theoretic Transfer) ---")
    if fit["fraction_within_15pct"] >= 0.5:
        print(f"  SUPPORTED: {fit['fraction_within_15pct']:.0%} of predictions within 15% of observed")
    else:
        print(f"  PARTIAL/REFUTED: Only {fit['fraction_within_15pct']:.0%} within 15%")
    print(f"  Mean relative error: {fit['mean_rel_error']:.1%}")
    print()

    # Save
    os.makedirs("outputs", exist_ok=True)
    with open("outputs/blotto_conditions.json", "w") as f:
        json.dump(conditions, f, indent=2)
    with open("outputs/blotto_fit.json", "w") as f:
        json.dump(fit, f, indent=2)
    print(f"Saved to outputs/blotto_conditions.json and outputs/blotto_fit.json")


if __name__ == "__main__":
    main()
