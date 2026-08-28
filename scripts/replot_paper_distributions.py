#!/usr/bin/env python3

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from qiskit.visualization import plot_histogram

QUANTUM_RESEARCH = Path.home() / "Desktop/quantum-research/src"
MVCSOLVER = Path.home() / "Desktop/qubit-efficient-mvc-grover/src"

JOBS = [
    (QUANTUM_RESEARCH / "mvc-solver-1.4.0/outputs/run_20260222_165935_K3_K6/K_5/pivot_5",
     "distribution_K5_pivot5_dicke_01.png"),
    (QUANTUM_RESEARCH / "mvc-solver-1.3.0/outputs/run_20260303_142020/K_5/pivot_5",
     "distribution_K5_pivot5_arith_01.png"),
    (QUANTUM_RESEARCH / "mvc-solver-1.4.0/outputs/run_20260222_165935_K3_K6/K_6/pivot_6",
     "distribution_K6_pivot6_dicke_01.png"),
    (QUANTUM_RESEARCH / "mvc-solver-1.3.0/outputs/run_20260303_142020/K_6/pivot_6",
     "distribution_K6_pivot6_arith_01.png"),
    (QUANTUM_RESEARCH / "mvc-solver-1.4.0/outputs/run_20260303_142341_C5/graph/pivot_4",
     "distribution_cycle_C5_dicke_01.png"),
    (QUANTUM_RESEARCH / "mvc-solver-1.3.0/outputs/run_20260324_000911/graph/pivot_4",
     "distribution_cycle_C5_arith_01.png"),
    (QUANTUM_RESEARCH / "mvc-solver-1.4.0/outputs/run_20260303_142350_C6/graph/pivot_4",
     "distribution_cycle_C6_dicke_01.png"),
    (QUANTUM_RESEARCH / "mvc-solver-1.3.0/outputs/run_20260324_000933/graph/pivot_4",
     "distribution_cycle_C6_arith_01.png"),
    (QUANTUM_RESEARCH / "mvc-solver-1.3.0/outputs/run_20260303_142020/K_7/pivot_7",
     "distribution_K7_pivot7_arith_01.png"),
    (MVCSOLVER / "mvc-solver-1.5.0/outputs/run_20260303_142831/graph/pivot_4",
     "distribution_weighted_K3_123_01.png"),
    (MVCSOLVER / "mvc-solver-1.5.0/outputs/run_20260303_142855/graph/pivot_6",
     "distribution_weighted_P4_1234_01.png"),
    (MVCSOLVER / "mvc-solver-1.5.0/outputs/run_20260303_142944/graph/pivot_2",
     "distribution_weighted_S5_1110101_01.png"),
]

PAPER_FIGURES_DIR = Path.home() / "Desktop/overleaf/qemvc-tqe/figures"

KEEP_BY_QUBITS = {5: 20, 6: 16, 7: 12}


def replot(run_dir: Path, out_path: Path) -> dict:
    """Render a distribution chart from one run's results.json into out_path."""
    results = json.loads((run_dir / "results.json").read_text())
    config = json.loads((run_dir / "config.json").read_text())
    counts = results["counts"]

    n_qubits = len(next(iter(counts)))
    keep = KEEP_BY_QUBITS.get(n_qubits)

    plt.rcParams["font.size"] = 12
    fig = plot_histogram(counts, number_to_keep=keep, bar_labels=True)
    ax = fig.axes[0]
    ax.tick_params(labelsize=11)
    plt.setp(ax.get_xticklabels(), rotation=90)
    if keep and ax.get_xticklabels()[-1].get_text() == "rest":
        rest_patch = ax.patches[-1]
        rest_patch.set_facecolor((0.72, 0.72, 0.72, 1.0))
        rest_patch.set_edgecolor((0.55, 0.55, 0.55, 1.0))
        if ax.texts:
            ax.texts[-1].set_color((0.55, 0.55, 0.55, 1.0))
    ax.set_title(f"Measured Distribution (Pivot={config['pivot_number']})", fontsize=13)
    fig.set_size_inches(6.4, 4.8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=300)
    plt.close(fig)

    kept_sum = sum(counts[k] for k in sorted(counts, key=lambda k: -counts[k])[:keep]) \
        if keep else sum(counts.values())
    return {
        "out": out_path.name,
        "qubits": n_qubits,
        "states": len(counts),
        "bars": (keep or len(counts)) + (1 if keep else 0),
        "rest": sum(counts.values()) - kept_sum,
        "shots": sum(counts.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=str(PAPER_FIGURES_DIR),
                        help="output directory (default: paper figures/)")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the job list and exit without writing files")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    missing = []
    summary = []
    for run_dir, fname in JOBS:
        if not (run_dir / "results.json").exists():
            missing.append(str(run_dir))
            continue
        info = {"source": str(run_dir), "out": fname}
        if not args.dry_run:
            out_dir.mkdir(parents=True, exist_ok=True)
            info.update(replot(run_dir, out_dir / fname))
        summary.append(info)

    width = max(len(s["out"]) for s in summary)
    for s in summary:
        if args.dry_run:
            print(f"[dry-run] {s['out']:<{width}}  <-  {s['source']}")
        else:
            print(f"{s['out']:<{width}}  qubits={s['qubits']} states={s['states']} "
                  f"bars={s['bars']} rest={s['rest']}/1024 -> {s['out']}")

    if missing:
        print("Missing sources:", file=sys.stderr)
        for m in missing:
            print(f"  {m}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())