#!/usr/bin/env python3
"""Dry-run verification of QAOA experiment pipeline.
Builds circuits and checks resource counts WITHOUT running full optimization."""

import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src/mvc_qaoa/src"))

from graphs import BENCHMARK_GRAPHS
from qubo import build_mvc_qubo
from ising import qubo_to_ising
from circuit import build_qaoa_circuit
from qiskit_aer import AerSimulator
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

print("=" * 60)
print("QAOA Experiment Pipeline — Dry Run Verification")
print("=" * 60)

pm = generate_preset_pass_manager(optimization_level=3, backend=AerSimulator())

for g in BENCHMARK_GRAPHS:
    name = g["name"]
    n = g["n"]
    edges = g["edges"]
    penalty = n + 1

    Q = build_mvc_qubo(n, edges, penalty)
    J, h = qubo_to_ising(Q)

    for p in [1, 2, 3]:
        # Use random angles for circuit construction only
        import numpy as np
        gammas = np.random.uniform(-np.pi, np.pi, p)
        betas = np.random.uniform(-np.pi, np.pi, p)

        qc = build_qaoa_circuit(n, J, h, p, params=np.concatenate([gammas, betas]))
        qc_t = pm.run(qc)
        depth = qc_t.depth()
        cx = qc_t.count_ops().get("cx", 0)
        qubits = qc_t.num_qubits
        print(f"  {name:8s} p={p} | qubits={qubits:2d} | depth={depth:6d} | CX={cx:5d}")

print("=" * 60)
print("All circuits built successfully!")
