"""Exact brute-force solver for small MVC instances."""

from typing import List, Tuple, Dict
import numpy as np
from qubo import qubo_cost, is_valid_cover, cover_size


def solve_exact(n: int, edges: List[Tuple[int, int]], Q: np.ndarray) -> Dict:
    """Brute-force enumerate all 2^n bitstrings and find optimal covers.

    Returns:
        Dict with optimal_cost, optimal_size, optimal_covers, and all_results.
    """
    all_results = []
    for b in range(2 ** n):
        bs = format(b, f"0{n}b")[::-1]  # little-endian
        cost = qubo_cost(bs, Q)
        valid = is_valid_cover(bs, edges)
        size = cover_size(bs)
        all_results.append({
            "bitstring": bs,
            "cost": float(cost),
            "valid": valid,
            "size": size
        })

    # Sort by cost ascending, then by size ascending
    all_results.sort(key=lambda r: (r["cost"], r["size"]))

    # Find optimal valid covers
    valid_results = [r for r in all_results if r["valid"]]
    if not valid_results:
        raise ValueError("No valid cover found — graph may be empty.")

    optimal_cost = valid_results[0]["cost"]
    optimal_size = valid_results[0]["size"]
    optimal_covers = [r["bitstring"] for r in valid_results if r["cost"] == optimal_cost]

    return {
        "optimal_cost": float(optimal_cost),
        "optimal_size": int(optimal_size),
        "optimal_covers": optimal_covers,
        "num_valid_covers": len(valid_results),
        "all_results": all_results[:16]  # top 16 for brevity
    }
