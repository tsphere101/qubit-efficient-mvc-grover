#!/usr/bin/env python3
"""Extract Grover circuit metrics for a single solver version."""
import sys
import json
from pathlib import Path

solver_dir = Path(sys.argv[1])
graph_name = sys.argv[2]
n = int(sys.argv[3])
edges_str = sys.argv[4]

# Parse edges
edges = []
if edges_str:
    for part in edges_str.split(";"):
        u, v = part.split(",")
        edges.append((int(u), int(v)))

sys.path.insert(0, str(solver_dir))
from solver.models import SolverConfig
from solver.circuit_builder import VertexCoverPenaltyCircuitBuilder

mvc_sizes = {
    "K3": 2, "K4": 3, "K5": 4, "K6": 5, "K7": 6,
    "C4": 2, "C5": 3, "C6": 3,
    "S4": 1, "S5": 1,
    "P4": 2, "P5": 2,
    "Diamond": 2, "Bowtie": 2, "Tent": 2,
}
pivot = mvc_sizes.get(graph_name, n) + 1

cfg = SolverConfig(edges=edges, pivot_number=pivot, grover_iterations=1, barrier=False)
builder = VertexCoverPenaltyCircuitBuilder(cfg)
qc = builder.build()

result = {
    "name": graph_name,
    "n": n,
    "m": len(edges),
    "qubits": qc.num_qubits,
    "depth": qc.depth(),
    "cnots": qc.count_ops().get("cx", 0),
    "total_gates": qc.size(),
}
print(json.dumps(result))
