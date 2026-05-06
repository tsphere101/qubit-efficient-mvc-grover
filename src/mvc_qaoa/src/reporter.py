"""Output generation: JSON, text circuits, and plots."""

import os
import json
from typing import Dict, List
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from qiskit import QuantumCircuit


def save_json(data: Dict, path: str) -> None:
    """Save a dictionary to a pretty-printed JSON file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def save_circuit_text(circuit: QuantumCircuit, path: str) -> None:
    """Save circuit text diagram with fold=-1 (no wrapping)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    text = circuit.draw(output="text", fold=-1).single_string()
    with open(path, "w") as f:
        f.write(text)
        f.write("\n")


def save_circuit_image(circuit: QuantumCircuit, path: str) -> None:
    """Save circuit matplotlib diagram."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig = circuit.draw(output="mpl", style="iqp")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_convergence(history: List[float], optimal_cost: float, path: str) -> None:
    """Plot optimizer convergence curve."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(range(1, len(history) + 1), history, marker="o", markersize=3,
            linewidth=1.5, color="#0056b3")
    ax.axhline(y=optimal_cost, color="black", linestyle="--", linewidth=1,
               label=f"Optimal = {optimal_cost:.2f}")
    ax.set_xlabel("Iteration")
    ax.set_ylabel("Expected QUBO Cost")
    ax.set_title("Classical Optimiser Convergence")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_distribution(results: List[Dict], path: str, top_n: int = 12) -> None:
    """Plot measurement distribution histogram."""
    import matplotlib.patches as mpatches

    os.makedirs(os.path.dirname(path), exist_ok=True)
    top = results[:top_n]
    states = [r["bitstring"] for r in top]
    probs = [r["probability"] * 100 for r in top]
    colours = ["#0056b3" if r["valid"] else "#cccccc" for r in top]

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(range(len(states)), probs, color=colours, edgecolor="white")
    ax.set_xticks(range(len(states)))
    ax.set_xticklabels(states, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Probability (%)")
    ax.set_title(f"Measurement Distribution (top {top_n})")
    ax.grid(axis="y", alpha=0.3)

    valid_patch = mpatches.Patch(color="#0056b3", label="Valid Cover")
    invalid_patch = mpatches.Patch(color="#cccccc", label="Invalid Cover")
    ax.legend(handles=[valid_patch, invalid_patch], loc="upper right")

    plt.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
