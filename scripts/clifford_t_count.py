"""Clifford+T resource counts for the three prior-work MVC architectures (Cherif 2024,
Wang 2023, Jiang & Yan 2023) alongside the three proposed architectures.

The prior-work circuits are reconstructed from the papers:
  - Cherif et al. (2024), "A simplified quantum approach using Grover's algorithm
    for solving the vertex cover problem", AICCSA.  Oracle per Algorithm 1 of the
    paper (edge ancillas + size-(k+1) exclusion register C(n, k+1)).
  - Wang, Liang, Bao & Wu (2023), "Quantum speedup for solving the minimum vertex
    cover problem based on Grover search algorithm", Quantum Inf. Process. 22:271.
    Oracle per the five-register design: edge flags, feasible flag, and a pyramidal
    CCNOT population counter of (n+1)(n+2)/2 - 1 qubits.
  - Jiang & Yan (2023), "Novel Quantum Circuit Designs for the Oracle of Grover's
    Algorithm to Solve the Vertex Cover Problem", ECICE.  Oracle per the paper:
    shared quantum counter (ceil(log2 n) qubits), quantum-semaphore edge marking
    (gate order read directly from Fig. 8 of the paper), and an MCX marking gate
    activated when counter == k.

Every circuit is transpiled into the gate set {H, S, T, CX} at optimization level 3
and the T-count, T-depth, total depth, and CX count are reported, matching the
methodology of scripts/clifford_t_count.py so the six rows are directly comparable.
"""

import itertools
import json
import math
import sys
import time
from pathlib import Path

from qiskit import QuantumCircuit, QuantumRegister
from qiskit.transpiler import generate_preset_pass_manager

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import clifford_t_count as base

OUTPUT_DIRECTORY = REPO_ROOT / "outputs" / f"clifford_t_count_prior_{time.strftime('%Y%m%d_%H%M%S')}"
BASIS_GATES = base.BASIS_GATES
GRAPH_SIZES = [3, 4, 5, 6, 7]
GROVER_ARCHITECTURES = ["cherif", "wang", "jiang_yan", "arithmetic", "dicke", "weighted"]



def count_qubit_index(graph_size, row, column):
    """Linear index of the population-counter qubit w_{row, column}, row in 1..n."""
    offset = (row - 1) * (row + 2) // 2
    return offset + column


def standard_diffuser(circuit, vertex_register):
    """The standard Grover diffuser over the vertex register, matching the
    proposed solvers' `_apply_diffuser` exactly (H, X, mcp(pi), X, H)."""
    circuit.h(vertex_register)
    circuit.x(vertex_register)
    circuit.mcp(math.pi, vertex_register[:-1], vertex_register[-1])
    circuit.x(vertex_register)
    circuit.h(vertex_register)


def edge_coverage_and_penalty_register(compute, vertex_register, edge_register, edges):
    """Cherif edge check: edge ancilla = 1 iff the edge is covered (Algorithm 1)."""
    for index, (first, second) in enumerate(edges):
        compute.x(vertex_register[first])
        compute.x(vertex_register[second])
        compute.ccx(vertex_register[first], vertex_register[second], edge_register[index])
        compute.x(vertex_register[first])
        compute.x(vertex_register[second])
        compute.x(edge_register[index])


def build_cherif_pieces(graph_size, k):
    """Cherif control limit for covers <= k. Registers: vertex(n) + edge(m) +
    exclusion(C(n, k+1)) + output(1)."""
    edges = base.complete_graph_edges(graph_size)
    edge_count = len(edges)
    exclusion_count = math.comb(graph_size, k + 1)
    vertex_register = QuantumRegister(graph_size, "vertex")
    edge_register = QuantumRegister(edge_count, "edge")
    exclusion_register = QuantumRegister(exclusion_count, "exclusion")
    output_register = QuantumRegister(1, "output")
    circuit = QuantumCircuit(vertex_register, edge_register, exclusion_register, output_register)
    circuit.h(vertex_register)
    circuit.x(output_register)
    circuit.h(output_register)
    preparation = circuit

    compute = QuantumCircuit(vertex_register, edge_register, exclusion_register, output_register)
    edge_coverage_and_penalty_register(compute, vertex_register, edge_register, edges)
    for index, subset in enumerate(itertools.combinations(range(graph_size), k + 1)):
        compute.mcx([vertex_register[vertex] for vertex in subset], exclusion_register[index])
        compute.x(exclusion_register[index])

    oracle = preparation.copy()
    oracle.compose(compute, inplace=True)
    oracle.mcx(list(edge_register) + list(exclusion_register), output_register[0])
    oracle.compose(compute.inverse(), inplace=True)
    iteration = oracle.copy()
    standard_diffuser(iteration, vertex_register)
    return preparation, oracle, iteration


def build_wang_pieces(graph_size):
    """Wang five-register oracle: vertex(n) + edge(m) + feasible(1) +
    counter((n+1)(n+2)/2 - 1) + kickback(1)."""
    edges = base.complete_graph_edges(graph_size)
    edge_count = len(edges)
    counter_size = (graph_size + 1) * (graph_size + 2) // 2 - 1
    vertex_register = QuantumRegister(graph_size, "vertex")
    edge_register = QuantumRegister(edge_count, "edge")
    feasible_register = QuantumRegister(1, "feasible")
    counter_register = QuantumRegister(counter_size, "counter")
    kickback_register = QuantumRegister(1, "kickback")
    circuit = QuantumCircuit(vertex_register, edge_register, feasible_register,
                             counter_register, kickback_register)
    circuit.h(vertex_register)
    circuit.x(kickback_register)
    circuit.h(kickback_register)
    preparation = circuit

    compute = QuantumCircuit(vertex_register, edge_register, feasible_register,
                             counter_register, kickback_register)
    # Edge coverage: flip endpoints, Toffoli into the edge flag, restore.
    for index, (first, second) in enumerate(edges):
        compute.x(vertex_register[first])
        compute.x(vertex_register[second])
        compute.ccx(vertex_register[first], vertex_register[second], edge_register[index])
        compute.x(vertex_register[first])
        compute.x(vertex_register[second])
    # Invert edge flags so edge = 1 iff covered, then aggregate feasibility.
    compute.x(edge_register)
    compute.mcx(list(edge_register), feasible_register[0])
    # Feasibility ANDs into the population counter pyramid.
    compute.x(vertex_register[0])
    compute.ccx(feasible_register[0], vertex_register[0], counter_register[count_qubit_index(graph_size, 1, 0)])
    compute.x(vertex_register[0])
    compute.ccx(feasible_register[0], vertex_register[0], counter_register[count_qubit_index(graph_size, 1, 1)])
    for row in range(2, graph_size + 1):
        compute.x(vertex_register[row - 1])
        for column in range(0, row):
            compute.ccx(counter_register[count_qubit_index(graph_size, row - 1, column)],
                        vertex_register[row - 1],
                        counter_register[count_qubit_index(graph_size, row, column)])
        compute.x(vertex_register[row - 1])
        for column in range(1, row + 1):
            compute.ccx(counter_register[count_qubit_index(graph_size, row - 1, column - 1)],
                        vertex_register[row - 1],
                        counter_register[count_qubit_index(graph_size, row, column)])

    oracle = preparation.copy()
    oracle.compose(compute, inplace=True)
    for exact_size in range(1, graph_size + 1):
        oracle.cx(counter_register[count_qubit_index(graph_size, graph_size, exact_size)],
                  kickback_register[0])
    oracle.compose(compute.inverse(), inplace=True)
    iteration = oracle.copy()
    standard_diffuser(iteration, vertex_register)
    return preparation, oracle, iteration


def quantum_semaphore(circuit, control_qubit, target_qubit, ancilla_qubit):
    """The Jiang & Yan semaphore (Fig. 8): gates cx(target, ancilla); x(ancilla);
    cx(ancilla, target) applied when the control qubit is |1>.  Implemented as the
    controlled block: ccx(control, target, ancilla); cx(control, ancilla);
    ccx(control, ancilla, target)."""
    circuit.ccx(control_qubit, target_qubit, ancilla_qubit)
    circuit.cx(control_qubit, ancilla_qubit)
    circuit.ccx(control_qubit, ancilla_qubit, target_qubit)


def controlled_increment(circuit, control_qubit, counter_register):
    """Add 1 to the counter when the control qubit is |1>, no ancilla.  The
    ripple matches the proposed solvers' `_increment`: for bit i, toggle it if
    all lower bits and the control are |1>."""
    for bit in range(len(counter_register) - 1, -1, -1):
        circuit.mcx([control_qubit] + list(counter_register[:bit]), counter_register[bit])


def build_jiangyan_pieces(graph_size, k):
    """Jiang & Yan oracle: vertex(n) + counter(ceil(log2 n)) + edge targets(m) +
    edge ancillas(m) + solution(1)."""
    edges = base.complete_graph_edges(graph_size)
    edge_count = len(edges)
    counter_size = math.ceil(math.log2(graph_size))
    vertex_register = QuantumRegister(graph_size, "vertex")
    counter_register = QuantumRegister(counter_size, "counter")
    edge_register = QuantumRegister(edge_count, "edge")
    ancilla_register = QuantumRegister(edge_count, "edge_ancilla")
    solution_register = QuantumRegister(1, "solution")
    circuit = QuantumCircuit(vertex_register, counter_register, edge_register,
                             ancilla_register, solution_register)
    circuit.h(vertex_register)
    circuit.x(solution_register)
    circuit.h(solution_register)
    preparation = circuit

    compute = QuantumCircuit(vertex_register, counter_register, edge_register,
                             ancilla_register, solution_register)
    # Shared quantum counter: controlled increment per selected vertex.
    for vertex in range(graph_size):
        controlled_increment(compute, vertex_register[vertex], counter_register)
    # Quantum semaphores: mark each edge once it is covered by either endpoint.
    for index, (first, second) in enumerate(edges):
        quantum_semaphore(compute, vertex_register[first], edge_register[index], ancilla_register[index])
        compute.cx(edge_register[index], ancilla_register[index])
        quantum_semaphore(compute, vertex_register[second], edge_register[index], ancilla_register[index])

    oracle = preparation.copy()
    oracle.compose(compute, inplace=True)
    # Activate the marking MCX when the counter equals k.
    for bit in range(counter_size):
        if not ((k >> bit) & 1):
            oracle.x(counter_register[bit])
    oracle.mcx(list(edge_register) + list(counter_register), solution_register[0])
    for bit in range(counter_size):
        if not ((k >> bit) & 1):
            oracle.x(counter_register[bit])
    oracle.compose(compute.inverse(), inplace=True)
    iteration = oracle.copy()
    standard_diffuser(iteration, vertex_register)
    return preparation, oracle, iteration


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def build_prior_work_pieces(architecture, graph_size):
    """k = MVC(K_n) - allowed maximum cover size for the prior works."""
    k = graph_size - 1
    if architecture == "cherif":
        return build_cherif_pieces(graph_size, k)
    if architecture == "wang":
        return build_wang_pieces(graph_size)
    return build_jiangyan_pieces(graph_size, k)


def build_solver_pieces(architecture, graph_size):
    builder_module = base.SOLVER_BUILDERS[architecture]
    config = base.make_solver_config(builder_module, graph_size, architecture)
    builder = builder_module.VertexCoverPenaltyCircuitBuilder(config)
    if architecture == "dicke":
        return base.build_dicke_pieces(builder, graph_size)
    counter_method = builder._pop_count if architecture == "arithmetic" else builder._weight_sum
    return base.build_counted_pieces(builder, graph_size, counter_method)


def main():
    start_time = time.time()
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    pass_manager = generate_preset_pass_manager(optimization_level=3, basis_gates=BASIS_GATES)
    rows = []

    for architecture in GROVER_ARCHITECTURES:
        for graph_size in GRAPH_SIZES:
            if architecture in ("cherif", "wang", "jiang_yan"):
                preparation, oracle, iteration = build_prior_work_pieces(architecture, graph_size)
            else:
                preparation, oracle, iteration = build_solver_pieces(architecture, graph_size)

            transpiled_preparation = base.transpile_counts(preparation, pass_manager)
            transpiled_oracle = base.transpile_counts(oracle, pass_manager)
            transpiled_full = base.transpile_counts(iteration, pass_manager)

            t_oracle = transpiled_oracle.t_count - transpiled_preparation.t_count
            t_iteration = transpiled_full.t_count - transpiled_preparation.t_count
            row = {
                "architecture": architecture,
                "graph_size": graph_size,
                "k": graph_size - 1 if architecture in ("cherif", "jiang_yan") else None,
                "t_preparation": transpiled_preparation.t_count,
                "t_oracle": t_oracle,
                "t_iteration": t_iteration,
                "t_total": transpiled_full.t_count,
                "t_depth": transpiled_full.t_depth,
                "depth": transpiled_full.depth,
                "h_count": transpiled_full.operations.get("h", 0),
                "s_count": transpiled_full.operations.get("s", 0),
                "t_gate_count": transpiled_full.operations.get("t", 0),
                "t_dagger_count": transpiled_full.operations.get("tdg", 0),
                "cx_count": transpiled_full.operations.get("cx", 0),
                "qubit_count": transpiled_full.qubit_count,
                "delta": 0,
            }
            rows.append(row)
            print(f"{architecture} K{graph_size}: T_preparation={row['t_preparation']} "
                  f"T_oracle={row['t_oracle']} T_iteration={row['t_iteration']} "
                  f"T_total={row['t_total']} T_depth={row['t_depth']} Depth={row['depth']} "
                  f"H={row['h_count']} S={row['s_count']} T={row['t_gate_count']} "
                  f"T_dagger={row['t_dagger_count']} CX={row['cx_count']} "
                  f"qubits={row['qubit_count']} delta={row['delta']}")

            instance_directory = OUTPUT_DIRECTORY / f"{architecture}_K{graph_size}"
            instance_directory.mkdir(parents=True, exist_ok=True)
            vertex_weights = [1] * graph_size
            base.draw_circuit_image(preparation, instance_directory / "circuit_preparation.jpg", fold=-1)
            base.draw_circuit_image(oracle, instance_directory / "circuit_oracle.jpg", fold=-1)
            base.draw_circuit_image(iteration, instance_directory / "circuit_iteration.jpg", fold=-1)
            base.draw_graph_image(graph_size, vertex_weights, instance_directory / "graph.jpg")
            count_payload = {
                "architecture": architecture,
                "graph_size": graph_size,
                "vertex_weights": vertex_weights,
                "pivot": row["k"] if row["k"] is not None else graph_size,
                "grover_iterations": 1,
            }
            count_payload.update(row)
            (instance_directory / "counts.json").write_text(json.dumps(count_payload, indent=2) + "\n")

    (OUTPUT_DIRECTORY / "table_clifford_t.json").write_text(
        json.dumps(rows, indent=2) + "\n")
    print(f"done in {time.time() - start_time:.0f}s")


if __name__ == "__main__":
    main()
