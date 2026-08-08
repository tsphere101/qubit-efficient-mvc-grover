"""Measure K3-K7 transpiled depth to explicit {CX, RZ, SX, X} basis, barrier=False, for 1, 2, 3 Grover iterations.

Uses the engine's circuit-building path but with an explicit basis_gates
argument in the transpile pass manager. Does NOT modify any source files.
"""
import sys
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOLVER_DIR = REPO_ROOT / "src" / "mvc-solver-1.3.0"
sys.path.insert(0, str(SOLVER_DIR))

from solver.models import SolverConfig
from solver.circuit_builder import VertexCoverPenaltyCircuitBuilder
from solver.utils import complete_graph_edges

from qiskit.transpiler import generate_preset_pass_manager


def measure(n, pivot, grover_iterations=1, barrier=True):
    edges = complete_graph_edges(n)
    config = SolverConfig(
        edges=edges,
        pivot_number=pivot,
        shots=1024,
        grover_iterations=grover_iterations,
        calculate_good_states=False,
        barrier=barrier,
    )
    circuit = VertexCoverPenaltyCircuitBuilder(config).build()

    # Same transpile target as generate_transpiled_comparison.py:37-40
    pm = generate_preset_pass_manager(
        optimization_level=3,
        basis_gates=['cx', 'id', 'rz', 'sx', 'x'],
    )
    transpiled = pm.run(circuit)
    ops = transpiled.count_ops()
    return {
        'n': n,
        'pivot': pivot,
        'grover_iter': grover_iterations,
        'pre_d': circuit.depth(),
        'pre_cx': circuit.count_ops().get('cx', 0),
        'post_d': transpiled.depth(),
        'post_cx': ops.get('cx', 0),
        'post_rz': ops.get('rz', 0),
        'post_sx': ops.get('sx', 0),
        'post_x': ops.get('x', 0),
        'post_id': ops.get('id', 0),
        'qubits': transpiled.num_qubits,
    }


if __name__ == "__main__":
    print(f"{'n':>3} {'iter':>4} {'pivot':>5} {'qubits':>6} {'pre_d':>6} {'pre_cx':>6} "
          f"{'post_d':>6} {'post_cx':>6} {'post_rz':>7} {'post_sx':>7} {'post_x':>6} {'post_id':>7}")
    print("-" * 100)
    for n in [3, 4, 5, 6, 7]:
        for gi in [1, 2, 3]:
            m = measure(n, pivot=n, grover_iterations=gi, barrier=False)
            print(f"{m['n']:>3} {m['grover_iter']:>4} {m['pivot']:>5} {m['qubits']:>6} "
                  f"{m['pre_d']:>6} {m['pre_cx']:>6} "
                  f"{m['post_d']:>6} {m['post_cx']:>6} {m['post_rz']:>7} {m['post_sx']:>7} "
                  f"{m['post_x']:>6} {m['post_id']:>7}")
