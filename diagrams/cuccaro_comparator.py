#!/usr/bin/env python3
"""Generate the Cuccaro ripple-carry comparator circuit diagram.

Produces `comparator.jpg` — a Qiskit circuit diagram showing the MAJ/IMAJ
chain used in the Cuccaro adder configured as a comparator.

Reference: Cuccaro, Draper, Kutin, Moulton (2004).
"A new quantum ripple-carry addition circuit."
"""
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from qiskit import QuantumCircuit, QuantumRegister

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "diagrams" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def maj_gate():
    """MAJ (majority) gate as a sub-circuit."""
    qc = QuantumCircuit(3, name="MAJ")
    qc.cx(1, 2)
    qc.cx(1, 0)
    qc.ccx(0, 2, 1)
    return qc.to_gate()


def umaj_gate():
    """IMAJ (inverse majority) gate as a sub-circuit."""
    qc = QuantumCircuit(3, name="IMAJ")
    qc.ccx(0, 2, 1)
    qc.cx(1, 0)
    return qc.to_gate()


def build_comparator_circuit(n=4):
    """Build a Cuccaro comparator for n-bit comparison."""
    a = QuantumRegister(n, name="a")
    b = QuantumRegister(n, name="b")
    c = QuantumRegister(1, name="c")
    qc = QuantumCircuit(a, b, c, name="Cuccaro Comparator")

    maj = maj_gate()
    umaj = umaj_gate()

    # Forward: MAJ chain
    for i in range(n):
        qc.append(maj, [c[0] if i == 0 else b[i-1], a[i], b[i]])

    # The last carry-out is in b[n-1]
    # For comparator: check final carry
    qc.barrier()

    # Inverse: IMAJ chain (uncompute)
    for i in range(n-1, -1, -1):
        qc.append(umaj, [c[0] if i == 0 else b[i-1], a[i], b[i]])

    return qc


def main():
    n = 4
    qc = build_comparator_circuit(n)

    # Save as matplotlib figure
    fig, ax = plt.subplots(1, 1, figsize=(14, 4))
    qc.draw("mpl", style="iqp", ax=ax, fold=40)
    ax.set_title("Cuccaro Ripple-Carry Comparator (4-bit)", fontsize=14, pad=15)

    output_path = OUTPUT_DIR / "comparator.jpg"
    fig.savefig(output_path, dpi=200, bbox_inches="tight", format="jpg")
    plt.close(fig)
    print(f"Saved: {output_path}")

    # Also save to repo root for thesis copy
    root_path = Path(__file__).resolve().parent.parent / "comparator.jpg"
    fig2, ax2 = plt.subplots(1, 1, figsize=(14, 4))
    qc2 = build_comparator_circuit(n)
    qc2.draw("mpl", style="iqp", ax=ax2, fold=40)
    ax2.set_title("Cuccaro Ripple-Carry Comparator (4-bit)", fontsize=14, pad=15)
    fig2.savefig(root_path, dpi=200, bbox_inches="tight", format="jpg")
    plt.close(fig2)
    print(f"Saved: {root_path}")


if __name__ == "__main__":
    main()
