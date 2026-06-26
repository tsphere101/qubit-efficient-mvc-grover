#!/usr/bin/env python3
"""
Compute success probability values for the Arithmetic MVC architecture
at pivot k = n (the threshold that marks the n MVCs of K_n).

Uses the analytical Boyer 1998 formula (no circuit run):
  P_k = sin^2((2k+1) * theta)   where   sin(theta) = sqrt(M / N)
  M = n        (the n MVCs of K_n)
  N = 2^n      (search space)
  k = iterations

Tables covered (referenced by LaTeX label, not by section number):
  - tab:success-prob    (per-iteration success probability, K_3..K_7)
  - tab:grover-vs-qaoa  (optimal Grover success probability + optimal iters)
"""
import json
import math
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO / "experiments" / "manifests" / "table_5_4_5_5_regen.json"

NS = [3, 4, 5, 6, 7]
ITERATIONS = [1, 2, 3]


def boyer_p_success(n: int, iterations: int) -> float:
    """Boyer 1998: P_k = sin^2((2k+1) * theta) where sin(theta) = sqrt(M/N)."""
    M = n
    N = 2 ** n
    sin_theta = math.sqrt(M / N)
    theta = math.asin(sin_theta)
    return math.sin((2 * iterations + 1) * theta) ** 2


def analytical_optimal_iter(n: int) -> int:
    """Boyer 1998: floor(pi/4 * sqrt(N/M))."""
    return int(math.floor(math.pi / 4 * math.sqrt(2 ** n / n)))


def empirical_optimal_iter(n: int) -> tuple[int, float]:
    """Pick the iter in {1, 2, 3} that gives the highest P_success."""
    ps = {it: boyer_p_success(n, it) for it in ITERATIONS}
    best = max(ps, key=ps.get)
    return best, ps[best]


def main():
    table_5_4_rows = {}
    table_5_5_rows = {}

    for n in NS:
        M, N = n, 2 ** n
        print(f"\n=== K_{n} (M={M}, N={N}, sin(theta)=sqrt({M}/{N})={math.sqrt(M/N):.4f}) ===", flush=True)
        per_iter = {it: boyer_p_success(n, it) for it in ITERATIONS}
        for it, p in per_iter.items():
            print(f"  iter={it}: P_success = {p:.4f}", flush=True)

        best_iter, best_p = empirical_optimal_iter(n)
        analytical = analytical_optimal_iter(n)
        print(f"  optimal (empirical across 1..3): iter={best_iter}, P={best_p:.4f}", flush=True)
        print(f"  optimal (Boyer 1998 formula):    iter={analytical}", flush=True)

        table_5_4_rows[f"K_{n}"] = {
            "n": n,
            "pivot": n,
            "p_success": {str(it): per_iter[it] for it in ITERATIONS},
        }
        table_5_5_rows[f"K_{n}"] = {
            "n": n,
            "pivot": n,
            "p_optimal": best_p,
            "optimal_iter_empirical": best_iter,
            "optimal_iter_analytical_boyer1998": analytical,
        }

    manifest = {
        "manifest_version": "1.0",
        "thesis_labels": {
            "tab:success-prob": {
                "caption": "Success probability for the Arithmetic approach on complete graphs K_n",
                "rows": table_5_4_rows,
            },
            "tab:grover-vs-qaoa": {
                "caption": "Success probability comparison: Grover (Arithmetic) versus QAOA (p=1)",
                "note": "QAOA column comes from mvc_qaoa (separate regen), not this script. Grover (optimal) and Optimal iterations are from the Boyer 1998 analytical formula.",
                "rows": table_5_5_rows,
            },
        },
        "method": "Boyer 1998 analytical formula",
        "formula": "P_k = sin^2((2k+1)*theta) where sin(theta) = sqrt(M/N), M = n, N = 2^n",
        "pivot_convention": "k = n (verified: counter < n iff valid cover of size n-1)",
    }

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))
    print(f"\nManifest written to {MANIFEST_PATH}")

    print("\n=== LaTeX rows for tab:success-prob (6-results.tex:127-131) ===")
    for n in NS:
        d = table_5_4_rows[f"K_{n}"]["p_success"]
        print(f"\\(K_{n}\\) & {n} & {d['1']:.3f} & {d['2']:.3f} & {d['3']:.3f} \\\\")

    print("\n=== LaTeX rows for tab:grover-vs-qaoa (Grover optimal + optimal iters only) ===")
    for n in NS:
        d = table_5_5_rows[f"K_{n}"]
        print(f"\\(K_{n}\\) & {n} & {d['p_optimal']:.3f} & (QAOA TBD) & {d['optimal_iter_empirical']} \\\\")


if __name__ == "__main__":
    main()
