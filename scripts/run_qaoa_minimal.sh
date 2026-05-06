#!/bin/bash
# Minimal QAOA test — runs K3 p=1 with reduced parameters
# Full reproduction: make qaoa
set -e
cd "$(dirname "$0")/../src/mvc_qaoa"
source ../../.venv/bin/activate
python -c "
import os, sys, json, time
from pathlib import Path
sys.path.insert(0, 'src')
from graphs import BENCHMARK_GRAPHS
from qubo import build_mvc_qubo, qubo_cost, is_valid_cover
from ising import qubo_to_ising
from circuit import build_qaoa_circuit
from exact import solve_exact
from simulator import simulate_and_analyse

# Test: K3, p=1
g = BENCHMARK_GRAPHS[0]
n, edges = g['n'], g['edges']
name = g['name']
p = 1

print(f'=== {name} p={p} ===')
penalty = n + 1
Q = build_mvc_qubo(n, edges, penalty)
J, h = qubo_to_ising(Q)

# Build circuit
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_aer import AerSimulator
qc = build_qaoa_circuit(n, J, h, p)
pm = generate_preset_pass_manager(optimization_level=3, backend=AerSimulator())
qc_t = pm.run(qc)
print(f'  Depth: {qc_t.depth()}, CX: {qc_t.count_ops().get(\"cx\", 0)}')

# Optimize with SPSA
from optimizer import optimize_qaoa

def objective(params):
    qc = build_qaoa_circuit(n, J, h, p, params)
    counts = simulate_and_analyse(qc, shots=4096)['counts']
    return qubo_cost(counts, Q, n)

opt_result = optimize_qaoa(objective, 1, p=p, maxiter=10, random_restarts=1)
print(f'  Best params: {opt_result[\"x\"]}')
print(f'  Best cost: {opt_result[\"fun\"]:.4f}')

# Final simulation
final_qc = build_qaoa_circuit(n, J, h, p, opt_result['x'])
final = simulate_and_analyse(final_qc, shots=4096)
valid = sum(final['counts'].get(k, 0) for k in final['counts'] if is_valid_cover(k, n, edges))
print(f'  Valid cover probability: {valid/4096*100:.1f}%')
print(f'  QAOA test PASSED')
"
