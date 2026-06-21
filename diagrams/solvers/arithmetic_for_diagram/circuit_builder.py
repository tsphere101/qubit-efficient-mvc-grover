import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister

from .models import SolverConfig

class VertexCoverPenaltyCircuitBuilder:
    def __init__(self, config: SolverConfig):
        self.config = config
    def _barrier(self, circuit):
        if self.config.barrier:
            circuit.barrier()

    def _increment(self, circuit, target_reg, control_qubits=None, inverse=False):
        controls = list(control_qubits) if control_qubits else []
        
        n = len(target_reg)
        range_iter = range(n - 1, -1, -1)
        
        if inverse:
            range_iter = range(n)
            
        for i in range_iter:
            current_controls = controls + [target_reg[j] for j in range(i)]
            
            if len(current_controls) == 0:
                circuit.x(target_reg[i])
            elif len(current_controls) == 1:
                circuit.cx(current_controls[0], target_reg[i])
            else:
                circuit.mcx(current_controls, target_reg[i])


    def build(self) -> QuantumCircuit:
        (circuit, search_space_reg, binary_counter_reg, pivot_reg, kick_back_reg,
         comparator_c_reg, comparator_z_reg, c_register) = self._create_registers()

        self._initialize(circuit, pivot_reg, kick_back_reg, search_space_reg)

        for _ in range(self.config.grover_iterations):
            # 1. Compute state in counter register
            self._pop_count(circuit, search_space_reg, binary_counter_reg)
            self._barrier(circuit)

            self._apply_x_to_vertices_register(circuit, search_space_reg)
            self._edge_coverage_penalty_adder(circuit, search_space_reg, binary_counter_reg)
            self._barrier(circuit)
            self._apply_x_to_vertices_register(circuit, search_space_reg)

            # 2. Compare the counter with the pivot
            self._apply_cuccaro_comparator(circuit, pivot_reg, binary_counter_reg, comparator_z_reg, comparator_c_reg)
            self._barrier(circuit)

            # 3. Apply the phase kickback
            circuit.cx(comparator_z_reg[0], kick_back_reg[0])
            self._barrier(circuit)

            # 4. Uncompute Comparator
            self._apply_cuccaro_comparator(circuit, pivot_reg, binary_counter_reg, comparator_z_reg, comparator_c_reg)
            self._barrier(circuit)

            # 5. Uncompute Counter
            self._apply_x_to_vertices_register(circuit, search_space_reg)
            self._edge_coverage_penalty_adder(circuit, search_space_reg, binary_counter_reg, reverse=True)
            self._apply_x_to_vertices_register(circuit, search_space_reg)
            self._pop_count(circuit, search_space_reg, binary_counter_reg, inverse=True)
            self._barrier(circuit)

            # 6. Diffuse
            self._apply_diffuser(circuit, search_space_reg)

        circuit.measure(search_space_reg, circuit.clbits)
        return circuit

    def _create_registers(self):
        search_space_reg = QuantumRegister(self.config.num_vertices, 'search_space')
        binary_counter_reg = QuantumRegister(self.config.counter_size, 'counter')
        pivot_reg = QuantumRegister(self.config.counter_size, 'pivot')
        kick_back_reg = QuantumRegister(self.config.phase_kickback_bits, 'kickback')
        comparator_z_reg = QuantumRegister(1, 'comparator_z')
        comparator_c_reg = QuantumRegister(1, 'comparator_c')
        c_register = ClassicalRegister(self.config.num_vertices, self.config.classical_register_name)

        circuit = QuantumCircuit(search_space_reg, binary_counter_reg, pivot_reg, kick_back_reg,
                                    comparator_c_reg, comparator_z_reg, c_register)
        return (circuit, search_space_reg, binary_counter_reg, pivot_reg, kick_back_reg,
                comparator_c_reg, comparator_z_reg, c_register)

    def _initialize(self, circuit, pivot_reg, kick_back_reg, search_space_reg):
        for i in range(pivot_reg.size):
            if (self.config.pivot_number >> i) & 1:
                circuit.x(pivot_reg[i])
        circuit.x(kick_back_reg); circuit.h(kick_back_reg); circuit.h(search_space_reg); self._barrier(circuit)

    def _feasibility_check(self, circuit, search_space_reg, edge_check_reg, reverse=False):
        edges_enum = enumerate(self.config.edges) if not reverse else reversed(list(enumerate(self.config.edges)))
        for index, (u, v) in edges_enum:
            if not reverse:
                circuit.mcx([search_space_reg[u], search_space_reg[v]], edge_check_reg[index])
                circuit.x(edge_check_reg[index])
            else:
                circuit.x(edge_check_reg[index])
                circuit.mcx([search_space_reg[u], search_space_reg[v]], edge_check_reg[index])
            self._barrier(circuit)
    def _edge_coverage_penalty_adder(self, circuit, search_space_reg, binary_counter_register, reverse=False):
        edges_enum = enumerate(self.config.edges) if not reverse else reversed(list(enumerate(self.config.edges)))
        penalty_amount = self.config.penalty_amount
        
        # Decompose penalty_amount into bits
        penalty_bits = []
        temp_val = penalty_amount
        bit_idx = 0
        while temp_val > 0:
            if temp_val & 1:
                penalty_bits.append(bit_idx)
            temp_val >>= 1
            bit_idx += 1
            
        for index, (u, v) in edges_enum:
             controls = [search_space_reg[u], search_space_reg[v]]
             
             p_bits_iter = penalty_bits if not reverse else reversed(penalty_bits)
             
             for p_bit in p_bits_iter:
                 if p_bit < binary_counter_register.size:
                     target_qubits = [binary_counter_register[i] for i in range(p_bit, binary_counter_register.size)]
                     
                     self._increment(circuit, target_qubits, control_qubits=controls, inverse=reverse)
                     self._barrier(circuit)

        return circuit


    def _mark_feasible(self, circuit, search_space_reg, edge_check_reg, all_feasible):
        circuit.x(search_space_reg)
        self._feasibility_check(circuit, search_space_reg, edge_check_reg, reverse=False)
        circuit.mcx(edge_check_reg, all_feasible)
        self._feasibility_check(circuit, search_space_reg, edge_check_reg, reverse=True)
        circuit.x(search_space_reg); self._barrier(circuit)

    def _pop_count(self, circuit, bits_reg, count_reg, inverse=False):
        iter_bits = range(bits_reg.size) if not inverse else range(bits_reg.size - 1, -1, -1)
        
        for k in iter_bits:
            self._increment(circuit, count_reg, control_qubits=[bits_reg[k]], inverse=inverse)
            self._barrier(circuit)



    def _apply_cuccaro_comparator(self, circuit, reg_a, reg_b, reg_z, reg_c):
        def _maj(qc, a, b, c): qc.cx(a, c); qc.cx(a, b); qc.ccx(b, c, a)
        def _imaj(qc, a, b, c): qc.ccx(b, c, a); qc.cx(a, b); qc.cx(a, c)
        circuit.x(reg_b); self._barrier(circuit)
        _maj(circuit, reg_a[0], reg_b[0], reg_c[0])
        for i in range(1, reg_a.size): _maj(circuit, reg_a[i], reg_b[i], reg_a[i-1])
        self._barrier(circuit); circuit.cx(reg_a[-1], reg_z[0]); self._barrier(circuit)
        for i in range(reg_a.size - 1, 0, -1): _imaj(circuit, reg_a[i], reg_b[i], reg_a[i-1])
        _imaj(circuit, reg_a[0], reg_b[0], reg_c[0])
        self._barrier(circuit); circuit.x(reg_b); self._barrier(circuit)

    def _apply_diffuser(self, circuit, search_space_reg):
        circuit.h(search_space_reg); circuit.x(search_space_reg)
        circuit.mcp(np.pi, search_space_reg[:-1], search_space_reg[-1])
        circuit.x(search_space_reg); circuit.h(search_space_reg); self._barrier(circuit)
        
    def _apply_x_to_vertices_register(self, circuit, vertices_reg):
        circuit.x(vertices_reg); self._barrier(circuit)