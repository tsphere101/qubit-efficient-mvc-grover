"""Quantum simulation and result analysis."""

from typing import Dict, List, Tuple
import numpy as np
from qiskit_aer import AerSimulator
from qubo import qubo_cost, is_valid_cover, cover_size


def simulate_and_analyse(
    circuit,
    Q: np.ndarray,
    edges: List[Tuple[int, int]],
    shots: int = 4096
) -> Dict:
    """Run circuit on AerSimulator and compute comprehensive metrics.

    Returns:
        Dict with counts, top_results, metrics, and raw data.
    """
    simulator = AerSimulator()
    counts = simulator.run(circuit, shots=shots).result().get_counts()

    # Build detailed results for every observed state
    results = []
    for bs, cnt in counts.items():
        cost = qubo_cost(bs, Q)
        valid = is_valid_cover(bs, edges)
        size = cover_size(bs)
        results.append({
            "bitstring": bs,
            "count": int(cnt),
            "probability": round(cnt / shots, 6),
            "cost": float(cost),
            "valid": valid,
            "size": size
        })

    results.sort(key=lambda r: (-r["probability"], r["cost"], r["size"]))

    # Compute expected cost
    expected_cost = sum(r["cost"] * r["probability"] for r in results)

    # Valid-state probability
    valid_prob = sum(r["probability"] for r in results if r["valid"])

    # Best result among valid states
    valid_results = [r for r in results if r["valid"]]
    best_valid = min(valid_results, key=lambda r: (r["cost"], r["size"])) if valid_results else None

    # Top-8 summary
    top_8 = results[:8]

    return {
        "shots": shots,
        "num_unique_states": len(results),
        "expected_cost": float(expected_cost),
        "valid_probability": float(valid_prob),
        "best_valid": best_valid,
        "top_8": top_8,
        "raw_counts": {k: int(v) for k, v in counts.items()}
    }
