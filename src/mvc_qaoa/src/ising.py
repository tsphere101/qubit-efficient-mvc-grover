"""QUBO to Ising (Pauli-Z) mapping."""

from typing import List, Tuple, Dict
import numpy as np


def qubo_to_ising(Q: np.ndarray) -> Tuple[Dict[Tuple[int, ...], float], float]:
    """Map a symmetric QUBO matrix to Pauli-Z coefficients.

    Substitute x_i = (1 - Z_i)/2, collect terms, drop global constant.

    Returns:
        (terms, constant) where terms maps qubit index tuples to coeffs.
    """
    n = Q.shape[0]
    terms: Dict[Tuple[int, ...], float] = {}
    constant = 0.0

    for i in range(n):
        # Diagonal Q_ii * x_i
        constant += Q[i, i] / 2.0
        terms[(i,)] = terms.get((i,), 0.0) - Q[i, i] / 2.0

        for j in range(i + 1, n):
            if abs(Q[i, j]) < 1e-12:
                continue
            constant += Q[i, j] / 4.0
            terms[(i,)] = terms.get((i,), 0.0) - Q[i, j] / 4.0
            terms[(j,)] = terms.get((j,), 0.0) - Q[i, j] / 4.0
            terms[(i, j)] = terms.get((i, j), 0.0) + Q[i, j] / 4.0

    return terms, constant


def ising_to_json(terms: Dict[Tuple[int, ...], float]) -> List[Dict]:
    """Serialize Ising terms to JSON-friendly list."""
    out = []
    for qubits, coeff in sorted(terms.items()):
        out.append({
            "qubits": list(qubits),
            "coefficient": float(coeff),
            "type": "ZZ" if len(qubits) == 2 else "Z"
        })
    return out
