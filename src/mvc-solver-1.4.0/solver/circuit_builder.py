import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister

from .models import SolverConfig
from .utils import create_generalized_dicke_state

class VertexCoverPenaltyCircuitBuilder:
    def __init__(self, config: SolverConfig):
        self.config = config
        
    def _barrier(self, circuit):
        if self.config.barrier:
            circuit.barrier()

    def build(self) -> QuantumCircuit:
        (circuit, search_space_reg, edge_check_reg, kick_back_reg,
         all_feasible_reg, c_register) = self._create_registers()

        self._initialize(circuit, search_space_reg, kick_back_reg)

        for _ in range(self.config.grover_iterations):
            # 1. Oracle: Mark states that cover all edges
            self._edge_check_oracle(circuit, search_space_reg, edge_check_reg, all_feasible_reg)
            self._barrier(circuit)

            # 2. Apply Phase Kickback
            circuit.cx(all_feasible_reg[0], kick_back_reg[0])
            self._barrier(circuit)

            # 3. Uncompute Oracle
            self._edge_check_oracle(circuit, search_space_reg, edge_check_reg, all_feasible_reg, inverse=True)
            self._barrier(circuit)

            # 4. Diffuse (Dicke State Diffuser)
            self._apply_diffuser(circuit, search_space_reg)
            self._barrier(circuit)

        circuit.measure(search_space_reg, circuit.clbits)
        return circuit

    def _create_registers(self):
        search_space_reg = QuantumRegister(self.config.num_vertices, 'search_space')
        edge_check_reg = QuantumRegister(len(self.config.edges), 'edge_check')
        kick_back_reg = QuantumRegister(1, 'kickback')
        all_feasible_reg = QuantumRegister(1, 'all_feasible')
        c_register = ClassicalRegister(self.config.num_vertices, self.config.classical_register_name)

        circuit = QuantumCircuit(search_space_reg, edge_check_reg, kick_back_reg, all_feasible_reg, c_register)
        return (circuit, search_space_reg, edge_check_reg, kick_back_reg, all_feasible_reg, c_register)

    def _initialize(self, circuit, search_space_reg, kick_back_reg):
        # Prepare state |D_{<=k}^n>
        # We use pivot_number - 1 as k (max weight) to match the previous "pop_count < pivot" logic
        k = self.config.pivot_number - 1
        dicke_prep = create_generalized_dicke_state(self.config.num_vertices, k)
        circuit.append(dicke_prep.to_gate(label="GDS"), search_space_reg)
        
        # Prepare kickback qubit |- >
        circuit.x(kick_back_reg)
        circuit.h(kick_back_reg)
        self._barrier(circuit)

    def _edge_check_oracle(self, circuit, search_space_reg, edge_check_reg, all_feasible_reg, inverse=False):
        # An edge (u, v) is UNCOVERED if both search_space[u] and search_space[v] are 0.
        # We mark edge_check_reg[i] if edge i is UNCOVERED.
        
        edges_enum = enumerate(self.config.edges) if not inverse else reversed(list(enumerate(self.config.edges)))
        
        if not inverse:
            circuit.x(search_space_reg)
            # Step 1: Detect uncovered edges
            for i, (u, v) in edges_enum:
                circuit.mcx([search_space_reg[u], search_space_reg[v]], edge_check_reg[i])
            
            self._barrier(circuit)
            circuit.x(search_space_reg)
            self._barrier(circuit)
            
            # Step 2: Mark all_feasible if NO edges are uncovered
            # (i.e., all edge_check bits are 0)
            circuit.x(edge_check_reg)
            circuit.mcx(edge_check_reg, all_feasible_reg[0])
            circuit.x(edge_check_reg)
            
        else:
            # Uncompute Step 2
            circuit.x(edge_check_reg)
            circuit.mcx(edge_check_reg, all_feasible_reg[0])
            circuit.x(edge_check_reg)
            
            self._barrier(circuit)
            circuit.x(search_space_reg)
            # Uncompute Step 1
            for i, (u, v) in edges_enum:
                circuit.mcx([search_space_reg[u], search_space_reg[v]], edge_check_reg[i])
            self._barrier(circuit)
            circuit.x(search_space_reg)

    def _apply_diffuser(self, circuit, search_space_reg):
        n = self.config.num_vertices
        k = self.config.pivot_number - 1
        
        # S_D = GDS * (2|0><0| - I) * GDS^dagger
        # Note: Phase kickback is already handled by the oracle.
        # Here we need to implement the reflection around |D>
        
        dicke_prep = create_generalized_dicke_state(n, k)
        dicke_prep_inv = dicke_prep.inverse()
        
        # 1. GDS^dagger
        circuit.append(dicke_prep_inv.to_gate(label="GDS_inv"), search_space_reg)
        
        # 2. Reflection around |0>
        circuit.x(search_space_reg)
        circuit.h(search_space_reg[-1])
        if n > 1:
            circuit.mcx(search_space_reg[:-1], search_space_reg[-1])
        else:
            circuit.x(search_space_reg[0]) # Single qubit case
        circuit.h(search_space_reg[-1])
        circuit.x(search_space_reg)
        
        # 3. GDS
        circuit.append(dicke_prep.to_gate(label="GDS"), search_space_reg)