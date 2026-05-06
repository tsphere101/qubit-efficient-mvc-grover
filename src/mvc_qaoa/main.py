"""MVC QAOA Benchmark Suite — Main entry point.

Runs QAOA (p=1, p=2, p=3) on a suite of graphs, saving:
    - results.json       : comprehensive metrics per experiment
    - circuit.txt        : text diagram (fold=-1)
    - circuit.png        : matplotlib diagram
    - convergence.png    : optimizer convergence curve
    - distribution.png   : measurement histogram
    - exact_solution.json: brute-force verification
    - benchmark_summary.json : cross-graph comparison
    - scaling_plot.png     : resource scaling
    - approximation_ratio.png : quality comparison
"""

import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path

import numpy as np
from qiskit_aer import AerSimulator
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx

# Add src/ to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from graphs import BENCHMARK_GRAPHS
from qubo import build_mvc_qubo, qubo_cost, is_valid_cover, cover_size
from ising import qubo_to_ising, ising_to_json
from circuit import build_qaoa_circuit
from exact import solve_exact
from optimizer import optimize_qaoa
from simulator import simulate_and_analyse
from reporter import (
    save_json, save_circuit_text, save_circuit_image,
    plot_convergence, plot_distribution
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SHOTS_PER_EVAL = 4096
SHOTS_FINAL = 4096
MAXITER = 80
RANDOM_RESTARTS = 5
PS = [1, 2, 3]


def run_single_experiment(graph_def: dict, p: int, out_dir: str) -> dict:
    """Run one (graph, p) experiment and save all artifacts."""
    name = graph_def["name"]
    n = graph_def["n"]
    edges = graph_def["edges"]
    print(f"\n  [{name}] p={p} — building QUBO...")

    # 1. QUBO
    Q = build_mvc_qubo(n, edges)
    penalty = float(max(len([e for e in edges if i in e]) for i in range(n)) + 1)

    # 2. Ising
    terms, const = qubo_to_ising(Q)

    # 3. Exact solution
    exact = solve_exact(n, edges, Q)
    save_json(exact, os.path.join(out_dir, "exact_solution.json"))

    # 4. Circuit (before optimization, using dummy angles)
    dummy_gammas = [0.5] * p
    dummy_betas = [0.5] * p
    dummy_qc = build_qaoa_circuit(terms, dummy_gammas, dummy_betas, n)

    circuit_info = {
        "depth": dummy_qc.depth(),
        "total_gates": dummy_qc.size(),
        "gate_breakdown": dict(dummy_qc.count_ops()),
        "two_qubit_count": dummy_qc.count_ops().get("cx", 0),
        "qubit_count": n,
        "num_parameters": 2 * p
    }

    # Save circuit diagrams
    save_circuit_text(dummy_qc, os.path.join(out_dir, "circuit.txt"))
    save_circuit_image(dummy_qc, os.path.join(out_dir, "circuit.png"))

    # 5. Classical optimization
    def objective(params):
        gammas = params[:p].tolist()
        betas = params[p:].tolist()
        qc = build_qaoa_circuit(terms, gammas, betas, n)
        sim = AerSimulator()
        counts = sim.run(qc, shots=SHOTS_PER_EVAL).result().get_counts()
        total = sum(counts.values())
        exp_cost = sum(qubo_cost(bs, Q) * cnt for bs, cnt in counts.items()) / total
        return exp_cost

    print(f"  [{name}] p={p} — optimizing (SPSA, {MAXITER} iter, {RANDOM_RESTARTS} restarts)...")
    opt_result = optimize_qaoa(
        objective, p=p, method="SPSA",
        maxiter=MAXITER, shots_per_eval=SHOTS_PER_EVAL,
        random_restarts=RANDOM_RESTARTS
    )

    # 6. Final simulation with optimal angles
    print(f"  [{name}] p={p} — simulating ({SHOTS_FINAL} shots)...")
    best_qc = build_qaoa_circuit(terms, opt_result["gammas"], opt_result["betas"], n)
    sim_result = simulate_and_analyse(best_qc, Q, edges, shots=SHOTS_FINAL)

    # 7. Metrics
    best_valid = sim_result["best_valid"]
    optimal_cost = exact["optimal_cost"]
    approx_ratio = None
    if best_valid:
        approx_ratio = best_valid["cost"] / optimal_cost if optimal_cost != 0 else None

    metrics = {
        "optimal_cost": float(optimal_cost),
        "best_observed_cost": best_valid["cost"] if best_valid else None,
        "best_observed_size": best_valid["size"] if best_valid else None,
        "best_observed_bitstring": best_valid["bitstring"] if best_valid else None,
        "approximation_ratio": float(approx_ratio) if approx_ratio is not None else None,
        "success_probability": float(best_valid["probability"]) if best_valid else 0.0,
        "valid_probability": float(sim_result["valid_probability"]),
        "expected_cost": float(sim_result["expected_cost"]),
    }

    # 8. Plots
    plot_convergence(opt_result["history"], optimal_cost,
                     os.path.join(out_dir, "convergence.png"))
    plot_distribution(sim_result["top_8"],
                      os.path.join(out_dir, "distribution.png"))

    # 9. Landscape visualization
    print(f"  [{name}] p={p} — generating landscape plot...")
    generate_landscape_plot(
        name, p, n, terms, Q,
        opt_result["gammas"], opt_result["betas"],
        opt_result.get("trajectory", []),
        out_dir
    )

    # 10. Assemble results.json
    results = {
        "metadata": {
            "graph_name": name,
            "p": p,
            "timestamp": datetime.now().isoformat(),
            "shots_per_eval": SHOTS_PER_EVAL,
            "shots_final": SHOTS_FINAL,
            "optimizer": "SPSA",
            "maxiter": MAXITER,
            "random_restarts": RANDOM_RESTARTS,
        },
        "graph": {
            "n_vertices": n,
            "edges": edges,
            "num_edges": len(edges),
            "density": round(2 * len(edges) / (n * (n - 1)), 4) if n > 1 else 0,
        },
        "qubo": {
            "penalty": float(penalty),
            "matrix": Q.tolist(),
            "ising_terms": ising_to_json(terms),
            "constant_offset": float(const),
        },
        "circuit": circuit_info,
        "optimization": {
            "best_gammas": opt_result["gammas"],
            "best_betas": opt_result["betas"],
            "best_cost": opt_result["best_cost"],
            "history": opt_result["history"],
            "iterations_used": opt_result["iterations"],
            "time_seconds": round(opt_result["time_seconds"], 3),
            "success": opt_result["success"],
        },
        "simulation": {
            "shots": SHOTS_FINAL,
            "num_unique_states": sim_result["num_unique_states"],
            "expected_cost": round(sim_result["expected_cost"], 4),
            "valid_probability": round(sim_result["valid_probability"], 4),
            "top_8": sim_result["top_8"],
        },
        "metrics": metrics,
        "exact": {
            "optimal_cost": exact["optimal_cost"],
            "optimal_size": exact["optimal_size"],
            "optimal_covers": exact["optimal_covers"],
            "num_valid_covers": exact["num_valid_covers"],
        }
    }

    save_json(results, os.path.join(out_dir, "results.json"))
    gammas_str = ", ".join(f"{g:.4f}" for g in opt_result["gammas"])
    betas_str = ", ".join(f"{b:.4f}" for b in opt_result["betas"])
    print(f"  [{name}] p={p} — done.")
    print(f"    Final params:  gamma = [{gammas_str}],  beta = [{betas_str}]")
    print(f"    best_valid_cost={metrics['best_observed_cost']}, "
          f"approx_ratio={metrics['approximation_ratio']}, valid_prob={metrics['valid_probability']:.3f}")

    return results


def generate_landscape_plot(
    graph_name: str, p: int, n: int, terms, Q: np.ndarray,
    opt_gammas: list, opt_betas: list, trajectory: list, out_dir: str
) -> None:
    """Generate landscape visualization showing where the optimizer landed.

    p=1  : full 2D (gamma, beta) heatmap with trajectory overlay.
    p>=2 : 2D slice of (gamma_1, beta_1) + 1D curvature slices for all params.
    """
    LANDSCAPE_SHOTS = 4096

    def evaluate(gammas, betas):
        qc = build_qaoa_circuit(terms, gammas, betas, n)
        counts = AerSimulator().run(qc, shots=LANDSCAPE_SHOTS).result().get_counts()
        total = sum(counts.values())
        return sum(qubo_cost(bs, Q) * cnt for bs, cnt in counts.items()) / total

    # Compute data-driven bounds from trajectory + optimum + margin.
    # No clamping — the landscape must cover wherever the optimizer actually went.
    def _bounds(vals, margin=0.5, min_range=1.0):
        if vals:
            lo = min(vals) - margin
            hi = max(vals) + margin
        else:
            lo, hi = -margin, margin
        if hi - lo < min_range:
            centre = (lo + hi) / 2
            lo = centre - min_range / 2
            hi = centre + min_range / 2
        return lo, hi

    if p == 1:
        # Full 2D landscape
        all_g = ([pt[0] for pt in trajectory] if trajectory else []) + [opt_gammas[0]]
        all_b = ([pt[1] for pt in trajectory] if trajectory else []) + [opt_betas[0]]
        g_lo, g_hi = _bounds(all_g, margin=0.4, min_range=1.5)
        b_lo, b_hi = _bounds(all_b, margin=0.3, min_range=1.0)

        gamma_vals = np.linspace(g_lo, g_hi, 40)
        beta_vals = np.linspace(b_lo, b_hi, 40)
        costs = np.zeros((len(beta_vals), len(gamma_vals)))

        for i, g in enumerate(gamma_vals):
            for j, b in enumerate(beta_vals):
                costs[j, i] = evaluate([g], [b])

        fig, ax = plt.subplots(figsize=(7, 5.5))
        im = ax.imshow(
            costs, origin="lower", aspect="auto", cmap="viridis",
            extent=[gamma_vals[0], gamma_vals[-1], beta_vals[0], beta_vals[-1]]
        )

        # Overlay optimization trajectory
        if trajectory:
            traj_g = [pt[0] for pt in trajectory]
            traj_b = [pt[1] for pt in trajectory]
            ax.plot(traj_g, traj_b, "w-", linewidth=1.5, alpha=0.7, label="Optimizer path")
            ax.plot(traj_g[0], traj_b[0], "wo", markersize=6, markeredgecolor="black", label="Start")

        # Mark optimal point
        ax.plot(opt_gammas[0], opt_betas[0], "ro", markersize=10,
                markeredgecolor="white", markeredgewidth=2, label="Optimum")

        ax.set_xlabel(r"$\gamma$", fontsize=12)
        ax.set_ylabel(r"$\beta$", fontsize=12)
        ax.set_title(f"Cost Landscape — {graph_name} p={p}", fontsize=13)
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label("Expected QUBO Cost")
        ax.legend(loc="upper right", fontsize=8)
        plt.tight_layout()
        fig.savefig(os.path.join(out_dir, "landscape.png"), dpi=150)
        plt.close(fig)

    else:
        # p>=2: 2D slice (gamma_1, beta_1) with others fixed + 1D curvature slices
        n_params = 2 * p
        fig = plt.figure(figsize=(14, 3 + 2.2 * p))
        gs = fig.add_gridspec(1 + p, 2, hspace=0.45, wspace=0.3)

        # --- 2D slice (gamma_1, beta_1) ---
        ax2d = fig.add_subplot(gs[0, :])
        all_g1 = [opt_gammas[0]] + ([pt[0] for pt in trajectory] if trajectory else [])
        all_b1 = [opt_betas[0]] + ([pt[1] for pt in trajectory] if trajectory else [])
        g_lo, g_hi = _bounds(all_g1, margin=0.4, min_range=1.5)
        b_lo, b_hi = _bounds(all_b1, margin=0.3, min_range=1.0)

        gamma_vals = np.linspace(g_lo, g_hi, 30)
        beta_vals = np.linspace(b_lo, b_hi, 30)
        costs = np.zeros((len(beta_vals), len(gamma_vals)))

        for i, g in enumerate(gamma_vals):
            for j, b in enumerate(beta_vals):
                gammas = list(opt_gammas)
                betas = list(opt_betas)
                gammas[0] = g
                betas[0] = b
                costs[j, i] = evaluate(gammas, betas)

        im = ax2d.imshow(
            costs, origin="lower", aspect="auto", cmap="viridis",
            extent=[gamma_vals[0], gamma_vals[-1], beta_vals[0], beta_vals[-1]]
        )
        ax2d.plot(opt_gammas[0], opt_betas[0], "ro", markersize=10,
                  markeredgecolor="white", markeredgewidth=2)
        ax2d.set_xlabel(r"$\gamma_1$", fontsize=11)
        ax2d.set_ylabel(r"$\beta_1$", fontsize=11)
        ax2d.set_title(
            f"2D Slice — {graph_name} p={p}  (other params fixed at optima)", fontsize=12
        )
        cbar = plt.colorbar(im, ax=ax2d)
        cbar.set_label("Expected Cost")

        # --- 1D curvature slices ---
        param_names = [f"$\\gamma_{{{i+1}}}$" for i in range(p)] + \
                      [f"$\\beta_{{{i+1}}}$" for i in range(p)]
        all_params = opt_gammas + opt_betas

        for idx in range(n_params):
            ax = fig.add_subplot(gs[1 + idx // 2, idx % 2])
            val = all_params[idx]
            lo, hi = _bounds([val], margin=1.0, min_range=1.0)
            param_range = np.linspace(lo, hi, 20)
            sweep_costs = []

            for v in param_range:
                gammas = list(opt_gammas)
                betas = list(opt_betas)
                if idx < p:
                    gammas[idx] = v
                else:
                    betas[idx - p] = v
                sweep_costs.append(evaluate(gammas, betas))

            ax.plot(param_range, sweep_costs, "b-", linewidth=1.5)
            ax.axvline(x=all_params[idx], color="r", linestyle="--", linewidth=2)
            ax.set_xlabel(param_names[idx], fontsize=10)
            ax.set_ylabel("Expected Cost", fontsize=9)
            ax.set_title(f"Curvature: {param_names[idx]}", fontsize=10)
            ax.grid(True, alpha=0.3)

        fig.suptitle(f"Parameter Landscape — {graph_name} p={p}", fontsize=14, y=0.995)
        fig.savefig(os.path.join(out_dir, "landscape.png"), dpi=150, bbox_inches="tight")
        plt.close(fig)


def save_graph_image(edges: list, n: int, path: str) -> None:
    """Save a NetworkX-rendered graph diagram as JPG."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    G = nx.Graph()
    G.add_nodes_from(range(n))
    G.add_edges_from(edges)

    fig, ax = plt.subplots(figsize=(5, 5))
    pos = nx.spring_layout(G, seed=42)
    nx.draw_networkx_nodes(G, pos, node_color="#0056b3", node_size=600, ax=ax)
    nx.draw_networkx_edges(G, pos, edge_color="#888888", width=2, ax=ax)
    nx.draw_networkx_labels(G, pos, font_color="white", font_weight="bold", ax=ax)
    ax.set_title(f"Graph  (n={n}, m={len(edges)})")
    ax.axis("off")
    plt.tight_layout()
    fig.savefig(path, dpi=150, format="jpg")
    plt.close(fig)


def run_benchmark_suite() -> str:
    """Run the full benchmark suite and return the output directory path."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_dir = os.path.join(os.path.dirname(__file__), "experiments", f"run_{timestamp}")
    os.makedirs(base_dir, exist_ok=True)

    # Save global config
    config = {
        "timestamp": timestamp,
        "shots_per_eval": SHOTS_PER_EVAL,
        "shots_final": SHOTS_FINAL,
        "maxiter": MAXITER,
        "random_restarts": RANDOM_RESTARTS,
        "p_values": PS,
        "graphs": [g["name"] for g in BENCHMARK_GRAPHS],
    }
    save_json(config, os.path.join(base_dir, "run_config.json"))

    summary = []

    for graph_def in BENCHMARK_GRAPHS:
        name = graph_def["name"]
        n = graph_def["n"]
        edges = graph_def["edges"]
        print(f"\n{'='*60}")
        print(f"Graph: {name} (n={n}, m={len(edges)})")
        print(f"{'='*60}")

        # Save graph image once per graph (shared across all p values)
        graph_img_path = os.path.join(base_dir, name, "graph.jpg")
        save_graph_image(edges, n, graph_img_path)
        print(f"  Saved graph image -> {graph_img_path}")

        for p in PS:
            out_dir = os.path.join(base_dir, name, f"p{p}")
            os.makedirs(out_dir, exist_ok=True)
            results = run_single_experiment(graph_def, p, out_dir)
            summary.append({
                "graph": name,
                "n": graph_def["n"],
                "m": len(graph_def["edges"]),
                "p": p,
                "depth": results["circuit"]["depth"],
                "two_qubit_count": results["circuit"]["two_qubit_count"],
                "optimal_cost": results["exact"]["optimal_cost"],
                "best_observed_cost": results["metrics"]["best_observed_cost"],
                "approximation_ratio": results["metrics"]["approximation_ratio"],
                "valid_probability": results["metrics"]["valid_probability"],
                "expected_cost": results["metrics"]["expected_cost"],
                "time_seconds": results["optimization"]["time_seconds"],
                "best_gammas": results["optimization"]["best_gammas"],
                "best_betas": results["optimization"]["best_betas"],
            })

    # Save summary
    save_json(summary, os.path.join(base_dir, "benchmark_summary.json"))

    # Generate cross-graph plots
    generate_summary_plots(summary, base_dir)

    # Generate markdown report
    generate_markdown_report(summary, base_dir)

    print(f"\n{'='*60}")
    print(f"Benchmark complete.  Output: {base_dir}")
    print(f"{'='*60}")
    return base_dir


def generate_summary_plots(summary: list, base_dir: str) -> None:
    """Create scaling and quality comparison plots."""
    # 1. Scaling plot
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

    for p in PS:
        rows = [s for s in summary if s["p"] == p]
        names = [s["graph"] for s in rows]
        depths = [s["depth"] for s in rows]
        cnots = [s["two_qubit_count"] for s in rows]
        x = range(len(names))

        axes[0].plot(x, depths, marker="o", label=f"p={p}")
        axes[1].plot(x, cnots, marker="s", label=f"p={p}")

    axes[0].set_xticks(range(len(names)))
    axes[0].set_xticklabels(names, rotation=45, ha="right", fontsize=8)
    axes[0].set_ylabel("Circuit Depth")
    axes[0].set_title("Depth vs Graph")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    axes[1].set_xticks(range(len(names)))
    axes[1].set_xticklabels(names, rotation=45, ha="right", fontsize=8)
    axes[1].set_ylabel("CNOT Count")
    axes[1].set_title("Two-Qubit Gate Count vs Graph")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(os.path.join(base_dir, "scaling_plot.png"), dpi=150)
    plt.close(fig)

    # 2. Approximation ratio + valid probability
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

    for p in PS:
        rows = [s for s in summary if s["p"] == p]
        names_p = [s["graph"] for s in rows]
        ratios = [s["approximation_ratio"] if s["approximation_ratio"] is not None else 0 for s in rows]
        valids = [s["valid_probability"] for s in rows]
        x = range(len(names_p))

        axes[0].bar([xi + (p - 1) * 0.35 for xi in x], ratios, width=0.3,
                    label=f"p={p}", alpha=0.8)
        axes[1].bar([xi + (p - 1) * 0.35 for xi in x], valids, width=0.3,
                    label=f"p={p}", alpha=0.8)

    axes[0].set_xticks(range(len(names_p)))
    axes[0].set_xticklabels(names_p, rotation=45, ha="right", fontsize=8)
    axes[0].set_ylabel("Approximation Ratio")
    axes[0].set_title("Cost Ratio (lower is better)")
    axes[0].axhline(y=1.0, color="black", linestyle="--", linewidth=1)
    axes[0].legend()
    axes[0].grid(axis="y", alpha=0.3)

    axes[1].set_xticks(range(len(names_p)))
    axes[1].set_xticklabels(names_p, rotation=45, ha="right", fontsize=8)
    axes[1].set_ylabel("Valid Probability")
    axes[1].set_title("Probability of Measuring Valid Cover")
    axes[1].legend()
    axes[1].grid(axis="y", alpha=0.3)

    plt.tight_layout()
    fig.savefig(os.path.join(base_dir, "approximation_ratio.png"), dpi=150)
    plt.close(fig)


def generate_markdown_report(summary: list, base_dir: str) -> None:
    """Write a human-readable markdown summary table."""
    lines = [
        "# MVC QAOA Benchmark Report",
        "",
        "| Graph | n | m | p | Depth | CNOTs | Optimal | Best Obs. | Approx | Valid | Gammas | Betas |",
        "|-------|---|---|---|-------|-------|---------|-----------|--------|-------|--------|-------|",
    ]
    for s in summary:
        ar = f"{s['approximation_ratio']:.3f}" if s['approximation_ratio'] is not None else "N/A"
        gs = ", ".join(f"{g:.3f}" for g in s['best_gammas'])
        bs = ", ".join(f"{b:.3f}" for b in s['best_betas'])
        lines.append(
            f"| {s['graph']} | {s['n']} | {s['m']} | {s['p']} | "
            f"{s['depth']} | {s['two_qubit_count']} | {s['optimal_cost']:.2f} | "
            f"{s['best_observed_cost']:.2f} | {ar} | {s['valid_probability']:.3f} | `{gs}` | `{bs}` |"
        )

    lines.extend(["", "## Notes", "", "- **Approximation Ratio** = best_observed_cost / optimal_cost (1.0 is perfect).",
                  "- **Valid Prob** = probability that a measured state is a valid vertex cover.",
                  "- **Gammas / Betas** = final optimised QAOA parameters for the problem and mixer unitaries.",
                  "- All experiments use COBYLA with random restarts."])

    with open(os.path.join(base_dir, "benchmark_table.md"), "w") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    run_benchmark_suite()
