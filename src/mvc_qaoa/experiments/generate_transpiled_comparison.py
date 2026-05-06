#!/usr/bin/env python3
"""
Reproducible transpiled resource comparison: QAOA vs Grover architectures.
Measures circuit depth and CX count transpiled to {CX, RZ, SX, X} basis.

Usage:
    python generate_transpiled_comparison.py

Output:
    - Updated metrics JSON (grover_vs_qaoa_metrics_transpiled.json)
    - Depth comparison figure (fig_depth_comparison.png)
"""
import sys, json
sys.path.insert(0, '/Users/topfee/Desktop/quantum-research/src/mvc_qaoa')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from qiskit.transpiler import generate_preset_pass_manager

from src.circuit import build_qaoa_circuit
from src.qubo import build_mvc_qubo
from src.ising import qubo_to_ising

OUT_DIR = '/Users/topfee/Desktop/quantum-research/src/mvc_qaoa/experiments/qaoa_vs_grover_comparison'

GRAPHS = {
    'K3': (3, [(0,1),(0,2),(1,2)]),
    'K4': (4, [(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)]),
    'K5': (5, [(i,j) for i in range(5) for j in range(i+1,5)]),
    'K6': (6, [(i,j) for i in range(6) for j in range(i+1,6)]),
    'K7': (7, [(i,j) for i in range(7) for j in range(i+1,7)]),
}

PM = generate_preset_pass_manager(
    optimization_level=3,
    basis_gates=['cx', 'id', 'rz', 'sx', 'x']
)

def transpiled_metrics(qc):
    qc_t = PM.run(qc)
    return {
        'depth': qc_t.depth(),
        'cx': qc_t.count_ops().get('cx', 0),
        'gates': qc_t.size(),
    }

# QAOA
qaoa_metrics = {}
for name, (n, edges) in sorted(GRAPHS.items()):
    Q = build_mvc_qubo(n, edges)
    terms, const = qubo_to_ising(Q)
    res = {}
    for p in [1, 2, 3]:
        gammas = [0.5] * p
        betas = [0.5] * p
        qc = build_qaoa_circuit(terms, gammas, betas, n)
        res[p] = transpiled_metrics(qc)
    qaoa_metrics[name] = res

# Grover: Dicke
for m in list(sys.modules.keys()):
    if 'solver' in m:
        del sys.modules[m]
sys.path.insert(0, '/Users/topfee/Desktop/quantum-research/src/mvc-solver-1.4.0')
from solver.models import SolverConfig as DickeConfig
from solver.circuit_builder import VertexCoverPenaltyCircuitBuilder as DickeBuilder

dicke_metrics = {}
for name, (n, edges) in sorted(GRAPHS.items()):
    cfg = DickeConfig(edges=edges, pivot_number=n, grover_iterations=1, barrier=False)
    builder = DickeBuilder(cfg)
    qc = builder.build()
    dicke_metrics[name] = transpiled_metrics(qc)

# Grover: Arithmetic
for m in list(sys.modules.keys()):
    if 'solver' in m:
        del sys.modules[m]
sys.path.insert(0, '/Users/topfee/Desktop/quantum-research/src/mvc-solver-1.3.0')
from solver.models import SolverConfig as ArithConfig
from solver.circuit_builder import VertexCoverPenaltyCircuitBuilder as ArithBuilder

arith_metrics = {}
for name, (n, edges) in sorted(GRAPHS.items()):
    cfg = ArithConfig(edges=edges, pivot_number=n, grover_iterations=1, barrier=False)
    builder = ArithBuilder(cfg)
    qc = builder.build()
    arith_metrics[name] = transpiled_metrics(qc)

# Combine into one JSON
combined = []
for name in sorted(GRAPHS.keys()):
    n, _ = GRAPHS[name]
    combined.append({
        'graph': name, 'n': n,
        'qaoa_p1': qaoa_metrics[name][1],
        'qaoa_p2': qaoa_metrics[name][2],
        'qaoa_p3': qaoa_metrics[name][3],
        'dicke': dicke_metrics[name],
        'arith': arith_metrics[name],
    })

with open(f'{OUT_DIR}/grover_vs_qaoa_metrics_transpiled.json', 'w') as f:
    json.dump(combined, f, indent=2)
print("Saved metrics JSON")

# Plot
graphs_list = sorted(GRAPHS.keys())
x = np.arange(len(graphs_list))

qaoa_p1_d = [qaoa_metrics[g][1]['depth'] for g in graphs_list]
qaoa_p2_d = [qaoa_metrics[g][2]['depth'] for g in graphs_list]
qaoa_p3_d = [qaoa_metrics[g][3]['depth'] for g in graphs_list]
dicke_d   = [dicke_metrics[g]['depth'] for g in graphs_list]
arith_d   = [arith_metrics[g]['depth'] for g in graphs_list]

fig, ax = plt.subplots(figsize=(8, 5))
ax.semilogy(x, qaoa_p1_d, 'o-', label='QAOA $p=1$', color='#5B9BD5', markersize=5)
ax.semilogy(x, qaoa_p2_d, 's-', label='QAOA $p=2$', color='#ED7D31', markersize=5)
ax.semilogy(x, qaoa_p3_d, '^-', label='QAOA $p=3$', color='#70AD47', markersize=5)
ax.semilogy(x, dicke_d,   'v-', label='Dicke-state (Ours)', color='#0000FF', markersize=5)
ax.semilogy(x, arith_d,   'D-', label='Arithmetic-based (Ours)', color='#800080', markersize=5)

ax.set_xticks(x)
ax.set_xticklabels(graphs_list)
ax.set_xlabel('Graph')
ax.set_ylabel('Transpiled Circuit Depth')
ax.set_title('Resource Comparison (Transpiled to {CX, RZ, SX, X})')
ax.legend()
ax.grid(True, alpha=0.3)

plt.savefig(f'{OUT_DIR}/fig_depth_comparison.png', dpi=150, bbox_inches='tight')
print("Saved depth figure")
