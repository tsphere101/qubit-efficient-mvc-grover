# Quantum Minimum Vertex Cover Solver (v1.4.0)

A Python-based CLI tool that solves the Minimum Vertex Cover (MVC) problem using a quantum algorithm implemented in Qiskit. This version (1.4.0) introduces a significantly optimized architecture using **Generalized Dicke State Preparation (GDSP)**, which eliminates the need for binary counters and arithmetic comparators, drastically reducing qubit usage and circuit depth.

## Features

- **Optimized State Preparation**: Uses Generalized Dicke States $|D_{<=k}^n\rangle$ to restrict the search space to vertex covers of size $\le k$, replacing the expensive quantum popcount.
- **Efficient Oracle**: Implements a lightweight, ancilla-based oracle to verify edge coverage without arithmetic penalties.
- **Hardware Agnostic**: Runs on local simulators (Aer) or IBM Quantum hardware.
- **Automated Experimentation**: Batch solve for ranges of complete graphs or provide custom graph edges.
- **Comprehensive Reporting**: Automatically saves circuits, measurement distributions, and resource statistics.

## New in v1.4.0: Dicke State Integration

Previous versions relied on a quantum binary counter and a Cuccaro comparator to enforce vertex count constraints. Version 1.4.0 replaces these with a search space centered around the **Generalized Dicke State**, which naturally represents all combinations of $n$ qubits with Hamming weight up to $k$.

**Benefits include:**
- **Qubit Reduction**: Reduces total qubit usage by ~40% (e.g., K3 reduced from 14 to 8 qubits).
- **Lower Circuit Depth**: Eliminates the complex multi-level logic of quantum adders and comparators.
- **Improved Fidelity**: Shorter circuits lead to better results on near-term quantum hardware.

## Qubit Scaling (v1.4.0)

For a graph with $n$ vertices and $m$ edges, the total qubit requirement $Q_{total}$ is:

$$Q_{total} = n + m + 2$$

The v1.4.0 architecture achieves maximum qubit efficiency by:
- **n qubits**: For the search space (one per vertex).
- **m qubits**: One ancilla qubit per edge to check coverage.
- **2 qubits**: One for phase kickback ($|-\rangle$), one to aggregate all feasible results.

### Why No Counter Needed?

Unlike v1.3.0 and v1.5.0, v1.4.0 does NOT use a binary counter. Instead, it leverages the **Generalized Dicke State** property: the state $|D_{≤k}^n\rangle$ already contains only vertex combinations with Hamming weight ≤ k. By preparing this state initially, we eliminate the need for:
- Quantum popcount circuits
- Arithmetic penalty adders
- Binary comparators

This results in dramatic qubit savings, especially for larger graphs.

## Circuit Depth Scaling (v1.4.0)

For a graph with $n$ vertices and $m$ edges, the gate count per Grover iteration is:

$$D_{iter} = \underbrace{2 \cdot D_{GDSP}}_{\text{diffuser (fwd+rev)}} + \underbrace{8n + 28m + 8}_{\text{oracle (fwd+rev) + kickback}} + \underbrace{2n + 3}_{\text{diffuser reflection}}$$

Where $D_{GDSP}$ is the Generalized Dicke State Preparation gate count (from Narisada et al. 2023, Algorithm 2):

$$D_{GDSP}(n, k) = 2nk^2 - \frac{k^3}{3} - 5k^2 + 8nk - \frac{14k}{3} - 15n + 22$$

**Asymptotic notation:**

$$D_{GDSP}(n, k) = O(nk^2)$$

$$D_{iter} = O(nk^2 + m)$$

**Total circuit depth:**

$$D_{total}(n, m, k, G) = O(nk^2) + G \cdot O(nk^2 + m)$$

**Variable definitions:**
| Symbol | Name | Formula |
|--------|------|---------|
| $n$ | Number of vertices | Input parameter |
| $m$ | Number of edges | Input parameter |
| $k$ | Dicke state weight threshold | Pivot value ($k = w$ in the algorithm) |
| $D_{GDSP}(n,k)$ | GDSP gate count | $2nk^2 - \frac{k^3}{3} + O(nk + k^2 + n)$ |
| $G$ | Grover iterations | $\approx \frac{\pi}{4}\sqrt{\frac{2^n}{\binom{n}{\leq k}}}$ |

**Scaling examples:**
| Graph | $n$ | $m$ | $k$ | $D_{GDSP}$ | $D_{iter}$ (dominant) |
|-------|-----|-----|-----|------------|----------------------|
| $K_4$ | 4 | 6 | 2 | 52 | $O(nk^2)$ |
| $K_8$ | 8 | 28 | 4 | 432 | $O(nk^2)$ |
| $K_{10}$ | 10 | 45 | 5 | 920 | $O(nk^2)$ |

> **Note:** The Dicke State Preparation dominates the circuit depth ($O(nk^2)$), while the oracle scales only linearly with edges ($O(m)$). This makes v1.4.0 particularly efficient when $k \ll n$ (i.e., when searching for small vertex covers).

## Circuit Architecture

The v1.4.0 circuit uses a pure Dicke state approach with ancilla-based edge checking:

```
|0⟩ ── GDS(|D_{≤k}⟩) ──[Oracle]──[Kickback]──[Uncompute]──[Diffuser]── |0⟩
                           │
                    ┌──────┴──────┐
                    │ Edge Check  │
                    │ (m ancillas)│
                    ├──────────────�
                    │ All-Feasible│
                    │ Aggregation │
                    └──────────────┘
```

### Circuit Components

1. **Initialization ($|D_{≤k}^n\rangle$)**: Prepares the Generalized Dicke State using a recursive Gray-code based construction.

2. **Oracle (Edge Coverage)**:
   - **Edge Detection**: For each edge $(u, v)$, applies $X$ to search space, then uses MCX to set edge ancilla if BOTH endpoints are 0 (uncovered).
   - **Aggregation**: Uses MCX over all edge ancillas to set the `all_feasible` flag if NO edges are uncovered.
   - **Uncomputation**: Reverses the edge detection to restore ancillas.

3. **Phase Kickback**: Controlled-Z rotation via the `all_feasible` flag on the kickback qubit.

4. **Diffuser**: Reflection around the Dicke state: $GDS \cdot (2|0\rangle\langle 0| - I) \cdot GDS^\dagger$.

### Key Innovation: Why It Works

The key insight is that by initializing in $|D_{≤k}^n\rangle$:
- States with >k vertices have **zero amplitude** from the start
- We only need to check edge coverage (no popcount needed)
- The diffuser naturally amplifies valid covers because it reflects around the Dicke subspace

## CLI Usage

Run the solver using `main.py` from the root of the `mvc-solver-1.4.0` directory.

### Examples

**Solve for a specific complete graph $K_4$:**
```bash
python main.py --graph-n 4
```

**Batch solve for a range of complete graphs ($K_3$ to $K_5$):**
```bash
python main.py --n-range 3 5
```

**Solve for a custom graph:**
```bash
python main.py --graph-edges "0,1;1,2;2,3"
```

**Solve with a specific number of shots and show plots:**
```bash
python main.py --graph-n 3 --shots 2048 --plot
```

### Arguments

| Argument | Type | Description |
| :--- | :--- | :--- |
| `--graph-n` | `int` | Number of vertices for a complete graph. |
| `--n-range` | `int int` | Start and end range for solving multiple complete graphs. |
| `--graph-edges`| `str` | Semicolon-separated list of vertex pairs (e.g., `"0,1;1,2"`). |
| `--shots` | `int` | Number of circuit executions (default: 1024). |
| `--plot` | `flag` | Show the measurement histogram after the run. |
| `--include-statevector` | `flag` | Include full statevector in results (CPU/Memory intensive). |
| `--include-theoretical` | `flag` | Include theoretical probability distribution. |

## Module Overview

### `main.py`
The entry point. Orchestrates the iterative "pivot" search, decreasing the target cover size $k$ until the Dicke-state-restricted Grover search no longer finds valid solutions.

### `solver/`
- **`engine.py`**: Manages the Qiskit environment, transpilation, and job execution.
- **`circuit_builder.py`**: Now implements the **GDSP-centered Grover algorithm**:
    - **Initialization**: Prepares the $|D_{<=k}^n\rangle$ state.
    - **Oracle**: Marks states covering all edges using one ancilla per edge.
    - **Diffuser**: Reflection around the Generalized Dicke State.
- **`models.py`**: Defines `SolverConfig` and `SimulationResults`.
- **`utils.py`**: Includes the `create_generalized_dicke_state` implementation and graph helpers.

### `reporting/`
- **`exporter.py`**: Saves configurations, JSON results, graphs, and circuit visualizations to the `outputs/` folder.

## Outputs

All runs generate a unique folder in `outputs/run_YYYYMMDD_HHMMSS/`. Inside, results are grouped by graph label (e.g., `K_3`) and by the specific `pivot_n` tested.

A `run_summary.json` provides the final minimum vertex cover size for each task.
