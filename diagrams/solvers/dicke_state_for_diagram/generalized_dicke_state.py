import math
from qiskit import QuantumCircuit
from qiskit.circuit.library import RYGate
from qiskit.quantum_info import Statevector

def create_generalized_dicke_state(n: int, k: int) -> QuantumCircuit:
    """
    Creates a quantum circuit that prepares the generalized Dicke state 
    for Hamming weights <= K using Algorithm 2 from Narisada et al. (2023).
    DOI:10.5220/0011618000003405
    
    Args:
        n (int): Total number of qubits.
        k (int): Maximum Hamming weight (K).
        
    Returns:
        QuantumCircuit: The synthesized Qiskit circuit preparing |D_{<=k}^n>.
    """
    qc = QuantumCircuit(n)
    
    if k == 0:
        return qc  # |00...0> is already the <= 0 Dicke state
    if k > n:
        raise ValueError("k cannot be greater than n")

    # ==========================================
    # Step 1: Input Superposition Preparation
    # ==========================================
    # Calculate alphas: the ideal probability amplitudes for each weight
    total_states = sum(math.comb(n, i) for i in range(k + 1))
    alphas = [math.sqrt(math.comb(n, i) / total_states) for i in range(k + 1)]
    
    # Calculate betas for the RY and CRY rotation angles
    betas = []
    sum_alpha_sq = 0.0
    for i in range(k + 1):
        if 1.0 - sum_alpha_sq <= 1e-12:  # Avoid float precision domain errors
            betas.append(1.0)
        else:
            betas.append(math.sqrt(alphas[i]**2 / (1.0 - sum_alpha_sq)))
        sum_alpha_sq += alphas[i]**2

    # Line 1: Apply initial RY to the highest indexed qubit
    qc.ry(2 * math.acos(betas[0]), n - 1)
    
    # Lines 2-3: Apply chained CRY gates
    for i in range(1, k):
        # 0-based indexing equivalent of n-i+1 controlling n-i
        qc.cry(2 * math.acos(betas[i]), n - i, n - i - 1)
        
    # ==========================================
    # Step 2: Concat Un,k Gate Construction
    # ==========================================
    # U_{n,k} shifts the localized 1s to form the uniform Dicke combinations
    q_idx = list(range(n))
    
    def apply_B(i_val, j_val, active_qubits):
        """Applies the B_{i,j} partial swap / rotation block."""
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
        """Applies the S_{i,l} shift block composed of B blocks."""
        for j_val in range(1, l_val + 1):
            # B_{i,j} acts on the last j+1 qubits of the span
            apply_B(i_val, j_val, span_qubits[-(j_val + 1):])

    # Multiply from right to left (Algorithm 2's Un,k expansion rule)
    # 1. Apply second product: i from n down to k+1
    for i in range(n, k, -1):
        span = q_idx[i - k - 1 : i]
        apply_S(i, k, span)
        
    # 2. Apply first product: i from k down to 2
    for i in range(k, 1, -1):
        span = q_idx[0 : i]
        apply_S(i, i - 1, span)
        
    return qc

# Example Usage:
if __name__ == "__main__":
    n_qubits = 3
    max_weight = 2
    circuit = create_generalized_dicke_state(n=n_qubits, k=max_weight)
    print(circuit.draw(output='text'))
    sv = Statevector.from_instruction(circuit)
    print(f'probabilities in percentage')
    for i in range(2**n_qubits):
        print(f' |  {i:0{n_qubits}b}>: {round(abs(sv[i])**2*100, 4)}%')
