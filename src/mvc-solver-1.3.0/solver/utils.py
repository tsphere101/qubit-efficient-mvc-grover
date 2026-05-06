from typing import List, Tuple
from itertools import combinations

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