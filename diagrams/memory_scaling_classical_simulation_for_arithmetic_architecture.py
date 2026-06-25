#!/usr/bin/env python3
"""
Memory requirements for classical statevector simulation of the
Arithmetic MVC architecture (Table 5.9 in the thesis).

Source of truth:
  - Qubit-count formula: mvc-solver-1.5.0/solver/circuit_builder.py:75-87
    qubits = n + 2 * counter_size + 3
  - counter_size: mvc-solver-1.5.0/solver/models.py:48-51
    counter_size = (sum(vertex_weights) + penalty_amount * num_edges).bit_length()
  - With default unit weights: penalty_amount = n + 1,
    counter_size = (n + (n + 1) * m).bit_length()
  - Statevector memory: 2^qubits * 16 bytes (complex128 = 2 * float64)
"""
from math import log2


def qubit_count(n: int) -> int:
    """Arithmetic-architecture qubit count for a complete graph K_n."""
    m = n * (n - 1) // 2
    penalty = n + 1
    counter_size = (n + penalty * m).bit_length()
    return n + 2 * counter_size + 3


def fmt(b: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{int(b):,} {unit}"
        b //= 1024
    return f"{int(b):,} TB"


NS = [3, 4, 5, 6, 7]

print("=== LaTeX rows for 6-results.tex (table body) ===")
for n in NS:
    q = qubit_count(n)
    sv = 2 ** q
    print(f"{n}  & {q} & {sv:,} & {fmt(sv * 16)} \\\\")

print()
print("=== Markdown preview ===")
print("| n | Qubits | Statevector | RAM |")
print("|---|---|---|---|")
for n in NS:
    q = qubit_count(n)
    sv = 2 ** q
    print(f"| {n} | {q} | {sv:,} | {fmt(sv * 16)} |")
