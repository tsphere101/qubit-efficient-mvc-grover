# Experiments — Thesis Reproducibility

Every thesis table traces to a YAML config and produces a JSON manifest.

## Structure

```
experiments/
├── configs/           # YAML configs for each thesis table
├── manifests/         # JSON manifests from runs (git-tracked)
├── provenance.py      # Manifest builder utility
├── run_all.py         # Master script to run experiments
├── generate_provenance_map.py  # Generate PROVENANCE.md
└── README.md          # This file
```

## Usage

```bash
# List all available tables
python experiments/run_all.py --list

# Run a specific table
python experiments/run_all.py --table 5.7

# Run all tables
python experiments/run_all.py --all

# Generate PROVENANCE.md from manifests
python experiments/generate_provenance_map.py
```

## Table → Config Mapping

| Table | Config | Type | Solver |
|---|---|---|---|
| 5.1 | `table_5.1_qubit_scaling.yaml` | formula | N/A |
| 5.2 | `table_5.2_depth_scaling.yaml` | grover | arithmetic |
| 5.3 | `table_5.3_depth_compare.yaml` | grover | all 3 |
| 5.4 | `table_5.4_success_prob.yaml` | grover | arithmetic (statevector) |
| 5.5 | `table_5.5_grover_vs_qaoa.yaml` | qaoa | arithmetic + QAOA |
| 5.6 | `table_5.6_cx_count.yaml` | transpiled | all 3 |
| 5.7 | `table_5.7_weighted_mvc.yaml` | grover | weighted |
| 5.8 | `table_5.8_full_comparison.yaml` | grover | all 3 |
| 5.9 | `table_5.9_memory_scaling.yaml` | formula | N/A |
| A.1 | `table_A.1_verification.yaml` | transpiled | all 3 |

## Manifest Schema

Each manifest in `manifests/` contains:

```json
{
  "manifest_version": "1.0",
  "thesis_table": "5.7",
  "git_commit": "abc123...",
  "git_branch": "main",
  "timestamp": "2026-06-21T...",
  "solver": "mvc-solver-1.5.0",
  "experiment_config": "experiments/configs/table_5.7_*.yaml",
  "input_params": { "graphs": [...], "shots": 1024, "method": "statevector" },
  "results": { "rows": [...] },
  "environment": { "python": "3.x", "qiskit": "2.4.1", ... }
}
```
