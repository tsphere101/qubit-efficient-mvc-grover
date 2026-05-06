"""Graph definitions for the MVC QAOA benchmark suite."""

from typing import List, Tuple, Dict

GraphDef = Dict[str, any]


def clique(n: int) -> List[Tuple[int, int]]:
    """Return edges of a complete graph K_n."""
    return [(i, j) for i in range(n) for j in range(i + 1, n)]


def cycle(n: int) -> List[Tuple[int, int]]:
    """Return edges of a cycle graph C_n."""
    return [(i, (i + 1) % n) for i in range(n)]


def star(n: int) -> List[Tuple[int, int]]:
    """Return edges of a star graph S_n (0 is the center)."""
    return [(0, i) for i in range(1, n)]


def path(n: int) -> List[Tuple[int, int]]:
    """Return edges of a path graph P_n."""
    return [(i, i + 1) for i in range(n - 1)]


# All benchmark graphs
BENCHMARK_GRAPHS: List[GraphDef] = [
    # Cliques (dense)
    {"name": "K3", "n": 3, "edges": clique(3)},
    {"name": "K4", "n": 4, "edges": clique(4)},
    {"name": "K5", "n": 5, "edges": clique(5)},
    {"name": "K6", "n": 6, "edges": clique(6)},
    {"name": "K7", "n": 7, "edges": clique(7)},

    # Cycles (regular, sparse)
    {"name": "C4", "n": 4, "edges": cycle(4)},
    {"name": "C5", "n": 5, "edges": cycle(5)},
    {"name": "C6", "n": 6, "edges": cycle(6)},

    # Stars (hub-and-spoke)
    {"name": "S4", "n": 4, "edges": star(4)},
    {"name": "S5", "n": 5, "edges": star(5)},

    # Paths (linear)
    {"name": "P4", "n": 4, "edges": path(4)},
    {"name": "P5", "n": 5, "edges": path(5)},

    # Mixed / custom
    {"name": "Diamond", "n": 4, "edges": [(0, 1), (0, 2), (1, 2), (1, 3)]},
    {"name": "Bowtie", "n": 5, "edges": [(0, 1), (0, 2), (1, 2), (1, 3), (2, 4), (3, 4)]},
    {"name": "Tent", "n": 5, "edges": [(0, 1), (0, 2), (1, 2), (2, 3), (2, 4), (3, 4)]},
]
