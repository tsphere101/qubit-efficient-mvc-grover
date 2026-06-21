import os
from dataclasses import dataclass, fields, field, asdict
from typing import List, Dict, Optional, Tuple, Any

def pretty_repr(obj):
    cls = type(obj)
    field_lines = []
    for f in fields(obj):
        value = getattr(obj, f.name)
        field_lines.append(f"    {f.name}: {repr(value)}")
    return f"{cls.__name__}(\n" + ",\n".join(field_lines) + "\n)"

@dataclass
class SolverConfig:
    edges: List[Tuple[int, int]]
    pivot_number: int = 0
    grover_iterations: int = 1
    shots: int = 1024
    show_circuit: bool = False
    backend: Optional[Any] = None
    return_counts: bool = True
    calculate_good_states: bool = False
    calculate_theoretical_probabilities: bool = False
    calculate_statevector: bool = False
    output_dir: Optional[str] = None
    barrier: bool = True
    penalty_amount: float = 0.0

    def __post_init__(self):
        nodes = set()
        for u, v in self.edges:
            nodes.add(u); nodes.add(v)
        self.num_vertices: int = max(nodes) + 1 if nodes else 0
        self.num_edges: int = len(self.edges)
        self.phase_kickback_bits: int = 1
        self.classical_register_name: str = 'c'
        self.penalty_amount: float = self.num_vertices + 1
        self.counter_size: int = (self.num_vertices + self.penalty_amount * self.num_edges).bit_length()

    def __repr__(self):
        return pretty_repr(self)

@dataclass
class SimulationResults:
    counts: Dict[str, int] = field(default_factory=dict)
    good_states: Optional[Dict[str, int]] = None
    all_edge_covered_states: Optional[Dict[str, int]] = None
    pop_count_less_than_pivot_states: Optional[Dict[str, int]] = None
    quasi_probabilities: Optional[Dict[str, float]] = None
    theoretical_probabilities: Optional[Dict[str, float]] = None
    statevector: Optional[Dict[str, complex]] = None
    elapsed_time: float = 0.0
    circuit_depth: int = 0
    transpiled_depth: int = 0
    qubits_used: int = 0
    operations: Dict[str, int] = field(default_factory=dict)

    def __repr__(self):
        return pretty_repr(self)    