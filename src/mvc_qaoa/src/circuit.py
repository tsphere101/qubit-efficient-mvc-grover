"""QAOA circuit builder for arbitrary Ising Hamiltonians."""

from typing import Dict, List, Tuple
from qiskit import QuantumCircuit


def build_qaoa_circuit(
    terms: Dict[Tuple[int, ...], float],
    gammas: List[float],
    betas: List[float],
    num_qubits: int
) -> QuantumCircuit:
    """Construct a p-layer QAOA circuit from Ising Pauli-Z terms.

    Args:
        terms: Maps qubit tuples to coefficients (single or two-qubit).
        gammas: Problem angles [gamma_1, ..., gamma_p].
        betas: Mixer angles [beta_1, ..., beta_p].
        num_qubits: Number of qubits.

    Returns:
        QuantumCircuit with measurements appended.
    """
    assert len(gammas) == len(betas), "gammas and betas must have same length"
    p = len(gammas)

    qc = QuantumCircuit(num_qubits, num_qubits)
    qc.h(range(num_qubits))

    for layer in range(p):
        gamma = gammas[layer]
        beta = betas[layer]

        # Problem unitary U(H_P, gamma)
        for qubits, coeff in terms.items():
            angle = 2.0 * coeff * gamma
            if len(qubits) == 1:
                qc.rz(angle, qubits[0])
            elif len(qubits) == 2:
                i, j = qubits
                qc.cx(i, j)
                qc.rz(angle, j)
                qc.cx(i, j)
            else:
                raise NotImplementedError("Only Z and ZZ terms supported.")

        # Mixer unitary U(H_M, beta)
        qc.rx(2.0 * beta, range(num_qubits))

    qc.measure(range(num_qubits), range(num_qubits))
    return qc
