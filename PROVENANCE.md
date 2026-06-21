# Thesis Provenance Map

Every number, table, figure, and claim in the thesis traces to reproducible code.

## Tables

| Table | Manifest | Config | Solver | Method |
|---|---|---|---|---|
| 5.1 (tab:qubit-scaling) | `manifests/table_5_1_manifest.json` | `configs/table_5.1*` | formula (no experiment) | formula |

## Figure Generators

| Generator | Script |
|---|---|
| bloch_sphere | `diagrams/bloch_sphere.py` |
| box_circuit_generator | `diagrams/box_circuit_generator.py` |
| circuit_depth_comparison | `diagrams/circuit_depth_comparison.py` |
| fully_connected_graph | `diagrams/fully_connected_graph.py` |
| gate_decomposition | `diagrams/gate_decomposition.py` |
| generate_scaling_charts | `diagrams/generate_scaling_charts.py` |
| mvc_graph | `diagrams/mvc_graph.py` |
| mvc_graph_example | `diagrams/mvc_graph_example.py` |
| quantum_gates | `diagrams/quantum_gates.py` |
| qubit_utilization | `diagrams/qubit_utilization.py` |
| qubit_utilization_3d | `diagrams/qubit_utilization_3d.py` |
| simulation_runtime | `diagrams/simulation_runtime.py` |

## Environment

| Package | Version |
|---|---|
| python | 3.14.3 |
| platform | macOS-26.5-arm64-arm-64bit-Mach-O |
| qiskit | 2.4.1 |
| numpy | 2.4.4 |
| scipy | 1.17.1 |
| networkx | 3.6.1 |
| matplotlib | 3.10.9 |

**Git commit:** `9dcb60bb4fd9406e9208e7283bd722a994195dd8`
**Branch:** `feat/i-081-provenance-infra`
