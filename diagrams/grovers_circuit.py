#!/usr/bin/env python3
"""Generate the Grover's algorithm circuit diagram.

Produces `grovers_algorithm_circuit.png` — a Qiskit circuit showing
the standard Grover algorithm structure: Hadamard init, oracle, diffuser.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "diagrams" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def build_grover_circuit(n=3):
    """Build a Grover circuit for n qubits (1 iteration)."""
    q = QuantumRegister(n, name="q")
    c = ClassicalRegister(n, name="c")
    qc = QuantumCircuit(q, c, name="Grover")

    # Step 1: Initialization — Hadamard on all qubits
    qc.h(q)
    qc.barrier(label="Init")

    # Step 2: Oracle (placeholder — marks target state |101>)
    # For illustration: a simple oracle that flips phase of |101>
    qc.x(q[1])
    qc.h(q[n-1])
    qc.mcx(q[:n-1], q[n-1])
    qc.h(q[n-1])
    qc.x(q[1])
    qc.barrier(label="Oracle")

    # Step 3: Diffuser (reflection about |s>)
    qc.h(q)
    qc.x(q)
    qc.h(q[n-1])
    qc.mcx(q[:n-1], q[n-1])
    qc.h(q[n-1])
    qc.x(q)
    qc.h(q)
    qc.barrier(label="Diffuser")

    # Step 4: Measurement
    qc.measure(q, c)

    return qc


def main():
    n = 3
    qc = build_grover_circuit(n)

    fig, ax = plt.subplots(1, 1, figsize=(14, 5))
    qc.draw("mpl", style="iqp", ax=ax, fold=40)
    ax.set_title("Grover's Algorithm Circuit (3 qubits, 1 iteration)", fontsize=14, pad=15)

    output_path = OUTPUT_DIR / "grovers_algorithm_circuit.png"
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {output_path}")

    # Also save to repo root
    root_path = Path(__file__).resolve().parent.parent / "grovers_algorithm_circuit.png"
    fig2, ax2 = plt.subplots(1, 1, figsize=(14, 5))
    qc2 = build_grover_circuit(n)
    qc2.draw("mpl", style="iqp", ax=ax2, fold=40)
    ax2.set_title("Grover's Algorithm Circuit (3 qubits, 1 iteration)", fontsize=14, pad=15)
    fig2.savefig(root_path, dpi=200, bbox_inches="tight")
    plt.close(fig2)
    print(f"Saved: {root_path}")


if __name__ == "__main__":
    main()
