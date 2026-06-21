#!/usr/bin/env python3
"""Extract QAOA & Grover success probabilities from existing experimental results,
then generate updated comparison figures using success probability."""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent  # qubit-efficient-mvc-grover/
QAOA_RUN_DIR = REPO_ROOT / "src" / "mvc_qaoa" / "experiments" / "run_20260426_111406"
OUTPUT_DIR = REPO_ROOT / "src" / "mvc_qaoa" / "experiments" / "qaoa_vs_grover_comparison"
OUTPUT_DIR.mkdir(exist_ok=True)

GRAPHS = ["K3", "K4", "K5", "K6", "K7"]
OPTIMAL_SIZES = {"K3": 2, "K4": 3, "K5": 4, "K6": 5, "K7": 6}

# LaTeX-formatted display names for figures
DISPLAY_NAMES = {
    "K3": r"$K_3$",
    "K4": r"$K_4$",
    "K5": r"$K_5$",
    "K6": r"$K_6$",
    "K7": r"$K_7$",
}

# ---------------------------------------------------------------------------
# 1. QAOA: total probability of all optimal states
# ---------------------------------------------------------------------------
def extract_qaoa_success(graph: str, p: int):
    """Return total probability of all optimal states from QAOA simulation."""
    path = QAOA_RUN_DIR / graph / f"p{p}" / "results.json"
    with open(path) as f:
        data = json.load(f)

    optimal_covers = set(data["exact"]["optimal_covers"])
    top_8 = data["simulation"]["top_8"]

    total_optimal = sum(
        state["probability"] for state in top_8
        if state["bitstring"] in optimal_covers
    )
    return total_optimal

# ---------------------------------------------------------------------------
# 2. Grover: sum(good_states) / total shots from existing outputs
# ---------------------------------------------------------------------------
def extract_grover_success(results_path: Path):
    with open(results_path) as f:
        data = json.load(f)
    good = data.get("good_states", {})
    counts = data["counts"]
    total = sum(counts.values())
    if total == 0:
        return 0.0
    return sum(good.values()) / total

# Mapping of graph -> pivot -> results.json path
GROVER_ARITH_PATHS = {
    "K3": REPO_ROOT / "src/mvc-solver-1.3.0/outputs/run_20260303_142020/K_3/pivot_3/results.json",
    "K4": REPO_ROOT / "src/mvc-solver-1.3.0/outputs/run_20260303_142020/K_4/pivot_4/results.json",
    "K5": REPO_ROOT / "src/mvc-solver-1.3.0/outputs/run_20260303_142020/K_5/pivot_5/results.json",
    "K6": REPO_ROOT / "src/mvc-solver-1.3.0/outputs/run_20260303_142020/K_6/pivot_6/results.json",
    "K7": REPO_ROOT / "src/mvc-solver-1.3.0/outputs/run_20260303_142020/K_7/pivot_7/results.json",
}

GROVER_DICKE_PATHS = {
    "K3": REPO_ROOT / "src/mvc-solver-1.4.0/outputs/run_20260222_165935_K3_K6/K_3/pivot_3/results.json",
    "K4": REPO_ROOT / "src/mvc-solver-1.4.0/outputs/run_20260222_165935_K3_K6/K_4/pivot_4/results.json",
    "K5": REPO_ROOT / "src/mvc-solver-1.4.0/outputs/run_20260222_165935_K3_K6/K_5/pivot_5/results.json",
    "K6": REPO_ROOT / "src/mvc-solver-1.4.0/outputs/run_20260222_165935_K3_K6/K_6/pivot_6/results.json",
    "K7": REPO_ROOT / "src/mvc-solver-1.4.0/outputs/run_20260222_165935_K3_K6/K_7/pivot_8/results.json",
}

# ---------------------------------------------------------------------------
# Gather all data
# ---------------------------------------------------------------------------
qaoa_success = {g: {} for g in GRAPHS}
for g in GRAPHS:
    for p in [1, 2, 3]:
        qaoa_success[g][p] = extract_qaoa_success(g, p)

arith_success = {g: extract_grover_success(GROVER_ARITH_PATHS[g]) for g in GRAPHS}
dicke_success = {g: extract_grover_success(GROVER_DICKE_PATHS[g]) for g in GRAPHS}

print("Success probabilities:")
for g in GRAPHS:
    print(f"  {g}: QAOA(p1={qaoa_success[g][1]:.3f}, p2={qaoa_success[g][2]:.3f}, p3={qaoa_success[g][3]:.3f}) | "
          f"Arith={arith_success[g]:.3f} | Dicke={dicke_success[g]:.3f}")

# ---------------------------------------------------------------------------
# Figure: Success Probability Comparison
# ---------------------------------------------------------------------------
def plot_success_comparison():
    x = np.arange(len(GRAPHS))
    width = 0.15

    qaoa_p1 = [qaoa_success[g][1] for g in GRAPHS]
    qaoa_p2 = [qaoa_success[g][2] for g in GRAPHS]
    qaoa_p3 = [qaoa_success[g][3] for g in GRAPHS]
    arith_vals = [arith_success[g] for g in GRAPHS]
    dicke_vals = [dicke_success[g] for g in GRAPHS]

    fig, ax = plt.subplots(figsize=(10, 5))

    ax.bar(x - 2*width, qaoa_p1, width, label="QAOA $p=1$", color="#5B9BD5")
    ax.bar(x - width,   qaoa_p2, width, label="QAOA $p=2$", color="#ED7D31")
    ax.bar(x,           qaoa_p3, width, label="QAOA $p=3$", color="#70AD47")
    ax.bar(x + width,   dicke_vals, width, label="Dicke-state (Ours)", color="#0000FF")
    ax.bar(x + 2*width, arith_vals, width, label="Arithmetic-based (Ours)", color="#800080")

    ax.set_ylabel("Probability of Optimal Solution", fontsize=12)
    ax.set_title("Success Probability: QAOA vs Grover Oracle Architectures", fontsize=13)
    ax.set_xticks(x)
    ax.set_xticklabels([DISPLAY_NAMES[g] for g in GRAPHS])
    ax.set_ylim(0, 1.05)
    ax.axhline(y=1.0, color="black", linestyle="--", linewidth=0.8, alpha=0.3)
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig_success_probability_comparison.png", dpi=300)
    plt.close(fig)
    print(f"Saved success-probability comparison -> {OUTPUT_DIR / 'fig_success_probability_comparison.png'}")

plot_success_comparison()

# Save JSON summary
summary = []
for g in GRAPHS:
    summary.append({
        "graph": g,
        "qaoa_p1_success": round(qaoa_success[g][1], 4),
        "qaoa_p2_success": round(qaoa_success[g][2], 4),
        "qaoa_p3_success": round(qaoa_success[g][3], 4),
        "grover_arith_success": round(arith_success[g], 4),
        "grover_dicke_success": round(dicke_success[g], 4),
    })

with open(OUTPUT_DIR / "success_probability_summary.json", "w") as f:
    json.dump(summary, f, indent=2)

print("\nDone!")
