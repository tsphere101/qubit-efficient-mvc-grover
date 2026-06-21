#!/usr/bin/env python3
"""Master experiment runner — reproduces every thesis table.

Usage:
    python experiments/run_all.py --table 5.7    # re-run specific table
    python experiments/run_all.py --all          # re-run everything
    python experiments/run_all.py --list         # list available tables

Each table has a YAML config in experiments/configs/.
Each run produces a JSON manifest in experiments/manifests/.
"""

import argparse
import itertools
import json
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "experiments"))

from provenance import ManifestBuilder, read_solver_results

try:
    import yaml
except ImportError:
    print("pyyaml required: pip install pyyaml")
    sys.exit(1)

CONFIGS_DIR = REPO_ROOT / "experiments" / "configs"
MANIFESTS_DIR = REPO_ROOT / "experiments" / "manifests"
OUTPUTS_DIR = REPO_ROOT / "outputs"

SOLVERS = {
    "arithmetic": REPO_ROOT / "src" / "mvc-solver-1.3.0",
    "dicke": REPO_ROOT / "src" / "mvc-solver-1.4.0",
    "weighted": REPO_ROOT / "src" / "mvc-solver-1.5.0",
    "qaoa": REPO_ROOT / "src" / "mvc_qaoa",
}

VENV_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"
if not VENV_PYTHON.exists():
    VENV_PYTHON = Path(sys.executable)


def load_config(table: str) -> dict:
    config_path = CONFIGS_DIR / f"table_{table}_*.yaml"
    matches = list(CONFIGS_DIR.glob(f"table_{table}_*.yaml"))
    if not matches:
        raise FileNotFoundError(f"No config found for table {table}")
    return yaml.safe_load(matches[0].read_text())


def list_tables() -> list[str]:
    configs = sorted(CONFIGS_DIR.glob("table_*.yaml"))
    tables = []
    for c in configs:
        name = c.stem
        if name.startswith("table_"):
            t = name.replace("table_", "").split("_")[0]
            tables.append(t)
    return tables


def complete_graph_edges(n: int) -> list[list[int]]:
    return [[i, j] for i in range(n) for j in range(i + 1, n)]


def run_solver(
    solver_key: str,
    args: list[str],
    cwd: Path | None = None,
) -> subprocess.CompletedProcess:
    solver_dir = SOLVERS[solver_key]
    cmd = [str(VENV_PYTHON), "main.py"] + args
    cwd = cwd or solver_dir
    print(f"  Running: {' '.join(cmd)} (cwd={cwd})")
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)


def run_grover_table(config: dict, table_id: str) -> dict:
    """Run a Grover solver table (arithmetic, dicke, or weighted)."""
    solver_key = config.get("solver_key", "arithmetic")
    graphs = config.get("graphs", [])
    shots = config.get("shots", 1024)
    method = config.get("method", "statevector")
    grover_iter = config.get("grover_iterations", "")
    include_sv = config.get("include_statevector", True)
    include_theory = config.get("include_theoretical", False)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    table_slug = table_id.replace(".", "_")
    run_dir = OUTPUTS_DIR / f"run_{timestamp}_table_{table_slug}"
    run_dir.mkdir(parents=True, exist_ok=True)

    builder = ManifestBuilder(
        table=table_id,
        label=config.get("label", ""),
        config_path=f"experiments/configs/table_{table_id}*.yaml",
    )
    builder.add_solver(config.get("solver", solver_key))
    builder.add_input_params(graphs, shots=shots, grover_iterations=grover_iter, method=method)
    builder.set_run_dir(str(run_dir))

    for g in graphs:
        name = g["name"]
        n = g["n"]
        edges = g.get("edges", complete_graph_edges(n))
        weights = g.get("weights")

        edges_str = ";".join(f"{u},{v}" for u, v in edges)
        args = [
            "--graph-n", str(n),
            "--graph-edges", edges_str,
            "--shots", str(shots),
        ]
        if grover_iter and grover_iter != "optimal":
            args.extend(["--grover-iteration", str(grover_iter)])
        if include_sv:
            args.append("--include-statevector")
        if include_theory:
            args.append("--include-theoretical")
        if config.get("no_barrier", False):
            args.append("--no-barrier")
        if weights:
            args.extend(["--vertex-weights", ",".join(str(w) for w in weights)])
        if config.get("skip_k", False):
            args.append("--skip-k")

        print(f"  [{table_id}] {name} (n={n}, edges={len(edges)})...")
        result = run_solver(solver_key, args)

        if result.returncode != 0:
            print(f"    WARNING: solver returned {result.returncode}")
            print(f"    stderr: {result.stderr[:500]}")
            builder.add_graph_result(name=name, status="failed", error=result.stderr[:500])
        else:
            print(f"    OK")
            builder.add_graph_result(name=name, status="ok", n=n, edges=len(edges))

    manifest_path = MANIFESTS_DIR / f"table_{table_slug}_manifest.json"
    builder.write(manifest_path)
    print(f"  Manifest: {manifest_path}")
    return {"manifest": str(manifest_path), "run_dir": str(run_dir)}


def run_qaoa_table(config: dict, table_id: str) -> dict:
    """Run QAOA benchmark for a table."""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    table_slug = table_id.replace(".", "_")
    run_dir = SOLVERS["qaoa"] / "experiments" / f"run_{timestamp}_table_{table_slug}"

    p_values = config.get("p_values", [1])
    shots = config.get("shots", 4096)
    maxiter = config.get("maxiter", 80)
    restarts = config.get("random_restarts", 5)

    builder = ManifestBuilder(
        table=table_id,
        label=config.get("label", ""),
        config_path=f"experiments/configs/table_{table_id}*.yaml",
    )
    builder.add_solver("mvc_qaoa")
    builder.add_input_params(
        graphs=config.get("graphs", []),
        shots=shots,
        grover_iterations="N/A",
        method="QAOA",
    )
    builder.add_extra("p_values", p_values)
    builder.add_extra("maxiter", maxiter)
    builder.add_extra("random_restarts", restarts)
    builder.set_run_dir(str(run_dir))

    print(f"  QAOA benchmarks not yet automated via run_all.")
    print(f"  Use: cd src/mvc_qaoa && python main.py")
    builder.add_extra("note", "QAOA runs manually; manifest is a placeholder")

    manifest_path = MANIFESTS_DIR / f"table_{table_slug}_manifest.json"
    builder.write(manifest_path)
    print(f"  Manifest (placeholder): {manifest_path}")
    return {"manifest": str(manifest_path)}


def run_formula_table(config: dict, table_id: str) -> dict:
    """Formula-based table (no experiment needed)."""
    table_slug = table_id.replace(".", "_")
    manifest_path = MANIFESTS_DIR / f"table_{table_slug}_manifest.json"

    builder = ManifestBuilder(
        table=table_id,
        label=config.get("label", ""),
        config_path=f"experiments/configs/table_{table_id}*.yaml",
    )
    builder.add_solver("formula (no experiment)")
    builder.add_input_params(
        graphs=config.get("graphs", []),
        method="formula",
    )
    builder.add_extra("formula", config.get("formula", ""))
    builder.add_extra("description", config.get("description", ""))
    builder.write(manifest_path)
    print(f"  Formula manifest: {manifest_path}")
    return {"manifest": str(manifest_path)}


def run_transpiled_table(config: dict, table_id: str) -> dict:
    """Transpiled resource comparison table."""
    table_slug = table_id.replace(".", "_")
    script = config.get("script", "")
    script_path = REPO_ROOT / script if script else None

    builder = ManifestBuilder(
        table=table_id,
        label=config.get("label", ""),
        config_path=f"experiments/configs/table_{table_id}*.yaml",
    )
    builder.add_solver("transpiled comparison script")
    builder.add_input_params(
        graphs=config.get("graphs", []),
        method="transpilation",
    )

    if script_path and script_path.exists():
        print(f"  Running: {script_path}")
        result = subprocess.run(
            [str(VENV_PYTHON), str(script_path)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(f"  OK")
            builder.add_extra("stdout", result.stdout[-500:])
        else:
            print(f"  WARNING: script failed")
            builder.add_extra("stderr", result.stderr[:500])
    else:
        print(f"  Script not found: {script_path}")
        builder.add_extra("note", "Script not yet available")

    manifest_path = MANIFESTS_DIR / f"table_{table_slug}_manifest.json"
    builder.write(manifest_path)
    print(f"  Manifest: {manifest_path}")
    return {"manifest": str(manifest_path)}


def run_table(table_id: str) -> dict:
    config = load_config(table_id)
    table_type = config.get("type", "grover")

    print(f"\n{'='*60}")
    print(f"  Table {table_id}: {config.get('title', '')}")
    print(f"  Type: {table_type}")
    print(f"{'='*60}")

    MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)

    if table_type == "formula":
        return run_formula_table(config, table_id)
    elif table_type == "qaoa":
        return run_qaoa_table(config, table_id)
    elif table_type == "transpiled":
        return run_transpiled_table(config, table_id)
    else:
        return run_grover_table(config, table_id)


def main():
    parser = argparse.ArgumentParser(description="Run thesis experiments with provenance")
    parser.add_argument("--table", help="Specific table to run (e.g., 5.7)")
    parser.add_argument("--all", action="store_true", help="Run all tables")
    parser.add_argument("--list", action="store_true", help="List available tables")
    args = parser.parse_args()

    if args.list:
        tables = list_tables()
        print("Available tables:")
        for t in tables:
            config = load_config(t)
            print(f"  Table {t}: {config.get('title', '')} [{config.get('type', 'grover')}]")
        return

    if args.all:
        tables = list_tables()
        results = {}
        for t in tables:
            try:
                results[t] = run_table(t)
            except Exception as e:
                print(f"  ERROR: {e}")
                results[t] = {"error": str(e)}
        print(f"\n{'='*60}")
        print("Summary:")
        for t, r in results.items():
            status = "OK" if "error" not in r else "FAILED"
            print(f"  Table {t}: {status}")
        return

    if args.table:
        result = run_table(args.table)
        print(f"\nDone: {result}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
