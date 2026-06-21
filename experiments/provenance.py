"""Provenance manifest system for thesis reproducibility.

Every experiment run produces a JSON manifest capturing:
- git hash and branch
- input parameters (from YAML config)
- output paths
- key results (aggregated from solver outputs)
- environment versions

Usage:
    from experiments.provenance import ManifestBuilder

    builder = ManifestBuilder(table="5.7", config_path="configs/table_5.7_weighted_mvc.yaml")
    builder.add_solver("mvc-solver-1.5.0")
    builder.add_graph_result(name="K_{2,2}", n=4, edges=[[0,2],[0,3],[1,2],[1,3]],
                             weights=[1,2,3,4], qubits=11, optimal_cover=[0,1],
                             success_prob=1.0, grover_iterations=1)
    builder.write("manifests/table_5.7_manifest.json")
"""

import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def _git_hash() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except Exception:
        return "unknown"


def _git_branch() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except Exception:
        return "unknown"


def _env_versions() -> dict[str, str]:
    versions: dict[str, str] = {
        "python": platform.python_version(),
        "platform": platform.platform(),
    }
    for pkg in ("qiskit", "numpy", "scipy", "networkx", "matplotlib"):
        try:
            mod = __import__(pkg)
            versions[pkg] = getattr(mod, "__version__", "unknown")
        except ImportError:
            versions[pkg] = "not installed"
    return versions


def _json_default(obj: Any) -> Any:
    if isinstance(obj, complex):
        return {"real": obj.real, "imag": obj.imag}
    if isinstance(obj, set):
        return sorted(obj)
    if isinstance(obj, Path):
        return str(obj)
    if hasattr(obj, "tolist"):
        return obj.tolist()
    return str(obj)


class ManifestBuilder:
    def __init__(self, table: str, config_path: str, label: str = ""):
        self.table = table
        self.label = label
        self.config_path = config_path
        self.solver: str = ""
        self.method: str = ""
        self.shots: int = 0
        self.grover_iterations: str | int = ""
        self.graphs_input: list[dict] = []
        self.results: list[dict] = []
        self.run_dir: str = ""
        self.extra: dict[str, Any] = {}

    def add_solver(self, solver: str) -> "ManifestBuilder":
        self.solver = solver
        return self

    def add_method(self, method: str) -> "ManifestBuilder":
        self.method = method
        return self

    def add_input_params(
        self, graphs: list[dict], shots: int = 0,
        grover_iterations: str | int = "", method: str = ""
    ) -> "ManifestBuilder":
        self.graphs_input = graphs
        self.shots = shots
        self.grover_iterations = grover_iterations
        if method:
            self.method = method
        return self

    def add_graph_result(self, name: str, **kwargs) -> "ManifestBuilder":
        row = {"instance": name}
        row.update(kwargs)
        self.results.append(row)
        return self

    def add_results(self, rows: list[dict]) -> "ManifestBuilder":
        self.results.extend(rows)
        return self

    def set_run_dir(self, path: str) -> "ManifestBuilder":
        self.run_dir = path
        return self

    def add_extra(self, key: str, value: Any) -> "ManifestBuilder":
        self.extra[key] = value
        return self

    def build(self) -> dict:
        return {
            "manifest_version": "1.0",
            "thesis_table": self.table,
            "thesis_label": self.label,
            "git_commit": _git_hash(),
            "git_branch": _git_branch(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "solver": self.solver,
            "experiment_config": self.config_path,
            "input_params": {
                "graphs": self.graphs_input,
                "shots": self.shots,
                "grover_iterations": self.grover_iterations,
                "method": self.method,
            },
            "outputs": {
                "run_dir": self.run_dir,
            },
            "results": {"rows": self.results},
            "environment": _env_versions(),
            "extra": self.extra,
        }

    def write(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        manifest = self.build()
        p.write_text(json.dumps(manifest, indent=2, default=_json_default, ensure_ascii=False))
        return p


def load_manifest(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())


def read_solver_results(run_dir: str | Path) -> dict:
    """Read results.json and config.json from a solver run directory.

    Looks for run_dir/run_summary.json and per-pivot results.
    Returns a dict with 'summary', 'pivots', and 'config'.
    """
    run_dir = Path(run_dir)
    data: dict[str, Any] = {"pivots": []}

    summary_path = run_dir / "run_summary.json"
    if summary_path.exists():
        data["summary"] = json.loads(summary_path.read_text())

    for pivot_dir in sorted(run_dir.glob("*/pivot_*")):
        results_path = pivot_dir / "results.json"
        config_path = pivot_dir / "config.json"
        pivot_data: dict[str, Any] = {"path": str(pivot_dir)}
        if results_path.exists():
            pivot_data["results"] = json.loads(results_path.read_text())
        if config_path.exists():
            pivot_data["config"] = json.loads(config_path.read_text())
        data["pivots"].append(pivot_data)

    return data
