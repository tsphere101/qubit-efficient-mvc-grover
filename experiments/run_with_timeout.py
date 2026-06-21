#!/usr/bin/env python3
"""Batch run experiments — small graphs first, 3-min timeout per graph."""
import json
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "experiments"))
from provenance import ManifestBuilder

VENV_PYTHON = str(REPO_ROOT / ".venv" / "bin" / "python")
SOLVER_130 = REPO_ROOT / "src" / "mvc-solver-1.3.0"
SOLVER_140 = REPO_ROOT / "src" / "mvc-solver-1.4.0"
SOLVER_150 = REPO_ROOT / "src" / "mvc-solver-1.5.0"
MANIFESTS_DIR = REPO_ROOT / "experiments" / "manifests"
MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)

TIMEOUT = 30  # Only fast graphs for now; come back for slow ones later

def complete_graph_edges(n):
    return [[i, j] for i in range(n) for j in range(i + 1, n)]

def run_one(solver_dir, args, label):
    cmd = [VENV_PYTHON, "main.py"] + args
    print(f"  [{label}] Running (timeout={TIMEOUT}s)...", flush=True)
    start = time.time()
    try:
        result = subprocess.run(
            cmd, cwd=str(solver_dir),
            capture_output=True, text=True,
            timeout=TIMEOUT,
        )
        elapsed = time.time() - start
        ok = result.returncode == 0
        print(f"  [{label}] {'OK' if ok else 'FAIL'} ({elapsed:.1f}s)", flush=True)
        if not ok:
            print(f"  [{label}] stderr: {result.stderr[:300]}", flush=True)
        return ok, result.stdout + result.stderr, elapsed
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        print(f"  [{label}] TIMEOUT ({elapsed:.1f}s) — SKIPPED", flush=True)
        return False, "TIMEOUT", elapsed

# Define all tasks, ordered by estimated runtime (smallest n first)
TASKS = [
    # --- Fast: K3-K5 across tables ---
    {"table": "5.2", "label": "tab:depth-scaling", "solver_dir": SOLVER_130, "solver": "mvc-solver-1.3.0",
     "name": "K3", "n": 3, "extra": ["--grover-iteration", "1"]},
    {"table": "5.2", "label": "tab:depth-scaling", "solver_dir": SOLVER_130, "solver": "mvc-solver-1.3.0",
     "name": "K4", "n": 4, "extra": ["--grover-iteration", "1"]},
    {"table": "5.2", "label": "tab:depth-scaling", "solver_dir": SOLVER_130, "solver": "mvc-solver-1.3.0",
     "name": "K5", "n": 5, "extra": ["--grover-iteration", "1"]},
    {"table": "5.4", "label": "tab:success-prob", "solver_dir": SOLVER_130, "solver": "mvc-solver-1.3.0",
     "name": "K3", "n": 3, "extra": []},
    {"table": "5.4", "label": "tab:success-prob", "solver_dir": SOLVER_130, "solver": "mvc-solver-1.3.0",
     "name": "K4", "n": 4, "extra": []},
    {"table": "5.4", "label": "tab:success-prob", "solver_dir": SOLVER_130, "solver": "mvc-solver-1.3.0",
     "name": "K5", "n": 5, "extra": []},
    {"table": "5.3", "label": "tab:depth-compare", "solver_dir": SOLVER_130, "solver": "mvc-solver-1.3.0",
     "name": "K3", "n": 3, "extra": ["--grover-iteration", "1"]},
    {"table": "5.3", "label": "tab:depth-compare", "solver_dir": SOLVER_130, "solver": "mvc-solver-1.3.0",
     "name": "K4", "n": 4, "extra": ["--grover-iteration", "1"]},
    {"table": "5.3", "label": "tab:depth-compare", "solver_dir": SOLVER_130, "solver": "mvc-solver-1.3.0",
     "name": "K5", "n": 5, "extra": ["--grover-iteration", "1"]},
    # Dicke K3-K5
    {"table": "5.3", "label": "tab:depth-compare-dicke", "solver_dir": SOLVER_140, "solver": "mvc-solver-1.4.0",
     "name": "K3", "n": 3, "extra": ["--grover-iteration", "1"]},
    {"table": "5.3", "label": "tab:depth-compare-dicke", "solver_dir": SOLVER_140, "solver": "mvc-solver-1.4.0",
     "name": "K4", "n": 4, "extra": ["--grover-iteration", "1"]},
    {"table": "5.3", "label": "tab:depth-compare-dicke", "solver_dir": SOLVER_140, "solver": "mvc-solver-1.4.0",
     "name": "K5", "n": 5, "extra": ["--grover-iteration", "1"]},
    # Weighted K_{2,2} (already done, re-run for manifest)
    {"table": "5.7", "label": "tab:weighted-results", "solver_dir": SOLVER_150, "solver": "mvc-solver-1.5.0",
     "name": "K_{2,2}", "n": 4, "edges": [[0,2],[0,3],[1,2],[1,3]], "weights": [1,2,3,4], "extra": ["--skip-k"]},
    {"table": "5.7", "label": "tab:weighted-results", "solver_dir": SOLVER_150, "solver": "mvc-solver-1.5.0",
     "name": "K_{2,3}", "n": 5, "edges": [[0,2],[0,3],[0,4],[1,2],[1,3],[1,4]], "weights": [2,3,1,4,5], "extra": ["--skip-k"]},

    # --- Medium: K6 ---
    {"table": "5.2", "label": "tab:depth-scaling", "solver_dir": SOLVER_130, "solver": "mvc-solver-1.3.0",
     "name": "K6", "n": 6, "extra": ["--grover-iteration", "1"]},
    {"table": "5.4", "label": "tab:success-prob", "solver_dir": SOLVER_130, "solver": "mvc-solver-1.3.0",
     "name": "K6", "n": 6, "extra": []},
    {"table": "5.3", "label": "tab:depth-compare", "solver_dir": SOLVER_130, "solver": "mvc-solver-1.3.0",
     "name": "K6", "n": 6, "extra": ["--grover-iteration", "1"]},
    {"table": "5.8", "label": "tab:full-comparison", "solver_dir": SOLVER_130, "solver": "mvc-solver-1.3.0",
     "name": "K6", "n": 6, "extra": ["--grover-iteration", "1"]},

    # --- Slow: K7, Dicke K6, large bipartite (may timeout) ---
    {"table": "5.2", "label": "tab:depth-scaling", "solver_dir": SOLVER_130, "solver": "mvc-solver-1.3.0",
     "name": "K7", "n": 7, "extra": ["--grover-iteration", "1"]},
    {"table": "5.4", "label": "tab:success-prob", "solver_dir": SOLVER_130, "solver": "mvc-solver-1.3.0",
     "name": "K7", "n": 7, "extra": []},
    {"table": "5.3", "label": "tab:depth-compare", "solver_dir": SOLVER_130, "solver": "mvc-solver-1.3.0",
     "name": "K7", "n": 7, "extra": ["--grover-iteration", "1"]},
    {"table": "5.3", "label": "tab:depth-compare-dicke", "solver_dir": SOLVER_140, "solver": "mvc-solver-1.4.0",
     "name": "K6", "n": 6, "extra": ["--grover-iteration", "1"]},
    {"table": "5.7", "label": "tab:weighted-results", "solver_dir": SOLVER_150, "solver": "mvc-solver-1.5.0",
     "name": "K_{3,3}", "n": 6, "edges": [[0,3],[0,4],[0,5],[1,3],[1,4],[1,5],[2,3],[2,4],[2,5]], "weights": [5,2,3,1,4,6], "extra": ["--skip-k"]},
    {"table": "5.7", "label": "tab:weighted-results", "solver_dir": SOLVER_150, "solver": "mvc-solver-1.5.0",
     "name": "K_{3,4}", "n": 7, "edges": [[0,3],[0,4],[0,5],[0,6],[1,3],[1,4],[1,5],[1,6],[2,3],[2,4],[2,5],[2,6]], "weights": [3,7,2,5,1,4,6], "extra": ["--skip-k"]},
    {"table": "5.7", "label": "tab:weighted-results", "solver_dir": SOLVER_150, "solver": "mvc-solver-1.5.0",
     "name": "K_{3,5}", "n": 8, "edges": [[0,3],[0,4],[0,5],[0,6],[0,7],[1,3],[1,4],[1,5],[1,6],[1,7],[2,3],[2,4],[2,5],[2,6],[2,7]], "weights": [2,4,6,8,1,3,5,7], "extra": ["--skip-k"]},
]

def main():
    # Group results by table for manifest building
    table_results: dict[str, list] = {}
    all_skipped = []

    for task in TASKS:
        table = task["table"]
        name = task["name"]
        n = task["n"]
        edges = task.get("edges", complete_graph_edges(n))
        weights = task.get("weights")
        edges_str = ";".join(f"{u},{v}" for u, v in edges)

        args = [
            "--graph-n", str(n),
            "--graph-edges", edges_str,
            "--shots", "1024",
            "--no-barrier",
        ] + task["extra"]

        if weights:
            args.extend(["--vertex-weights", ",".join(str(w) for w in weights)])

        label = f"{table}/{name}"
        ok, output, elapsed = run_one(task["solver_dir"], args, label)

        entry = {"name": name, "n": n, "edges": len(edges), "elapsed": elapsed}
        if weights:
            entry["weights"] = weights
        if ok:
            entry["status"] = "ok"
        else:
            entry["status"] = "skipped"
            entry["reason"] = "timeout" if output == "TIMEOUT" else output[:200]
            all_skipped.append({"table": table, "graph": name, "n": n, "reason": entry["reason"]})

        table_results.setdefault(table, {"solver": task["solver"], "label": task["label"], "rows": []})
        table_results[table]["rows"].append(entry)

    # Build manifests per table
    for table, info in table_results.items():
        builder = ManifestBuilder(
            table=table, label=info["label"],
            config_path=f"experiments/configs/table_{table}*.yaml",
        )
        builder.add_solver(info["solver"])
        builder.add_input_params([], shots=1024, method="shot-based")
        builder.add_results(info["rows"])
        slug = table.replace(".", "_")
        manifest_path = MANIFESTS_DIR / f"table_{slug}_manifest.json"
        builder.write(manifest_path)
        ok_count = sum(1 for r in info["rows"] if r["status"] == "ok")
        print(f"  Manifest {table}: {ok_count}/{len(info['rows'])} ok → {manifest_path}")

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    if all_skipped:
        print(f"Skipped {len(all_skipped)} graph(s):")
        for s in all_skipped:
            print(f"  Table {s['table']}: {s['graph']} (n={s['n']}) — {s['reason'][:50]}")
    else:
        print("All graphs completed!")

    (MANIFESTS_DIR / "skipped_graphs.json").write_text(json.dumps(all_skipped, indent=2))

if __name__ == "__main__":
    main()
