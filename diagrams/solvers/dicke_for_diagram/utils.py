import math
from typing import List, Tuple
from itertools import combinations
from qiskit import QuantumCircuit
from qiskit.circuit.library import RYGate

def is_valid_cover(state_str: str, edges: List[Tuple[int, int]], num_vertices: int) -> bool:
    # Logic preserved: Qiskit little-endian (rightmost is qubit 0)
    state = [int(b) for b in reversed(state_str.zfill(num_vertices))]
    for u, v in edges:
        if u < len(state) and v < len(state):
            if state[u] == 0 and state[v] == 0:
                return False
    return True

def get_popcount(state_str: str) -> int:
    return sum(int(b) for b in state_str)

def complete_graph_edges(n: int) -> List[Tuple[int, int]]:
    return list(combinations(range(n), 2))

def create_generalized_dicke_state(n: int, k: int) -> QuantumCircuit:
    """
    Creates a quantum circuit that prepares the generalized Dicke state 
    for Hamming weights <= K using Algorithm 2 from Narisada et al. (2023).
    DOI:10.5220/0011618000003405
    """
    qc = QuantumCircuit(n)
    
    if k == 0:
        return qc  # |00...0> is already the <= 0 Dicke state
    if k > n:
        raise ValueError("k cannot be greater than n")

    # ==========================================
    # Step 1: Input Superposition Preparation
    # ==========================================
    total_states = sum(math.comb(n, i) for i in range(k + 1))
    alphas = [math.sqrt(math.comb(n, i) / total_states) for i in range(k + 1)]
    
    betas = []
    sum_alpha_sq = 0.0
    for i in range(k + 1):
        if 1.0 - sum_alpha_sq <= 1e-12:
            betas.append(1.0)
        else:
            betas.append(math.sqrt(alphas[i]**2 / (1.0 - sum_alpha_sq)))
        sum_alpha_sq += alphas[i]**2

    qc.ry(2 * math.acos(betas[0]), n - 1)
    for i in range(1, k):
        qc.cry(2 * math.acos(betas[i]), n - i, n - i - 1)
        
    # ==========================================
    # Step 2: Concat Un,k Gate Construction
    # ==========================================
    q_idx = list(range(n))
    
    def apply_B(i_val, j_val, active_qubits):
        A = active_qubits[0]
        B_target = active_qubits[-1]
        C = active_qubits[1:-1]
        theta = math.acos(math.sqrt(j_val / i_val))
        
        if len(C) == 0:
            qc.cx(B_target, A)
            qc.cry(2 * theta, A, B_target)
            qc.cx(B_target, A)
        else:
            qc.mcx(C + [B_target], A)
            mcry = RYGate(2 * theta).control(len(C) + 1, annotated=True)
            qc.append(mcry, C + [A, B_target])
            qc.mcx(C + [B_target], A)

    def apply_S(i_val, l_val, span_qubits):
        for j_val in range(1, l_val + 1):
            apply_B(i_val, j_val, span_qubits[-(j_val + 1):])

    for i in range(n, k, -1):
        span = q_idx[i - k - 1 : i]
        apply_S(i, k, span)
        
    for i in range(k, 1, -1):
        span = q_idx[0 : i]
        apply_S(i, i - 1, span)
        
    return qc