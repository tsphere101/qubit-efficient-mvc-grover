"""Analytical Clifford+T resource counts.

    Toffoli (2 controls, data target)  = 7 T        (Barenco 1995)
    Gidney AND (2 controls, ancilla)   = 4 T + 0 T  (Gidney 2018, arXiv:1709.06648)
    MCX with c >= 3 controls           = 4*(c-1) T  (Gidney AND ladder, ancilla reuse)
    MCP(pi) with c controls            = MCX with c controls  (H sandwich)
    RY                                 = 3*log2(1/eps) ~= 100 T  (eps = 1e-10)
    CRY                                = 2 RY = 200 T          (sandwich)
    MCRY with c controls               = 4*(c-1) + 200 T       (ladder + sandwich)
    CX, H, X, S                        = 0 T  (Clifford)

A 2-control gate whose target is a dedicated ancilla register
(counter / edge / edge_check / edge_ancilla / exclusion / feasible) is an
AND = 4 T.  A 2-control gate on data (comparator carry chain on pivot bits,
diffuser on vertex register) is a Toffoli = 7 T.

"""

import importlib.util
import itertools
import json
import math
import sys
import time
from collections import Counter
from pathlib import Path

from qiskit import QuantumCircuit, QuantumRegister, transpile
from qiskit.circuit.annotated_operation import AnnotatedOperation, ControlModifier
from qiskit.circuit.library import RYGate

REPO_ROOT = Path(__file__).resolve().parents[1]
SOLVER_DIRS = {
    "arithmetic": REPO_ROOT / "src" / "mvc-solver-1.3.0",
    "dicke": REPO_ROOT / "src" / "mvc-solver-1.4.0",
    "weighted": REPO_ROOT / "src" / "mvc-solver-1.5.0",
}


def load_solver(architecture):
    """Load one solver package under a unique module namespace."""
    solver_dir = SOLVER_DIRS[architecture]
    pkg = f"{architecture}_solver"

    def _load(mod_name, rel_path):
        spec = importlib.util.spec_from_file_location(
            f"{pkg}.{mod_name}", solver_dir / "solver" / rel_path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[f"{pkg}.{mod_name}"] = mod
        spec.loader.exec_module(mod)
        return mod

    models = _load("models", "models.py")
    utils = _load("utils", "utils.py")
    builder = _load("circuit_builder", "circuit_builder.py")
    return builder, models, utils


SOLVERS = {arch: load_solver(arch) for arch in SOLVER_DIRS}

# ---------------------------------------------------------------------------
# Constants (declared in the paper note)
# ---------------------------------------------------------------------------
EPS = 1e-10
T_TOFFOLI = 7
T_AND = 4
T_RY = math.ceil(3 * math.log2(1 / EPS))  # 3*log2(1e10) = 99.66 -> 100
T_CRY = 2 * T_RY

# Registers whose qubits are dedicated ancillas (2-control gate = AND).
AND_REGISTERS = {"counter", "edge", "edge_check", "edge_ancilla", "exclusion", "feasible"}


def complete_graph_edges(n):
    return list(itertools.combinations(range(n), 2))


def path_graph_edges(n):
    return [(i, i + 1) for i in range(n - 1)]


def star_graph_edges(n):
    return [(i, n - 1) for i in range(n - 1)]


# ---------------------------------------------------------------------------
# Primitive classifier
# ---------------------------------------------------------------------------

def classify(circuit):
    """Return Counter of logical primitives with their control counts.

    Keys: 'toffoli', 'and', ('mcx', c), ('mcphase', c), 'ry', 'cry',
    ('mcry', c), 'gds', ('unknown', name).
    """
    counts = Counter()
    for inst in circuit.data:
        op = inst.operation
        name = op.name
        qubits = inst.qubits
        n_total = len(qubits)

        if name in ("barrier", "measure", "reset", "cx", "h", "x", "s", "sdg", "z", "t", "tdg"):
            continue
        if name == "ccx" or (name == "mcx" and n_total == 3):
            bit_info = circuit.find_bit(qubits[-1])
            target_reg = bit_info.registers[0][0].name if bit_info.registers else ""
            if target_reg in AND_REGISTERS:
                counts["and"] += 1
            else:
                counts["toffoli"] += 1
        elif name == "mcx":
            c = n_total - 1
            if c < 3:
                raise AssertionError(f"unexpected mcx with {c} controls")
            counts[("mcx", c)] += 1
        elif name in ("mcphase", "mcp"):
            counts[("mcphase", n_total - 1)] += 1
        elif name == "ry":
            counts["ry"] += 1
        elif name == "cry":
            counts["cry"] += 1
        elif name == "mcry":
            counts[("mcry", n_total - 1)] += 1
        elif isinstance(op, AnnotatedOperation):
            base = op.base_op
            n_ctrl = sum(m.num_ctrl_qubits for m in op.modifiers if isinstance(m, ControlModifier))
            if not isinstance(base, RYGate):
                raise AssertionError(f"unexpected annotated base {base.name}")
            counts[("mcry", n_ctrl)] += 1
        elif name.startswith("circuit-") or name in ("GDS", "GDS_inv"):
            # Opaque composite gate: the GDS (or its inverse) in the Dicke solver.
            counts["gds"] += 1
        else:
            counts[("unknown", name)] += 1
    return counts


def t_cost(counts, t_gds=0):
    """T-count for a classified circuit. t_gds = T per GDSP call."""
    t = 0
    t += counts["toffoli"] * T_TOFFOLI
    t += counts["and"] * T_AND
    t += counts["ry"] * T_RY
    t += counts["cry"] * T_CRY
    t += counts["gds"] * t_gds
    for key, n in counts.items():
        if not isinstance(key, tuple):
            continue
        kind, c = key
        if kind == "mcx":
            t += n * 4 * (c - 1)
        elif kind == "mcphase":
            t += n * (T_TOFFOLI if c == 2 else 4 * (c - 1))
        elif kind == "mcry":
            t += n * (4 * (c - 1) + T_CRY)
    return t


def primitive_columns(counts, t_gds=0):
    """Per-iteration primitive counts for the table.

    #Toffoli: 2-control gates on data + mcp with exactly 2 controls.
    #AND:     2-control ancilla gates + Gidney-ladder steps of mcx(c>=3),
              mcp(c>=3), and mcry(c>=2).
    #RY:      number of RY gates.
    #CRY:     number of CRY gates + one per MCRY (ladder steps join #AND).
    T(G=1) == 7*#Toffoli + 4*#AND + 100*#RY + 200*#CRY.
    """
    n_t = counts["toffoli"]
    n_a = counts["and"]
    n_r = counts["ry"]
    n_c = counts["cry"]
    for key, n in counts.items():
        if not isinstance(key, tuple):
            continue
        kind, c = key
        if kind == "mcx":
            n_a += n * (c - 1)
        elif kind == "mcphase":
            if c == 2:
                n_t += n
            else:
                n_a += n * (c - 1)
        elif kind == "mcry":
            n_a += n * (c - 1)
            n_c += n
    return {"n_toffoli": n_t, "n_and": n_a, "n_ry": n_r, "n_cry": n_c}


# ---------------------------------------------------------------------------
# Logical decomposer: materialize a circuit in {H,S,T,CX} from the declared
# primitives, so T-depth / Depth / CX can be measured on the SAME circuit
# that defines the T-count (no transpiler artifacts, no mixed bases).
# ---------------------------------------------------------------------------

class LogicalDecomposer:
    """Expand logical primitives into the basis {H,S,T,CX}.

    Conventions (identical to the classifier above):
      - 2-control gate with target in AND_REGISTERS  -> Gidney AND (4 T, 4 CX)
      - 2-control gate on data                       -> Barenco Toffoli
                                                        (fixed 7 T / 6 CX layout)
      - mcx(c >= 3) / mcp(pi, c)                     -> (c-1)-AND Gidney ladder
      - annotated mcry(c)                            -> (c-1)-AND ladder + CRY
      - RY                                           -> T_RY serial T gates
      - CRY                                          -> 2 RY + 2 CX (sandwich)
      - opaque GDS gate ('circuit-*' / GDS / GDS_inv)-> recurse into its
                                                        definition with the
                                                        same rules
    Each ladder step uses a fresh ancilla and the T-free AND uncompute is not
    materialized (it contributes 0 T and is not charged, by convention).
    """

    def __init__(self):
        tof = QuantumCircuit(3)
        tof.ccx(0, 1, 2)
        self.toffoli = transpile(tof, basis_gates=["h", "s", "t", "cx"],
                                 optimization_level=0)
        ops = self.toffoli.count_ops()
        t = ops.get("t", 0) + ops.get("tdg", 0)
        assert t == T_TOFFOLI, f"Toffoli layout has {t} T, expected {T_TOFFOLI}"
        assert ops.get("cx", 0) == 6, f"Toffoli layout has {ops.get('cx', 0)} CX, expected 6"
        self.ancillas = []
        self._anc_idx = 0

    def _next_ancilla(self):
        qb = self.ancillas[self._anc_idx]
        self._anc_idx += 1
        return qb

    def _and(self, qc, a, b, t, counter):
        # Gidney AND (compute stage): 4 T, 4 CX.
        qc.t(t)
        qc.cx(a, t)
        qc.tdg(t)
        qc.cx(b, t)
        qc.t(t)
        qc.cx(a, t)
        qc.tdg(t)
        qc.cx(b, t)
        counter["and"] += 1

    def _toffoli(self, qc, a, b, t, counter):
        mapped = (a, b, t)
        for inst in self.toffoli.data:
            qs = [mapped[self.toffoli.find_bit(q).index] for q in inst.qubits]
            qc.append(inst.operation, qs)
        counter["toffoli"] += 1

    def _ry(self, qc, target, counter):
        for _ in range(T_RY):
            qc.t(target)
        counter["ry"] += 1

    def _ladder(self, qc, controls, target, counter, fresh_last=False):
        """(len(controls)-1)-AND Gidney ladder.  Returns the last AND target."""
        prev = controls[0]
        last = len(controls) - 1
        for i in range(1, len(controls)):
            if i == last and not fresh_last:
                nxt = target
            else:
                nxt = self._next_ancilla()
            self._and(qc, prev, controls[i], nxt, counter)
            prev = nxt
        return prev

    def _walk(self, qc, src, instructions, qmap=None):
        for inst in instructions:
            op = inst.operation
            raw_qubits = inst.qubits
            name = op.name
            n = len(raw_qubits)

            if name in ("barrier", "measure", "reset"):
                continue
            if name == "ccx" or (name == "mcx" and n == 3):
                bit_info = src.find_bit(raw_qubits[-1])
                target_reg = bit_info.registers[0][0].name if bit_info.registers else ""
                qubits = [qmap(q) for q in raw_qubits] if qmap else raw_qubits
                if target_reg in AND_REGISTERS:
                    self._and(qc, qubits[0], qubits[1], qubits[2], self.counter)
                else:
                    self._toffoli(qc, qubits[0], qubits[1], qubits[2], self.counter)
            else:
                qubits = [qmap(q) for q in raw_qubits] if qmap else raw_qubits
                if name == "mcx":
                    c = n - 1
                    if c < 3:
                        raise AssertionError(f"unexpected mcx with {c} controls")
                    self._ladder(qc, qubits[:-1], qubits[-1], self.counter)
                elif name in ("mcphase", "mcp"):
                    qc.h(qubits[-1])
                    if n == 3:
                        # Phase flip on |11>: H + Toffoli + H (7 T, 6 CX),
                        # consistent with the classifier's c == 2 rule.
                        self._toffoli(qc, qubits[0], qubits[1], qubits[-1], self.counter)
                    else:
                        self._ladder(qc, qubits[:-1], qubits[-1], self.counter)
                    qc.h(qubits[-1])
                elif name == "ry":
                    self._ry(qc, qubits[0], self.counter)
                elif name == "cry":
                    self._ry(qc, qubits[1], self.counter)
                    qc.cx(qubits[0], qubits[1])
                    self._ry(qc, qubits[1], self.counter)
                elif isinstance(op, AnnotatedOperation):
                    base = op.base_op
                    n_ctrl = sum(m.num_ctrl_qubits for m in op.modifiers
                                 if isinstance(m, ControlModifier))
                    if not isinstance(base, RYGate):
                        raise AssertionError(f"unexpected annotated base {base.name}")
                    controls, target = qubits[:n_ctrl], qubits[n_ctrl]
                    combined = self._ladder(qc, controls, target, self.counter,
                                            fresh_last=True)
                    self._ry(qc, target, self.counter)
                    qc.cx(combined, target)
                    self._ry(qc, target, self.counter)
                elif name.startswith("circuit-") or name in ("GDS", "GDS_inv"):
                    definition = op.definition
                    if definition is None:
                        raise AssertionError(f"opaque gate without definition: {name}")
                    def map_q(q):
                        idx = definition.find_bit(q).index
                        return qubits[idx]
                    self._walk(qc, definition, definition.data, qmap=map_q)
                elif name in ("cx", "h", "x", "z", "s", "sdg", "t", "tdg"):
                    qc.append(op, qubits)
                else:
                    raise AssertionError(f"cannot decompose gate {name}")

    def _ancilla_need(self, src, start, end):
        total = 0
        for inst in src.data[start:end]:
            op = inst.operation
            name = op.name
            n = len(inst.qubits)
            if name == "mcx" and n > 3:
                total += n - 3            # (n-1) controls -> c-2 ancillas
            elif name in ("mcphase", "mcp") and n > 3:
                total += n - 3
            elif isinstance(op, AnnotatedOperation):
                base = op.base_op
                n_ctrl = sum(m.num_ctrl_qubits for m in op.modifiers
                             if isinstance(m, ControlModifier))
                if not isinstance(base, RYGate):
                    raise AssertionError(f"unexpected annotated base {base.name}")
                total += n_ctrl - 1       # c controls -> c-1 ancillas
            elif name.startswith("circuit-") or name in ("GDS", "GDS_inv"):
                definition = op.definition
                if definition is None:
                    raise AssertionError(f"opaque gate without definition: {name}")
                total += self._ancilla_need(definition, 0, len(definition.data))
        return total

    def decompose(self, circuit, start=0, end=None):
        """Materialize circuit.data[start:end]; return (qc, T-count of qc)."""
        end = len(circuit.data) if end is None else end
        need = self._ancilla_need(circuit, start, end)
        qc = QuantumCircuit(*circuit.qregs)
        if need:
            anc = QuantumRegister(need, "mcv_anc")
            qc.add_register(anc)
            self.ancillas = list(anc)
        else:
            self.ancillas = []
        self._anc_idx = 0
        self.counter = Counter()
        self._walk(qc, circuit, circuit.data[start:end])
        ops = qc.count_ops()
        t_count = ops.get("t", 0) + ops.get("tdg", 0)
        return qc, t_count


def prep_extent(circuit, architecture, pivot, n_vertices):
    """Index of the first instruction of the Grover iteration (G=1 scope).

    Apply this to the direct builder output (no remove_final_measurements):
    the state-preparation gates are the leading instructions:
      arithmetic / weighted: X on pivot bits, X/H on kickback, H on each
                             search-space qubit  -> popcount(pivot)+2+n
      dicke: GDS, X/H on kickback                 -> 3
    The expected pattern is asserted so a solver change fails loudly
    instead of silently mixing scopes.
    """
    data = circuit.data
    if architecture == "dicke":
        assert data[0].operation.name.startswith("circuit-") or data[0].operation.name == "GDS", \
            f"dicke prep must start with the GDS gate, got {data[0].operation.name}"
        assert data[1].operation.name == "x" and data[2].operation.name == "h", \
            f"dicke kickback prep mismatch: {data[1].operation.name}, {data[2].operation.name}"
        return 3
    n_pivot = bin(pivot).count("1")
    idx = 0
    for _ in range(n_pivot):
        assert data[idx].operation.name == "x", f"pivot prep mismatch at {idx}"
        idx += 1
    assert data[idx].operation.name == "x", "kickback X prep mismatch"
    idx += 1
    assert data[idx].operation.name == "h", "kickback H prep mismatch"
    idx += 1
    for _ in range(n_vertices):
        assert data[idx].operation.name == "h", f"search-space H prep mismatch at {idx}"
        idx += 1
    assert idx == n_pivot + 2 + n_vertices, "unexpected instructions after prep"
    return idx


def build_logical(builder_cls, models, edges, pivot, weights=None):
    kw = dict(vertex_weights=weights) if weights is not None else {}
    config = models.SolverConfig(
        edges=edges,
        pivot_number=pivot,
        grover_iterations=1,
        barrier=False,
        **kw,
    )
    circuit = builder_cls(config).build()
    circuit.remove_final_measurements(inplace=True)
    return circuit, config


def count_qubit_index(graph_size, row, column):
    """Linear index of the population-counter qubit w_{row, column}, row in 1..n."""
    offset = (row - 1) * (row + 2) // 2
    return offset + column


def standard_diffuser(circuit, vertex_register):
    circuit.h(vertex_register)
    circuit.x(vertex_register)
    circuit.mcp(math.pi, vertex_register[:-1], vertex_register[-1])
    circuit.x(vertex_register)
    circuit.h(vertex_register)


def build_cherif_pieces(graph_size, k):
    edges = complete_graph_edges(graph_size)
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
    for index, (first, second) in enumerate(edges):
        compute.x(vertex_register[first])
        compute.x(vertex_register[second])
        compute.ccx(vertex_register[first], vertex_register[second], edge_register[index])
        compute.x(vertex_register[first])
        compute.x(vertex_register[second])
        compute.x(edge_register[index])
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
    edges = complete_graph_edges(graph_size)
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
    for index, (first, second) in enumerate(edges):
        compute.x(vertex_register[first])
        compute.x(vertex_register[second])
        compute.ccx(vertex_register[first], vertex_register[second], edge_register[index])
        compute.x(vertex_register[first])
        compute.x(vertex_register[second])
    compute.x(edge_register)
    compute.mcx(list(edge_register), feasible_register[0])
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
    circuit.ccx(control_qubit, target_qubit, ancilla_qubit)
    circuit.cx(control_qubit, ancilla_qubit)
    circuit.ccx(control_qubit, ancilla_qubit, target_qubit)


def controlled_increment(circuit, control_qubit, counter_register):
    for bit in range(len(counter_register) - 1, -1, -1):
        circuit.mcx([control_qubit] + list(counter_register[:bit]), counter_register[bit])


def build_jiangyan_pieces(graph_size, k):
    edges = complete_graph_edges(graph_size)
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
    for vertex in range(graph_size):
        controlled_increment(compute, vertex_register[vertex], counter_register)
    for index, (first, second) in enumerate(edges):
        quantum_semaphore(compute, vertex_register[first], edge_register[index], ancilla_register[index])
        compute.cx(edge_register[index], ancilla_register[index])
        quantum_semaphore(compute, vertex_register[second], edge_register[index], ancilla_register[index])

    oracle = preparation.copy()
    oracle.compose(compute, inplace=True)
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



def dicke_support_size(n, k):
    """N = number of n-bit states of Hamming weight <= k (Dicke register)."""
    return sum(math.comb(n, i) for i in range(k + 1))


def boyer_cap(N):
    """W = ceil(sqrt(2N)): per-shot Grover window (Boyer et al. 1998)."""
    return math.ceil(math.sqrt(2 * N))


def verify_constants():
    results = {}
    qc = QuantumCircuit(3)
    qc.ccx(0, 1, 2)
    ts = []
    for lvl in (0, 3):
        tr = transpile(qc, basis_gates=["h", "s", "t", "cx"], optimization_level=lvl)
        ops = tr.count_ops()
        ts.append(ops.get("t", 0) + ops.get("tdg", 0))
    results["toffoli_T"] = ts

    # Gidney AND circuit (arXiv:1709.06648, Fig. 1): 4 T compute.
    and_qc = QuantumCircuit(3, name="AND")
    and_qc.t(2)
    and_qc.cx(0, 2)
    and_qc.tdg(2)
    and_qc.cx(1, 2)
    and_qc.t(2)
    and_qc.cx(0, 2)
    and_qc.tdg(2)
    and_qc.cx(1, 2)
    tr = transpile(and_qc, basis_gates=["t", "tdg", "cx"], optimization_level=0)
    ops = tr.count_ops()
    results["and_T"] = ops.get("t", 0) + ops.get("tdg", 0)

    ry_qc = QuantumCircuit(1)
    ry_qc.ry(0.3, 0)
    tr = transpile(ry_qc, basis_gates=["h", "s", "t", "cx"], optimization_level=3)
    results["ry_qiskit_T"] = tr.count_ops().get("t", 0)
    return results


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def main():
    start = time.time()
    out_dir = REPO_ROOT / "outputs" / f"count_analytical_v2_{time.strftime('%Y%m%d_%H%M%S')}"
    out_dir.mkdir(parents=True, exist_ok=True)

    verification = verify_constants()
    print("verify:", verification)
    assert verification["toffoli_T"] == [7, 7], "Toffoli != 7 T"
    assert verification["and_T"] == 4, "Gidney AND != 4 T"

    decomposer = LogicalDecomposer()
    rows = []

    instances = []
    for n in range(3, 8):
        instances.append(("arithmetic", f"K{n}", complete_graph_edges(n), [1] * n, n))
        instances.append(("dicke", f"K{n}", complete_graph_edges(n), [1] * n, n))
    instances += [
        ("weighted", "K3", complete_graph_edges(3), [1, 2, 3], 4),
        ("weighted", "P4", path_graph_edges(4), [1, 2, 3, 4], 6),
        ("weighted", "S5", star_graph_edges(5), [1, 1, 10, 10, 1], 2),
    ]

    for architecture, label, edges, weights, pivot in instances:
        builder_mod, models, utils = SOLVERS[architecture]
        kw = dict(vertex_weights=weights) if architecture == "weighted" else {}
        config = models.SolverConfig(edges=edges, pivot_number=pivot,
                                     grover_iterations=1, barrier=False, **kw)
        circuit = builder_mod.VertexCoverPenaltyCircuitBuilder(config).build()
        ops = classify(circuit)
        n_vert = config.num_vertices
        unknown = [k for k in ops if isinstance(k, tuple) and k[0] == "unknown"]
        if unknown:
            print(f"WARN {architecture} {label}: unclassified gates {unknown}")

        if architecture == "dicke":
            k = pivot - 1
            gds = utils.create_generalized_dicke_state(n_vert, k)
            gds_counts = classify(gds)
            t_gdsp = t_cost(gds_counts)
            # iteration = prep(GDS) + oracle + diffuser(GDS+reflection+GDS)
            reflect_c = n_vert - 1
            reflection_t = T_TOFFOLI if reflect_c == 2 else 4 * (reflect_c - 1)
            t_diffusion = 2 * t_gdsp + reflection_t
            t_prep = t_gdsp
        else:
            t_gdsp = 0
            t_prep = 0
            # diffuser = H, X, mcp(pi, n-1 controls), X, H
            t_diffusion = T_TOFFOLI if n_vert - 1 == 2 else 4 * (n_vert - 2)

        t_iteration = t_cost(ops, t_gds=t_gdsp)
        t_oracle = t_iteration - t_prep - t_diffusion
        # Per-iteration cost G=1 (excludes the one-time initial preparation).
        t_iter_g1 = t_oracle + t_diffusion

        if architecture == "dicke":
            gds_prim = primitive_columns(gds_counts)
            per_iter = primitive_columns(ops)
            per_iter = {k: per_iter[k] + 2 * gds_prim[k] for k in per_iter}
        else:
            per_iter = primitive_columns(ops)
        assert (7 * per_iter["n_toffoli"] + 4 * per_iter["n_and"]
                + 100 * per_iter["n_ry"] + 200 * per_iter["n_cry"]) == t_iter_g1, (
            f"primitive invariant failed for {architecture} {label}")

        start_idx = prep_extent(circuit, architecture, pivot, n_vert)
        decomposed, t_decomp = decomposer.decompose(circuit, start_idx)
        assert t_decomp == t_iter_g1, (
            f"decomposed T mismatch {architecture} {label}: {t_decomp} != {t_iter_g1}")
        t_depth = decomposed.depth(lambda inst: inst.operation.name in ("t", "tdg"))
        depth = decomposed.depth()
        cx = decomposed.count_ops().get("cx", 0)

        N = dicke_support_size(n_vert, pivot - 1) if architecture == "dicke" else 2 ** n_vert
        W = boyer_cap(N)
        t_tot = W * t_oracle + (2 * W + 1) * t_gdsp

        rows.append({
            "architecture": architecture, "graph": label,
            "vertex_weights": weights, "pivot": pivot,
            "qubits": circuit.num_qubits,
            "primitive_counts": {str(k): v for k, v in ops.items()},
            "t_preparation": t_prep, "t_gdsp": t_gdsp,
            "t_oracle": t_oracle, "t_diffusion": t_diffusion,
            "t_iteration": t_iter_g1,
            "n_toffoli": per_iter["n_toffoli"], "n_and": per_iter["n_and"],
            "n_ry": per_iter["n_ry"], "n_cry": per_iter["n_cry"],
            "t_count_decomposed": t_decomp,
            "t_depth": t_depth, "depth": depth, "cx": cx,
            "N": N, "W": W, "t_tot": t_tot,
        })
        print(f"{architecture:>10} {label:>3} q={circuit.num_qubits:>3} "
              f"T(G=1)={t_iter_g1:>7} T-depth={t_depth:>7} Depth={depth:>9} CX={cx:>7} "
              f"| N={N} W={W} T_tot(W)={t_tot:>8}")

    for architecture in ("cherif", "wang", "jiang_yan"):
        for n in range(3, 8):
            k = n - 1
            if architecture == "cherif":
                prep, oracle, iteration = build_cherif_pieces(n, k)
            elif architecture == "wang":
                prep, oracle, iteration = build_wang_pieces(n)
            else:
                prep, oracle, iteration = build_jiangyan_pieces(n, k)
            t_prep = t_cost(classify(prep))
            t_iteration = t_cost(classify(iteration))
            t_oracle = t_cost(classify(oracle)) - t_prep
            t_diffusion = t_iteration - t_prep - t_oracle
            per_iter = primitive_columns(classify(iteration))
            assert (7 * per_iter["n_toffoli"] + 4 * per_iter["n_and"]
                    + 100 * per_iter["n_ry"] + 200 * per_iter["n_cry"]) == t_iteration, (
                f"primitive invariant failed for {architecture} K{n}")
            decomposed, t_decomp = decomposer.decompose(iteration)
            assert t_decomp == t_iteration, (
                f"decomposed T mismatch {architecture} K{n}: {t_decomp} != {t_iteration}")
            t_depth = decomposed.depth(lambda inst: inst.operation.name in ("t", "tdg"))
            depth = decomposed.depth()
            cx = decomposed.count_ops().get("cx", 0)
            N = 2 ** n
            W = boyer_cap(N)
            t_tot = W * t_oracle
            rows.append({
                "architecture": architecture, "graph": f"K{n}",
                "vertex_weights": [1] * n, "pivot": n,
                "qubits": iteration.num_qubits,
                "primitive_counts": {str(k): v for k, v in classify(iteration).items()},
                "t_preparation": t_prep, "t_gdsp": 0, "t_oracle": t_oracle,
                "t_diffusion": t_diffusion, "t_iteration": t_iteration,
                "n_toffoli": per_iter["n_toffoli"], "n_and": per_iter["n_and"],
                "n_ry": per_iter["n_ry"], "n_cry": per_iter["n_cry"],
                "t_count_decomposed": t_decomp,
                "t_depth": t_depth, "depth": depth, "cx": cx,
                "N": N, "W": W, "t_tot": t_tot,
            })
            print(f"{architecture:>10} K{n}    q={iteration.num_qubits:>3} "
                  f"T_iter={t_iteration:>7} T-depth={t_depth:>7} Depth={depth:>9} CX={cx:>7} "
                  f"| N={N} W={W} T_tot(W)={t_tot:>8}")

    verification["toffoli_cx"] = decomposer.toffoli.count_ops().get("cx", 0)
    (out_dir / "verification.json").write_text(json.dumps(verification, indent=2) + "\n")
    (out_dir / "table_analytical.json").write_text(json.dumps(rows, indent=2) + "\n")
    print(f"\nwrote {out_dir}\ndone in {time.time() - start:.0f}s")


if __name__ == "__main__":
    main()