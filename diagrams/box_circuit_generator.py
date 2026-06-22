"""
Hierarchical Circuit Diagram Generator for MVC Paper

Generates boxed/hierarchical circuit diagrams for the three architectures:
- Dicke-state (v1.4.0)
- Arithmetic (v1.3.0)  
- Weighted (v1.5.0)

Uses Qiskit's .to_gate() to create hierarchical boxes with internal circuit details.
"""

import os

from qiskit import QuantumCircuit, QuantumRegister

# Import from copied solvers (for diagram generation only)
from solvers.arithmetic_for_diagram.models import SolverConfig as ArithmeticConfig
from solvers.arithmetic_for_diagram.circuit_builder import VertexCoverPenaltyCircuitBuilder as ArithmeticBuilder

from solvers.dicke_for_diagram.models import SolverConfig as DickeConfig
from solvers.dicke_for_diagram.circuit_builder import VertexCoverPenaltyCircuitBuilder as DickeBuilder

from solvers.weighted_for_diagram.models import SolverConfig as WeightedConfig
from solvers.weighted_for_diagram.circuit_builder import VertexCoverPenaltyCircuitBuilder as WeightedBuilder

# Import GDSP function
from solvers.dicke_state_for_diagram.generalized_dicke_state import create_generalized_dicke_state


OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'outputs')


def create_popcount_circuit(num_vertices, counter_size):
    """Create Popcount circuit matching actual v1.3.0 implementation (ripple-carry incrementer)"""
    qc = QuantumCircuit(num_vertices + counter_size, name='Popcount')
    
    search_space = list(range(num_vertices))
    counter = list(range(num_vertices, num_vertices + counter_size))
    
    for k in range(num_vertices):
        for i in range(counter_size - 1, -1, -1):
            controls = [search_space[k]] + counter[:i]
            
            if len(controls) == 1:
                qc.cx(controls[0], counter[i])
            else:
                qc.mcx(controls, counter[i])
    
    return qc


def create_penalty_adder_circuit(edges, num_vertices, counter_size, penalty_amount):
    """Create Penalty Adder circuit with actual gates for uncovered edges"""
    qc = QuantumCircuit(num_vertices + counter_size, name='Penalty Adder')
    
    penalty_bits = []
    temp_val = penalty_amount
    bit_idx = 0
    while temp_val > 0:
        if temp_val & 1:
            penalty_bits.append(bit_idx)
        temp_val >>= 1
        bit_idx += 1
    
    for edge_idx, (u, v) in enumerate(edges):
        qc.x([u, v])
        
        for p_bit in penalty_bits:
            if p_bit < counter_size:
                target_idx = num_vertices + p_bit
                qc.ccx(u, v, target_idx)
        
        qc.x([u, v])
    
    return qc


def create_comparator_box(counter_size):
    """Create Comparator box (referenced to paper, no internal detail)"""
    qc = QuantumCircuit(2 * counter_size + 2, name='Cuccaro Comparator')
    return qc.to_gate(label='Cuccaro\nComparator')


def create_arithmetic_hierarchical():
    """Create hierarchical circuit for Arithmetic architecture (v1.3.0)"""
    print("\n=== Creating Arithmetic Hierarchical Circuit ===")
    
    edges = [(0, 1), (1, 2), (0, 2)]
    pivot_number = 4
    grover_iterations = 1
    
    config = ArithmeticConfig(
        edges=edges,
        pivot_number=pivot_number,
        grover_iterations=grover_iterations,
        barrier=True
    )
    
    num_vertices = config.num_vertices
    counter_size = config.counter_size
    
    builder = ArithmeticBuilder(config)
    full_circuit = builder.build()
    
    circuit = full_circuit.copy()
    circuit.remove_final_measurements()
    
    hier_circuit = QuantumCircuit(
        QuantumRegister(num_vertices, 'vertex'),
        QuantumRegister(counter_size, 'counter'),
        QuantumRegister(counter_size, 'pivot'),
        QuantumRegister(1, 'kickback'),
        QuantumRegister(1, 'comparator_z'),
        QuantumRegister(1, 'comparator_c'),
        name='Arithmetic Grover Iteration'
    )
    
    hier_circuit.h(range(num_vertices))
    hier_circuit.barrier()
    
    oracle_circuit = QuantumCircuit(
        QuantumRegister(num_vertices),
        QuantumRegister(counter_size),
        QuantumRegister(counter_size),
        QuantumRegister(1),
        QuantumRegister(1),
        QuantumRegister(1),
        name='Oracle'
    )
    oracle_gate = oracle_circuit.to_gate(label='Oracle')
    hier_circuit.append(oracle_gate, list(range(num_vertices)) + list(range(num_vertices, num_vertices + counter_size * 2 + 3)))
    hier_circuit.barrier()
    
    hier_circuit.cx(num_vertices + 2 * counter_size + 1, num_vertices + 2 * counter_size)
    hier_circuit.barrier()
    
    diffuser_circuit = QuantumCircuit(num_vertices, name='Grover Diffuser')
    diffuser_gate = diffuser_circuit.to_gate(label='Grover\nDiffuser')
    hier_circuit.append(diffuser_gate, range(num_vertices))
    hier_circuit.barrier()
    
    return circuit, hier_circuit


def create_arithmetic_oracle_detail():
    """Create detailed Oracle breakdown with gate-level Popcount and Penalty Adder"""
    print("\n=== Creating Arithmetic Oracle Detail ===")
    
    edges = [(0, 1), (1, 2), (0, 2)]
    pivot_number = 4
    
    config = ArithmeticConfig(
        edges=edges,
        pivot_number=pivot_number,
        grover_iterations=1,
        barrier=True
    )
    
    num_vertices = config.num_vertices
    counter_size = config.counter_size
    penalty_amount = config.penalty_amount
    
    breakdown = QuantumCircuit(
        QuantumRegister(num_vertices, 'vertex'),
        QuantumRegister(counter_size, 'counter'),
        QuantumRegister(counter_size, 'pivot'),
        QuantumRegister(1, 'kickback'),
        QuantumRegister(1, 'comparator_z'),
        QuantumRegister(1, 'comparator_c'),
        name='Oracle Breakdown'
    )
    
    popcount_qc = create_popcount_circuit(num_vertices, counter_size)
    popcount_gate = popcount_qc.to_gate(label='Popcount')
    breakdown.append(popcount_gate, list(range(num_vertices)) + list(range(num_vertices, num_vertices + counter_size)))
    breakdown.barrier()
    
    breakdown.x(range(num_vertices))
    breakdown.barrier()
    
    penalty_qc = create_penalty_adder_circuit(edges, num_vertices, counter_size, penalty_amount)
    penalty_gate = penalty_qc.to_gate(label='Penalty\nAdder')
    breakdown.append(penalty_gate, list(range(num_vertices)) + list(range(num_vertices, num_vertices + counter_size)))
    breakdown.barrier()
    
    breakdown.x(range(num_vertices))
    breakdown.barrier()
    
    comparator_gate = create_comparator_box(counter_size)
    breakdown.append(comparator_gate, list(range(num_vertices, num_vertices + counter_size)) + 
                     list(range(num_vertices + counter_size, num_vertices + 2 * counter_size + 2)))
    
    return breakdown


def create_dicke_hierarchical():
    """Create hierarchical circuit for Dicke-state architecture (v1.4.0)"""
    print("\n=== Creating Dicke-state Hierarchical Circuit ===")
    
    edges = [(0, 1), (1, 2), (0, 2)]
    pivot_number = 4
    grover_iterations = 1
    
    config = DickeConfig(
        edges=edges,
        pivot_number=pivot_number,
        grover_iterations=grover_iterations,
        barrier=True
    )
    
    num_vertices = config.num_vertices
    m = len(edges)
    
    builder = DickeBuilder(config)
    full_circuit = builder.build()
    
    circuit = full_circuit.copy()
    circuit.remove_final_measurements()
    
    hier_circuit = QuantumCircuit(
        QuantumRegister(num_vertices, 'vertex'),
        QuantumRegister(m, 'edge_ancilla'),
        QuantumRegister(1, 'kickback'),
        QuantumRegister(1, 'all_feasible'),
        name='Dicke-state Grover Iteration'
    )
    
    k = pivot_number - 1
    gdsp_circuit = create_generalized_dicke_state(num_vertices, k)
    gdsp_gate = gdsp_circuit.to_gate(label='GDSP')
    hier_circuit.append(gdsp_gate, range(num_vertices))
    hier_circuit.barrier()
    
    oracle_circuit = QuantumCircuit(
        QuantumRegister(num_vertices),
        QuantumRegister(m),
        QuantumRegister(1),
        QuantumRegister(1),
        name='Oracle'
    )
    oracle_gate = oracle_circuit.to_gate(label='Oracle')
    hier_circuit.append(oracle_gate, list(range(num_vertices + m + 2)))
    hier_circuit.barrier()
    
    hier_circuit.cx(num_vertices + m, num_vertices + m + 1)
    hier_circuit.barrier()
    
    diffuser_circuit = QuantumCircuit(num_vertices, name='GDS Diffuser')
    diffuser_gate = diffuser_circuit.to_gate(label='GDS\nDiffuser')
    hier_circuit.append(diffuser_gate, range(num_vertices))
    hier_circuit.barrier()
    
    return circuit, hier_circuit


def create_dicke_oracle_detail():
    """Create detailed Oracle breakdown for Dicke-state"""
    print("\n=== Creating Dicke-state Oracle Detail ===")
    
    edges = [(0, 1), (1, 2), (0, 2)]
    num_vertices = 3
    m = len(edges)
    
    breakdown = QuantumCircuit(
        QuantumRegister(num_vertices, 'vertex'),
        QuantumRegister(m, 'edge_ancilla'),
        QuantumRegister(1, 'kickback'),
        QuantumRegister(1, 'all_feasible'),
        name='Oracle Breakdown'
    )
    
    edge_check_qc = QuantumCircuit(num_vertices + m, name='Edge Check')
    for idx, (u, v) in enumerate(edges):
        edge_check_qc.x([u, v])
        edge_check_qc.ccx(u, v, num_vertices + idx)
        edge_check_qc.x([u, v])
    
    edge_check_gate = edge_check_qc.to_gate(label='Edge\nCheck')
    breakdown.append(edge_check_gate, list(range(num_vertices)) + list(range(num_vertices, num_vertices + m)))
    breakdown.barrier()
    
    agg_qc = QuantumCircuit(m + 1, name='All-Feasible')
    agg_gate = agg_qc.to_gate(label='All-Feasible\nAggregation')
    breakdown.append(agg_gate, list(range(num_vertices, num_vertices + m + 1)))
    
    return breakdown


def create_weighted_hierarchical():
    """Create hierarchical circuit for Weighted architecture (v1.5.0)"""
    print("\n=== Creating Weighted Hierarchical Circuit ===")
    
    edges = [(0, 1), (1, 2), (0, 2)]
    pivot_number = 4
    grover_iterations = 1
    vertex_weights = [1, 2, 3]
    
    config = WeightedConfig(
        edges=edges,
        pivot_number=pivot_number,
        grover_iterations=grover_iterations,
        vertex_weights=vertex_weights,
        barrier=True
    )
    
    num_vertices = config.num_vertices
    counter_size = config.counter_size
    
    builder = WeightedBuilder(config)
    full_circuit = builder.build()
    
    circuit = full_circuit.copy()
    circuit.remove_final_measurements()
    
    hier_circuit = QuantumCircuit(
        QuantumRegister(num_vertices, 'vertex'),
        QuantumRegister(counter_size, 'counter'),
        QuantumRegister(counter_size, 'pivot'),
        QuantumRegister(1, 'kickback'),
        QuantumRegister(1, 'comparator_z'),
        QuantumRegister(1, 'comparator_c'),
        name='Weighted Grover Iteration'
    )
    
    hier_circuit.h(range(num_vertices))
    hier_circuit.barrier()
    
    oracle_circuit = QuantumCircuit(
        QuantumRegister(num_vertices),
        QuantumRegister(counter_size),
        QuantumRegister(counter_size),
        QuantumRegister(1),
        QuantumRegister(1),
        QuantumRegister(1),
        name='Oracle'
    )
    oracle_gate = oracle_circuit.to_gate(label='Oracle')
    hier_circuit.append(oracle_gate, list(range(num_vertices)) + list(range(num_vertices, num_vertices + counter_size * 2 + 3)))
    hier_circuit.barrier()
    
    hier_circuit.cx(num_vertices + 2 * counter_size + 1, num_vertices + 2 * counter_size)
    hier_circuit.barrier()
    
    diffuser_circuit = QuantumCircuit(num_vertices, name='Grover Diffuser')
    diffuser_gate = diffuser_circuit.to_gate(label='Grover\nDiffuser')
    hier_circuit.append(diffuser_gate, range(num_vertices))
    hier_circuit.barrier()
    
    return circuit, hier_circuit


def create_weighted_oracle_detail():
    """Create detailed Oracle breakdown for Weighted architecture"""
    print("\n=== Creating Weighted Oracle Detail ===")
    
    edges = [(0, 1), (1, 2), (0, 2)]
    pivot_number = 4
    vertex_weights = [1, 2, 3]
    
    config = WeightedConfig(
        edges=edges,
        pivot_number=pivot_number,
        grover_iterations=1,
        vertex_weights=vertex_weights,
        barrier=True
    )
    
    num_vertices = config.num_vertices
    counter_size = config.counter_size
    penalty_amount = config.penalty_amount
    
    breakdown = QuantumCircuit(
        QuantumRegister(num_vertices, 'vertex'),
        QuantumRegister(counter_size, 'counter'),
        QuantumRegister(counter_size, 'pivot'),
        QuantumRegister(1, 'kickback'),
        QuantumRegister(1, 'comparator_z'),
        QuantumRegister(1, 'comparator_c'),
        name='Oracle Breakdown'
    )
    
    weighted_popcount_qc = QuantumCircuit(num_vertices + counter_size, name='Weighted Popcount')
    for v_idx in range(num_vertices):
        weight = vertex_weights[v_idx]
        
        weight_bits = []
        temp_val = weight
        bit_idx = 0
        while temp_val > 0:
            if temp_val & 1:
                weight_bits.append(bit_idx)
            temp_val >>= 1
            bit_idx += 1
        
        for w_bit in weight_bits:
            if w_bit < counter_size:
                target_idx = num_vertices + w_bit
                weighted_popcount_qc.cx(v_idx, target_idx)
    
    weighted_popcount_gate = weighted_popcount_qc.to_gate(label='Weighted\nPopcount')
    breakdown.append(weighted_popcount_gate, list(range(num_vertices)) + list(range(num_vertices, num_vertices + counter_size)))
    breakdown.barrier()
    
    breakdown.x(range(num_vertices))
    breakdown.barrier()
    
    penalty_qc = create_penalty_adder_circuit(edges, num_vertices, counter_size, penalty_amount)
    penalty_gate = penalty_qc.to_gate(label='Penalty\nAdder')
    breakdown.append(penalty_gate, list(range(num_vertices)) + list(range(num_vertices, num_vertices + counter_size)))
    breakdown.barrier()
    
    breakdown.x(range(num_vertices))
    breakdown.barrier()
    
    comparator_gate = create_comparator_box(counter_size)
    breakdown.append(comparator_gate, list(range(num_vertices, num_vertices + counter_size)) + 
                     list(range(num_vertices + counter_size, num_vertices + 2 * counter_size + 2)))
    
    return breakdown


def create_popcount_detail():
    """Create detailed Popcount circuit matching actual implementation"""
    print("\n=== Creating Popcount Detail ===")
    
    num_vertices = 3
    counter_size = 4
    
    popcount_detail = QuantumCircuit(
        QuantumRegister(num_vertices, 'vertex'),
        QuantumRegister(counter_size, 'counter'),
        name='Popcount Detail'
    )
    
    for k in range(num_vertices):
        for i in range(counter_size - 1, -1, -1):
            controls = [k] + list(range(num_vertices, num_vertices + i))
            
            if len(controls) == 1:
                popcount_detail.cx(controls[0], num_vertices + i)
            else:
                popcount_detail.mcx(controls, num_vertices + i)
        
        popcount_detail.barrier()
    
    return popcount_detail


def create_weighted_popcount_detail():
    """Create detailed Weighted Popcount circuit matching v1.5.0 implementation"""
    print("\n=== Creating Weighted Popcount Detail ===")
    
    num_vertices = 3
    counter_size = 4
    vertex_weights = [1, 2, 3]
    
    weighted_detail = QuantumCircuit(
        QuantumRegister(num_vertices, 'vertex'),
        QuantumRegister(counter_size, 'counter'),
        name='Weighted Popcount Detail'
    )
    
    for k in range(num_vertices):
        weight = vertex_weights[k]
        
        weight_bits = []
        temp_val = weight
        bit_idx = 0
        while temp_val > 0:
            if temp_val & 1:
                weight_bits.append(bit_idx)
            temp_val >>= 1
            bit_idx += 1
        
        for p_bit in weight_bits:
            if p_bit < counter_size:
                for i in range(counter_size - 1, p_bit - 1, -1):
                    target_idx = num_vertices + i
                    controls = [k] + list(range(num_vertices, num_vertices + i - p_bit))
                    
                    if len(controls) == 1:
                        weighted_detail.cx(controls[0], target_idx)
                    else:
                        weighted_detail.mcx(controls, target_idx)
        
        weighted_detail.barrier()
    
    return weighted_detail


def create_dicke_edge_check_detail():
    """Create detailed Edge Check circuit for Dicke-state"""
    print("\n=== Creating Dicke-state Edge Check Detail ===")
    
    edges = [(0, 1), (1, 2), (0, 2)]
    num_vertices = 3
    m = len(edges)
    
    edge_check_detail = QuantumCircuit(
        QuantumRegister(num_vertices, 'vertex'),
        QuantumRegister(m, 'edge_ancilla'),
        name='Edge Check Detail'
    )
    
    for idx, (u, v) in enumerate(edges):
        edge_check_detail.x([u, v])
        edge_check_detail.ccx(u, v, num_vertices + idx)
        edge_check_detail.x([u, v])
        edge_check_detail.barrier()
    
    return edge_check_detail


def create_penalty_detail():
    """Create detailed Penalty Adder circuit matching v1.3.0 implementation"""
    print("\n=== Creating Penalty Detail ===")
    
    edges = [(0, 1), (1, 2), (0, 2)]
    num_vertices = 3
    counter_size = 4
    penalty_amount = 4  # Default penalty for K3
    
    penalty_detail = QuantumCircuit(
        QuantumRegister(num_vertices, 'vertex'),
        QuantumRegister(counter_size, 'counter'),
        name='Penalty Adder Detail'
    )
    
    penalty_bits = []
    temp_val = penalty_amount
    bit_idx = 0
    while temp_val > 0:
        if temp_val & 1:
            penalty_bits.append(bit_idx)
        temp_val >>= 1
        bit_idx += 1
    
    for u, v in edges:
        penalty_detail.x([u, v])
        
        for p_bit in penalty_bits:
            if p_bit < counter_size:
                for i in range(counter_size - 1, p_bit - 1, -1):
                    target_idx = num_vertices + i
                    controls = [u, v] + list(range(num_vertices, num_vertices + i - p_bit))
                    
                    if len(controls) == 2:
                        penalty_detail.ccx(controls[0], controls[1], target_idx)
                    else:
                        penalty_detail.mcx(controls, target_idx)
        
        penalty_detail.x([u, v])
        penalty_detail.barrier()
    
    return penalty_detail


def create_dicke_k7_circuit():
    """Create Dicke-state circuit for K7"""
    print("\n=== Creating Dicke-state K7 Circuit ===")
    
    # K7 has 21 edges
    edges = [(i, j) for i in range(7) for j in range(i+1, 7)]
    pivot_number = 7
    grover_iterations = 1
    
    config = DickeConfig(
        edges=edges,
        pivot_number=pivot_number,
        grover_iterations=grover_iterations,
        barrier=True
    )
    
    num_vertices = config.num_vertices
    m = len(edges)
    
    builder = DickeBuilder(config)
    full_circuit = builder.build()
    
    circuit = full_circuit.copy()
    circuit.remove_final_measurements()
    
    # Create hierarchical circuit
    hier_circuit = QuantumCircuit(
        QuantumRegister(num_vertices, 'vertex'),
        QuantumRegister(m, 'edge_ancilla'),
        QuantumRegister(1, 'kickback'),
        QuantumRegister(1, 'all_feasible'),
        name='Dicke-state K7'
    )
    
    k = pivot_number - 1
    gdsp_circuit = create_generalized_dicke_state(num_vertices, k)
    gdsp_gate = gdsp_circuit.to_gate(label='GDSP')
    hier_circuit.append(gdsp_gate, range(num_vertices))
    hier_circuit.barrier()
    
    oracle_circuit = QuantumCircuit(
        QuantumRegister(num_vertices),
        QuantumRegister(m),
        QuantumRegister(1),
        QuantumRegister(1),
        name='Oracle'
    )
    oracle_gate = oracle_circuit.to_gate(label='Oracle')
    hier_circuit.append(oracle_gate, list(range(num_vertices + m + 2)))
    hier_circuit.barrier()
    
    hier_circuit.cx(num_vertices + m, num_vertices + m + 1)
    hier_circuit.barrier()
    
    diffuser_circuit = QuantumCircuit(num_vertices, name='GDS Diffuser')
    diffuser_gate = diffuser_circuit.to_gate(label='GDS\nDiffuser')
    hier_circuit.append(diffuser_gate, range(num_vertices))
    hier_circuit.barrier()
    
    return circuit, hier_circuit


def create_arithmetic_k7_circuit():
    """Create Arithmetic circuit for K7"""
    print("\n=== Creating Arithmetic K7 Circuit ===")
    
    # K7 has 21 edges
    edges = [(i, j) for i in range(7) for j in range(i+1, 7)]
    pivot_number = 7
    grover_iterations = 1
    
    config = ArithmeticConfig(
        edges=edges,
        pivot_number=pivot_number,
        grover_iterations=grover_iterations,
        barrier=True
    )
    
    num_vertices = config.num_vertices
    counter_size = config.counter_size
    
    builder = ArithmeticBuilder(config)
    full_circuit = builder.build()
    
    circuit = full_circuit.copy()
    circuit.remove_final_measurements()
    
    hier_circuit = QuantumCircuit(
        QuantumRegister(num_vertices, 'vertex'),
        QuantumRegister(counter_size, 'counter'),
        QuantumRegister(counter_size, 'pivot'),
        QuantumRegister(1, 'kickback'),
        QuantumRegister(1, 'comparator_z'),
        QuantumRegister(1, 'comparator_c'),
        name='Arithmetic K7'
    )
    
    hier_circuit.h(range(num_vertices))
    hier_circuit.barrier()
    
    oracle_circuit = QuantumCircuit(
        QuantumRegister(num_vertices),
        QuantumRegister(counter_size),
        QuantumRegister(counter_size),
        QuantumRegister(1),
        QuantumRegister(1),
        QuantumRegister(1),
        name='Oracle'
    )
    oracle_gate = oracle_circuit.to_gate(label='Oracle')
    hier_circuit.append(oracle_gate, list(range(num_vertices)) + list(range(num_vertices, num_vertices + counter_size * 2 + 3)))
    hier_circuit.barrier()
    
    hier_circuit.cx(num_vertices + 2 * counter_size + 1, num_vertices + 2 * counter_size)
    hier_circuit.barrier()
    
    diffuser_circuit = QuantumCircuit(num_vertices, name='Grover Diffuser')
    diffuser_gate = diffuser_circuit.to_gate(label='Grover\nDiffuser')
    hier_circuit.append(diffuser_gate, range(num_vertices))
    hier_circuit.barrier()
    
    return circuit, hier_circuit


def save_circuit_to_subdir(circuit, subdir, filename, fold=-1, dpi=300):
    """Save circuit to subdirectory

    Args:
        fold: Number of gates per row. -1 = no folding (single row, very wide
            for long circuits). Use a positive value to wrap the circuit into
            multiple rows, improving the aspect ratio for print.
        dpi: Output resolution. 300 is sufficient for print.
    """
    subdir_path = os.path.join(OUTPUT_DIR, subdir)
    os.makedirs(subdir_path, exist_ok=True)
    filepath = os.path.join(subdir_path, filename)

    fig = circuit.draw(
        output='mpl',
        fold=fold,
        idle_wires=False,
    )

    fig.savefig(filepath, dpi=dpi, bbox_inches='tight', facecolor='white', edgecolor='none')
    print(f"  Saved: {filepath}")
    return filepath


def create_dicke_k7_compact():
    """Create compact Dicke-state K7 circuit with grouped edge ancilla"""
    print("\n=== Creating Dicke-state K7 Compact Circuit ===")
    
    edges = [(i, j) for i in range(7) for j in range(i+1, 7)]
    num_vertices = 7
    m = len(edges)  # 21 edges
    
    hier_circuit = QuantumCircuit(
        QuantumRegister(num_vertices, 'vertex'),
        QuantumRegister(1, f'edge_ancilla ({m})'),
        QuantumRegister(1, 'kickback'),
        QuantumRegister(1, 'all_feasible'),
        name='Dicke-state K7 Compact'
    )
    
    k = 6  # pivot_number - 1 = 7 - 1 = 6
    gdsp_circuit = create_generalized_dicke_state(num_vertices, k)
    gdsp_gate = gdsp_circuit.to_gate(label='GDSP')
    hier_circuit.append(gdsp_gate, range(7))
    hier_circuit.barrier()
    
    oracle_circuit = QuantumCircuit(
        QuantumRegister(num_vertices),
        QuantumRegister(1),
        QuantumRegister(1),
        QuantumRegister(1),
        name='Oracle'
    )
    oracle_gate = oracle_circuit.to_gate(label='Oracle')
    hier_circuit.append(oracle_gate, list(range(num_vertices + 1 + 2)))
    hier_circuit.barrier()
    
    hier_circuit.cx(num_vertices + 1, num_vertices + 1 + 1)
    hier_circuit.barrier()
    
    diffuser_circuit = QuantumCircuit(num_vertices, name='GDS Diffuser')
    diffuser_gate = diffuser_circuit.to_gate(label='GDS\nDiffuser')
    hier_circuit.append(diffuser_gate, range(7))
    hier_circuit.barrier()
    
    return hier_circuit


def create_arithmetic_k7_compact():
    """Create compact Arithmetic K7 circuit with grouped counter/pivot"""
    print("\n=== Creating Arithmetic K7 Compact Circuit ===")
    
    num_vertices = 7
    num_edges = 21  # K7 has 21 edges
    penalty = num_vertices + 1  # default penalty
    counter_size = (num_vertices + penalty * num_edges).bit_length()  # 8 for K7
    
    hier_circuit = QuantumCircuit(
        QuantumRegister(num_vertices, 'vertex'),
        QuantumRegister(1, f'counter ({counter_size})'),
        QuantumRegister(1, f'pivot ({counter_size})'),
        QuantumRegister(1, 'kickback'),
        QuantumRegister(1, 'comparator_z'),
        QuantumRegister(1, 'comparator_c'),
        name='Arithmetic K7 Compact'
    )
    
    hier_circuit.h(range(num_vertices))
    hier_circuit.barrier()
    
    oracle_circuit = QuantumCircuit(
        QuantumRegister(num_vertices),
        QuantumRegister(1),
        QuantumRegister(1),
        QuantumRegister(1),
        QuantumRegister(1),
        QuantumRegister(1),
        name='Oracle'
    )
    oracle_gate = oracle_circuit.to_gate(label='Oracle')
    hier_circuit.append(oracle_gate, list(range(7)) + list(range(7, 12)))
    hier_circuit.barrier()
    
    hier_circuit.cx(9, 8)
    hier_circuit.barrier()
    
    diffuser_circuit = QuantumCircuit(num_vertices, name='Grover Diffuser')
    diffuser_gate = diffuser_circuit.to_gate(label='Grover\nDiffuser')
    hier_circuit.append(diffuser_gate, range(num_vertices))
    hier_circuit.barrier()
    
    return hier_circuit


def main():
    """Generate all hierarchical circuit diagrams"""
    print("=" * 60)
    print("Hierarchical Circuit Diagram Generator for MVC Paper")
    print("=" * 60)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # ========== Dicke-state ==========
    print("\n[1/3] Processing Dicke-state architecture...")
    
    # K3 circuits
    print("\n--- K3 Circuits ---")
    dicke_full, dicke_hier = create_dicke_hierarchical()
    save_circuit_to_subdir(dicke_full, 'dicke_state', 'k3_full.png', fold=40)
    save_circuit_to_subdir(dicke_hier, 'dicke_state', 'k3_main.png')
    
    dicke_oracle = create_dicke_oracle_detail()
    save_circuit_to_subdir(dicke_oracle, 'dicke_state', 'k3_oracle_detail.png')
    
    dicke_edge_check = create_dicke_edge_check_detail()
    save_circuit_to_subdir(dicke_edge_check, 'dicke_state', 'k3_edge_check_detail.png')
    
    # K7 circuits (compact for display)
    print("\n--- K7 Circuits (Compact) ---")
    dicke_k7_compact = create_dicke_k7_compact()
    save_circuit_to_subdir(dicke_k7_compact, 'dicke_state', 'k7_main.png', fold=30)
    
    # ========== Arithmetic ==========
    print("\n[2/3] Processing Arithmetic architecture...")
    
    # K3 circuits
    print("\n--- K3 Circuits ---")
    arith_full, arith_hier = create_arithmetic_hierarchical()
    save_circuit_to_subdir(arith_full, 'arithmetic', 'k3_full.png', fold=75)
    save_circuit_to_subdir(arith_hier, 'arithmetic', 'k3_main.png')
    
    arith_oracle = create_arithmetic_oracle_detail()
    save_circuit_to_subdir(arith_oracle, 'arithmetic', 'k3_oracle_detail.png')
    
    arith_popcount = create_popcount_detail()
    save_circuit_to_subdir(arith_popcount, 'arithmetic', 'k3_popcount_detail.png')
    
    arith_penalty = create_penalty_detail()
    save_circuit_to_subdir(arith_penalty, 'arithmetic', 'k3_penalty_detail.png')
    
    # K7 circuits (compact for display)
    print("\n--- K7 Circuits (Compact) ---")
    arith_k7_compact = create_arithmetic_k7_compact()
    save_circuit_to_subdir(arith_k7_compact, 'arithmetic', 'k7_main.png', fold=30)
    
    # ========== Weighted ==========
    print("\n[3/3] Processing Weighted architecture...")
    
    # K3 circuits
    print("\n--- K3 Circuits ---")
    weighted_full, weighted_hier = create_weighted_hierarchical()
    save_circuit_to_subdir(weighted_full, 'weighted', 'k3_full.png', fold=100)
    save_circuit_to_subdir(weighted_hier, 'weighted', 'k3_main.png')
    
    weighted_oracle = create_weighted_oracle_detail()
    save_circuit_to_subdir(weighted_oracle, 'weighted', 'k3_oracle_detail.png')
    
    weighted_popcount = create_weighted_popcount_detail()
    save_circuit_to_subdir(weighted_popcount, 'weighted', 'k3_popcount_detail.png')
    
    weighted_penalty = create_penalty_detail()
    save_circuit_to_subdir(weighted_penalty, 'weighted', 'k3_penalty_detail.png')
    
    print("\n" + "=" * 60)
    print("Done! Generated files in:", OUTPUT_DIR)
    print("=" * 60)
    
    print("\nGenerated files:")
    for root, dirs, files in os.walk(OUTPUT_DIR):
        for f in sorted(files):
            if f.endswith('.png'):
                rel_path = os.path.relpath(os.path.join(root, f), OUTPUT_DIR)
                print(f"  - {rel_path}")


if __name__ == '__main__':
    main()