#!/usr/bin/env python3
"""Extract Grover circuit metrics and generate QAOA vs Grover comparison figures."""

import sys
import os
import json
import subprocess
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# ---------------------------------------------------------------------------
# Graph definitions (must match QAOA benchmark exactly)
# ---------------------------------------------------------------------------
def clique(n):
    return [(i, j) for i in range(n) for j in range(i + 1, n)]

def cycle(n):
    return [(i, (i + 1) % n) for i in range(n)]

def star(n):
    return [(0, i) for i in range(1, n)]

def path(n):
    return [(i, i + 1) for i in range(n - 1)]

# Only graphs already present in the paper's simulation section
BENCHMARK_GRAPHS = [
    {"name": "K3",  "n": 3, "edges": clique(3)},
    {"name": "K4",  "n": 4, "edges": clique(4)},
    {"name": "K5",  "n": 5, "edges": clique(5)},
    {"name": "K6",  "n": 6, "edges": clique(6)},
    {"name": "K7",  "n": 7, "edges": clique(7)},
    {"name": "C4",  "n": 4, "edges": cycle(4)},
    {"name": "C5",  "n": 5, "edges": cycle(5)},
    {"name": "C6",  "n": 6, "edges": cycle(6)},
]

# Figures only use the K-series to show clear scaling trends
FIGURE_GRAPHS = [g for g in BENCHMARK_GRAPHS if g["name"].startswith("K")]

# LaTeX-formatted display names for figures
DISPLAY_NAMES = {
    "K3": r"$K_3$",
    "K4": r"$K_4$",
    "K5": r"$K_5$",
    "K6": r"$K_6$",
    "K7": r"$K_7$",
    "C4": r"$C_4$",
    "C5": r"$C_5$",
    "C6": r"$C_6$",
}

REPO_ROOT = Path("/Users/topfee/Desktop/quantum-research")
PYTHON = REPO_ROOT / "src" / "mvc-solver-1.4.0" / "venv" / "bin" / "python"
EXTRACT_SCRIPT = REPO_ROOT / "src" / "mvc_qaoa" / "experiments" / "extract_grover_single.py"

# ---------------------------------------------------------------------------
# Extract Grover metrics via subprocess (avoids Python module caching issues)
# ---------------------------------------------------------------------------
def extract_grover_metrics():
    arith_metrics = []
    dicke_metrics = []

    solver_dirs = {
        "arith": REPO_ROOT / "src" / "mvc-solver-1.3.0",
        "dicke": REPO_ROOT / "src" / "mvc-solver-1.4.0",
    }

    for g in BENCHMARK_GRAPHS:
        name = g["name"]
        n = g["n"]
        edges = g["edges"]
        edges_str = ";".join(f"{u},{v}" for u, v in edges)

        for arch, out_list in [("arith", arith_metrics), ("dicke", dicke_metrics)]:
            cmd = [
                str(PYTHON),
                str(EXTRACT_SCRIPT),
                str(solver_dirs[arch]),
                name,
                str(n),
                edges_str,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout.strip())
            out_list.append(data)

    return arith_metrics, dicke_metrics

# ---------------------------------------------------------------------------
# Load QAOA results
# ---------------------------------------------------------------------------
def load_qaoa_results(run_dir: Path):
    summary_path = run_dir / "benchmark_summary.json"
    with open(summary_path) as f:
        return json.load(f)

# ---------------------------------------------------------------------------
# Figure 1: Validity Probability Comparison
# ---------------------------------------------------------------------------
def plot_validity_comparison(qaoa_data, output_path: Path):
    graphs = [g["name"] for g in FIGURE_GRAPHS]
    x = np.arange(len(graphs))
    width = 0.2

    qaoa_p1 = []
    qaoa_p2 = []
    qaoa_p3 = []
    for name in graphs:
        p1 = next(r for r in qaoa_data if r["graph"] == name and r["p"] == 1)
        p2 = next(r for r in qaoa_data if r["graph"] == name and r["p"] == 2)
        p3 = next(r for r in qaoa_data if r["graph"] == name and r["p"] == 3)
        qaoa_p1.append(p1["valid_probability"])
        qaoa_p2.append(p2["valid_probability"])
        qaoa_p3.append(p3["valid_probability"])

    fig, ax = plt.subplots(figsize=(12, 5))

    ax.bar(x - 1.5*width, qaoa_p1, width, label="QAOA $p=1$", color="#5B9BD5")
    ax.bar(x - 0.5*width, qaoa_p2, width, label="QAOA $p=2$", color="#ED7D31")
    ax.bar(x + 0.5*width, qaoa_p3, width, label="QAOA $p=3$", color="#70AD47")
    ax.bar(x + 1.5*width, [1.0]*len(graphs), width, label="Grover (all arch.)", color="#C00000")

    ax.set_ylabel("Probability of Measuring Valid Cover", fontsize=12)
    ax.set_title("Validity Probability: QAOA vs Grover Oracle Architectures", fontsize=13)
    ax.set_xticks(x)
    ax.set_xticklabels([DISPLAY_NAMES[g] for g in graphs])
    ax.set_ylim(0, 1.15)
    ax.axhline(y=1.0, color="black", linestyle="--", linewidth=0.8, alpha=0.5)
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    fig.savefig(output_path, dpi=300)
    plt.close(fig)
    print(f"Saved validity comparison -> {output_path}")

# ---------------------------------------------------------------------------
# Figure 2a: Circuit Depth Comparison
# ---------------------------------------------------------------------------
def plot_depth_comparison(qaoa_data, arith_data, dicke_data, output_path: Path):
    graphs = [g["name"] for g in FIGURE_GRAPHS]
    x = np.arange(len(graphs))

    qaoa_p1_depth = []
    qaoa_p2_depth = []
    qaoa_p3_depth = []
    for name in graphs:
        p1 = next(r for r in qaoa_data if r["graph"] == name and r["p"] == 1)
        p2 = next(r for r in qaoa_data if r["graph"] == name and r["p"] == 2)
        p3 = next(r for r in qaoa_data if r["graph"] == name and r["p"] == 3)
        qaoa_p1_depth.append(p1["depth"])
        qaoa_p2_depth.append(p2["depth"])
        qaoa_p3_depth.append(p3["depth"])

    arith_depth = [next(a["depth"] for a in arith_data if a["name"] == name) for name in graphs]
    dicke_depth = [next(d["depth"] for d in dicke_data if d["name"] == name) for name in graphs]

    fig, ax = plt.subplots(figsize=(8, 4.5))

    ax.plot(x, qaoa_p1_depth, "o-", label="QAOA $p=1$", color="#5B9BD5", markersize=5)
    ax.plot(x, qaoa_p2_depth, "s-", label="QAOA $p=2$", color="#ED7D31", markersize=5)
    ax.plot(x, qaoa_p3_depth, "^-", label="QAOA $p=3$", color="#70AD47", markersize=5)
    ax.plot(x, dicke_depth, "v-", label="Dicke-state (Ours)", color="#0000FF", markersize=5)
    ax.plot(x, arith_depth, "D-", label="Arithmetic-based (Ours)", color="#800080", markersize=5)

    ax.set_ylabel("Circuit Depth", fontsize=12)
    ax.set_title("Per-Iteration Circuit Depth", fontsize=13)
    ax.set_xticks(x)
    ax.set_xticklabels([DISPLAY_NAMES[g] for g in graphs])
    ax.legend(fontsize=9, loc="upper left")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(output_path, dpi=300)
    plt.close(fig)
    print(f"Saved depth comparison -> {output_path}")

# ---------------------------------------------------------------------------
# Figure 2b: Qubit Count Comparison
# ---------------------------------------------------------------------------
def plot_qubit_comparison(qaoa_data, arith_data, dicke_data, output_path: Path):
    graphs = [g["name"] for g in FIGURE_GRAPHS]
    x = np.arange(len(graphs))

    qaoa_qubits = [next(r["n"] for r in qaoa_data if r["graph"] == name and r["p"] == 1) for name in graphs]
    arith_qubits = [next(a["qubits"] for a in arith_data if a["name"] == name) for name in graphs]
    dicke_qubits = [next(d["qubits"] for d in dicke_data if d["name"] == name) for name in graphs]

    fig, ax = plt.subplots(figsize=(8, 4.5))

    ax.plot(x, qaoa_qubits, "o-", label="QAOA (any $p$)", color="#5B9BD5", markersize=5)
    ax.plot(x, dicke_qubits, "v-", label="Dicke-state (Ours)", color="#0000FF", markersize=5)
    ax.plot(x, arith_qubits, "D-", label="Arithmetic-based (Ours)", color="#800080", markersize=5)

    ax.set_ylabel("Qubit Count", fontsize=12)
    ax.set_title("Total Qubit Requirement", fontsize=13)
    ax.set_xticks(x)
    ax.set_xticklabels([DISPLAY_NAMES[g] for g in graphs])
    ax.legend(fontsize=9, loc="upper left")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(output_path, dpi=300)
    plt.close(fig)
    print(f"Saved qubit comparison -> {output_path}")

# ---------------------------------------------------------------------------
# Save comparison table
# ---------------------------------------------------------------------------
def save_comparison_table(qaoa_data, arith_data, dicke_data, output_dir: Path):
    graphs = [g["name"] for g in BENCHMARK_GRAPHS]
    rows = []
    for name in graphs:
        q1 = next(r for r in qaoa_data if r["graph"] == name and r["p"] == 1)
        q2 = next(r for r in qaoa_data if r["graph"] == name and r["p"] == 2)
        q3 = next(r for r in qaoa_data if r["graph"] == name and r["p"] == 3)
        a = next(d for d in arith_data if d["name"] == name)
        d = next(d for d in dicke_data if d["name"] == name)

        rows.append({
            "graph": name,
            "n": q1["n"],
            "m": q1["m"],
            "qaoa_p1_qubits": q1["n"],
            "qaoa_p1_depth": q1["depth"],
            "qaoa_p1_valid": round(q1["valid_probability"], 3),
            "qaoa_p2_depth": q2["depth"],
            "qaoa_p2_valid": round(q2["valid_probability"], 3),
            "qaoa_p3_depth": q3["depth"],
            "qaoa_p3_valid": round(q3["valid_probability"], 3),
            "grover_arith_qubits": a["qubits"],
            "grover_arith_depth": a["depth"],
            "grover_dicke_qubits": d["qubits"],
            "grover_dicke_depth": d["depth"],
        })

    json_path = output_dir / "grover_vs_qaoa_metrics.json"
    with open(json_path, "w") as f:
        json.dump(rows, f, indent=2)

    md_path = output_dir / "grover_vs_qaoa_table.md"
    lines = [
        "# Grover vs QAOA Empirical Comparison",
        "",
        "| Graph | n | m | QAOA p=1 Depth | QAOA p=1 Valid% | QAOA p=2 Depth | QAOA p=2 Valid% | QAOA p=3 Depth | QAOA p=3 Valid% | Arithmetic (Ours) Qubits | Arithmetic (Ours) Depth | Dicke-state (Ours) Qubits | Dicke-state (Ours) Depth |",
        "|-------|---|---|----------------|-----------------|----------------|-----------------|----------------|-----------------|--------------------------|-------------------------|---------------------------|---------------------------|",
    ]
    for r in rows:
        lines.append(
            f"| {r['graph']} | {r['n']} | {r['m']} | "
            f"{r['qaoa_p1_depth']} | {r['qaoa_p1_valid']:.3f} | "
            f"{r['qaoa_p2_depth']} | {r['qaoa_p2_valid']:.3f} | "
            f"{r['qaoa_p3_depth']} | {r['qaoa_p3_valid']:.3f} | "
            f"{r['grover_arith_qubits']} | {r['grover_arith_depth']} | "
            f"{r['grover_dicke_qubits']} | {r['grover_dicke_depth']} |"
        )
    with open(md_path, "w") as f:
        f.write("\n".join(lines))

    print(f"Saved comparison table -> {md_path}")
    return rows

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    output_dir = REPO_ROOT / "src" / "mvc_qaoa" / "experiments" / "qaoa_vs_grover_comparison"
    output_dir.mkdir(exist_ok=True)

    print("Extracting Grover circuit metrics...")
    arith_data, dicke_data = extract_grover_metrics()

    qaoa_run_dir = REPO_ROOT / "src" / "mvc_qaoa" / "experiments" / "run_20260426_111406"
    print(f"Loading QAOA results from {qaoa_run_dir}...")
    qaoa_data = load_qaoa_results(qaoa_run_dir)

    print("Saving comparison table...")
    save_comparison_table(qaoa_data, arith_data, dicke_data, output_dir)

    print("Generating figures...")
    plot_validity_comparison(qaoa_data, output_dir / "fig_validity_comparison.png")
    plot_depth_comparison(qaoa_data, arith_data, dicke_data, output_dir / "fig_depth_comparison.png")
    plot_qubit_comparison(qaoa_data, arith_data, dicke_data, output_dir / "fig_qubit_comparison.png")

    print("\nDone! All artifacts saved to:", output_dir)

if __name__ == "__main__":
    main()
