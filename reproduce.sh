#!/usr/bin/env bash
# reproduce.sh — Reproduce all experiments for controllability-bound
# Usage: bash reproduce.sh [--skip-existing] [--quick]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Controllability Bound — Reproduction ==="
echo "Date: $(date -Iseconds)"
echo ""

# Check lock_commit
if grep -q "TO BE SET" EXPERIMENTAL_DESIGN.md 2>/dev/null; then
    echo "WARN: lock_commit not yet set in EXPERIMENTAL_DESIGN.md"
fi

# Phase 1: Collect and normalize existing project data
echo "--- Phase 1: Data Collection ---"
python3 src/collect_evidence.py --all
echo ""

# Phase 2: Fit controllability bound
echo "--- Phase 2: Bound Fitting ---"
python3 src/fit_bound.py --domains rl_agent llm_agent multi_agent cascade
echo ""

# Phase 3: Game-theoretic transfer test
echo "--- Phase 3: Transfer Test ---"
python3 src/game_theoretic_test.py --games 1000 --seeds 5
echo ""

# Phase 4: Ablation and baseline comparison
echo "--- Phase 4: Ablation ---"
python3 src/ablation.py --all
echo ""

# Phase 5: Score and package
echo "--- Phase 5: Results ---"
python3 src/analyze_results.py
echo ""

echo "=== Reproduction Complete ==="
