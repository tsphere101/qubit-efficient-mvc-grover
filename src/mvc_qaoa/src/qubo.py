"""MVC QUBO formulation for arbitrary undirected graphs."""

from typing import List, Tuple, Dict
import numpy as np


def build_mvc_qubo(n: int, edges: List[Tuple[int, int]], penalty: float = None) -> np.ndarray:
    """Build the exact QUBO matrix for Minimum Vertex Cover.

    C(x) = sum_i x_i + P * sum_{(i,j)} (1 - x_i)(1 - x_j)

    The penalty P must exceed the maximum degree for the formulation
    to be exact (no invalid cover beats a valid one).

    Args:
        n: Number of vertices.
        edges: List of undirected edges as (i, j) tuples.
        penalty: Penalty weight P.  If None, auto-set to max_degree + 1.

    Returns:
        Symmetric QUBO matrix Q.
    """
    degrees = [0] * n
    for i, j in edges:
        degrees[i] += 1
        degrees[j] += 1

    max_degree = max(degrees) if degrees else 0
    if penalty is None:
        penalty = float(max_degree + 1)

    Q = np.zeros((n, n))

    # Diagonal: 1 - P * degree(i)
    for i in range(n):
        Q[i, i] = 1.0 - penalty * degrees[i]

    # Off-diagonal: +P/2 for each edge (symmetric)
    for i, j in edges:
        Q[i, j] += penalty / 2.0
        Q[j, i] += penalty / 2.0

    return Q


def qubo_cost(bitstring: str, Q: np.ndarray) -> float:
    """Evaluate QUBO cost for a bitstring (Qiskit little-endian)."""
    x = np.array([int(b) for b in bitstring[::-1]], dtype=float)
    return float(x @ Q @ x)


def is_valid_cover(bitstring: str, edges: List[Tuple[int, int]]) -> bool:
    """Check whether a bitstring encodes a valid vertex cover."""
    x = [int(b) for b in bitstring[::-1]]
    return all(x[i] or x[j] for i, j in edges)


def cover_size(bitstring: str) -> int:
    """Count the number of 1s in the cover (little-endian)."""
    return sum(int(b) for b in bitstring[::-1])
