# Quantum Minimum Vertex Cover Solver (v1.3.0)

A Python-based CLI tool that solves the Minimum Vertex Cover (MVC) problem using a quantum algorithm implemented in Qiskit. The solver leverages Grover's Search Algorithm combined with a quantum popcount and comparator circuit to find the smallest set of vertices that covers all edges in a given graph.

## Features

- **Quantum Search**: Uses Grover's algorithm to search for valid vertex covers.
- **Arithmetic Oracle**: Implements quantum binary counters and Cuccaro comparators for exact vertex counting.
- **Penalty System**: Adds $n+1$ penalty for each uncovered edge to ensure feasibility.
- **Hardware Agnostic**: Runs on local simulators (Aer) or IBM Quantum hardware.
- **Automated Experimentation**: Batch solve for ranges of complete graphs or provide custom graph edges.
- **Comprehensive Reporting**: Automatically saves circuits (text and image), measurement distributions, problem graphs, and JSON results/configs.

## Qubit Scaling (v1.3.0)

For a graph with $n$ vertices and $m$ edges, the total qubit requirement $Q_{total}$ is:

$$Q_{total} = n + 2 \lceil \log_2( n + (n+1)m + 1 ) \rceil + 3$$

Where:
- **$n$**: Search space qubits (one per vertex)
- **$2 \times \lceil \log_2( n + (n+1)m + 1 ) \rceil$**: Binary counter and Pivot registers (to hold max vertex count + penalties)
- **$3$**: Ancilla qubits (1 kickback, 1 comparator Z, 1 comparator C)

### Why the $+1$ term?
The $+1$ term in the counter size comes from **binary bit capacity**. To represent a maximum value $V_{max}$ in binary, we need $\lceil \log_2(V_{max} + 1) \rceil$ bits.

#### Example: $K_3$ Graph
For a complete graph $K_3$ ($n=3, m=3$):
- Maximum counter value = $3 + (3+1)\times3 = 15$ (all 3 vertices selected + all 3 edges uncovered)
- Counter bits = $\lceil \log_2(15 + 1) \rceil = 4$ bits

Without the $+1$, we'd use 3 bits which can only hold values 0-7, causing overflow.

## Circuit Depth Scaling (v1.3.0)

For a graph with $n$ vertices and $m$ edges, the gate count per Grover iteration is:

$$D_{iter} = \underbrace{\frac{n \cdot t(t+1)}{2}}_{\text{popcount (fwd+rev)}} + \underbrace{\frac{m \cdot l_p \cdot t(t+1)}{2}}_{\text{penalty adder (fwd+rev)}} + \underbrace{6t + 4n + 5}_{\text{comparator + diffuser + kickback}}$$

Where:
- **$t = \lceil \log_2((n+1)(m+1)) \rceil$**: Binary counter bit width
- **$l_p = \lceil \log_2(n+1) \rceil$**: Penalty bit width
- **$G$**: Number of Grover iterations

**Asymptotic notation:**

$$D_{iter} = O\!\big( m \cdot \log n \cdot \log^2(nm) \big)$$

**Total circuit depth:**

$$D_{total}(n, m, G) = O(n) + G \cdot D_{iter}$$

**Variable definitions:**
| Symbol | Name | Formula |
|--------|------|---------|
| $n$ | Number of vertices | Input parameter |
| $m$ | Number of edges | Input parameter |
| $t$ | Counter bit width | $\lceil \log_2((n+1)(m+1)) \rceil$ |
| $l_p$ | Penalty bit width | $\lceil \log_2(n+1) \rceil$ |
| $G$ | Grover iterations | $\approx \frac{\pi}{4}\sqrt{\frac{2^n}{N_{valid}}}$ |

**Scaling examples:**
| Graph | $n$ | $m$ | $t$ | $D_{iter}$ (asymptotic) |
|-------|-----|-----|-----|------------------------|
| $K_4$ | 4 | 6 | 6 | $O(m \cdot \log n \cdot \log^2(nm))$ |
| $K_8$ | 8 | 28 | 8 | $O(m \cdot \log n \cdot \log^2(nm))$ |
| $K_{10}$ | 10 | 45 | 9 | $O(m \cdot \log n \cdot \log^2(nm))$ |

> **Note:** The dominant term $\frac{m \cdot l_p \cdot t(t+1)}{2}$ scales with both the number of edges and the counter bit width, making this architecture most efficient for sparse graphs.

## Circuit Architecture

The v1.3.0 circuit uses a standard Grover approach with arithmetic penalties:

```
|0⟩ ── H^{⊗n}|pivot⟩|−⟩ ──[Oracle]──[Kickback]──[Uncompute]──[Diffuser]── |0⟩
                                   │              │
                            ┌──────┴──────┐ ┌──────┴──────┐
                            │ Popcount    │ │ Popcount    │
                            │ (+X penalty)│ │ (-X penalty)│
                            ├─────────────┤ ├─────────────┤
                            │ Comparator  │ │ Comparator  │
                            │ (Cuccaro)   │ │ (Inverse)   │
                            └─────────────┘ └─────────────┘
```

### Circuit Components

1. **Initialization**: Applies Hadamard to all search space qubits (uniform superposition), sets pivot register to target value, and prepares kickback qubit in $|-\rangle$.

2. **Oracle (Forward)**:
   - **Popcount**: Uses recursive incrementers to count selected vertices into the binary counter.
   - **Penalty Adder**: First applies X to search space, then for each uncovered edge adds $n+1$ to the counter.
   - **Cuccaro Comparator**: Efficient ripple-carry comparison of counter vs pivot.

3. **Phase Kickback**: Controlled-phase on kickback qubit based on comparator output.

4. **Uncompute**: Reverses all operations to restore ancilla qubits.

5. **Diffuser**: Standard Grover diffuser $H^{\otimes n} \cdot (2|0\rangle\langle 0| - I) \cdot H^{\otimes n}$.

### How the Penalty Works

The penalty mechanism ensures feasibility:
- **Penalty Amount**: $P = n + 1$ (greater than maximum possible vertex count)
- **Valid Cover**: Total = vertex_count (≤ pivot)
- **Invalid Cover**: Total = vertex_count + $P \times$ (uncovered_edges) > pivot

For example, in $K_3$:
- Valid cover (2 vertices): Cost = 2
- Invalid cover (1 vertex, 1 uncovered edge): Cost = 1 + 4×1 = 5 > pivot (typically 2)
- Invalid cover (0 vertices, 3 uncovered edges): Cost = 0 + 4×3 = 12 > pivot

## CLI Usage

Run the solver using `main.py` from the root of the `mvc-solver-1.3.0` directory.

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

**Additional Configuration Combinations:**

1. **Custom graph with high precision and plotting:**
   ```bash
   python main.py --graph-edges "0,1;0,2;1,2" --shots 4096 --plot
   ```

2. **Validate circuit depth/compilation with dry-run (no execution):**
   ```bash
   python main.py --n-range 3 6 --dry-run
   ```

3. **Solve with circuit optimization (disable barriers):**
   ```bash
   python main.py --graph-n 5 --no-barrier
   ```

4. **Force a specific number of Grover iterations:**
   ```bash
   python main.py --graph-edges "0,1;1,2" --grover-iteration 1
   ```

5. **Solve small graphs with full statevector and theoretical analysis:**
   ```bash
   python main.py --n-range 3 4 --include-statevector --include-theoretical
   ```

6. **Solve a 4-node cycle graph:**
   ```bash
   python main.py --graph-edges "0,1;1,2;2,3;3,0"
   ```

7. **Solve a complete graph with high shot count for better statistics:**
   ```bash
   python main.py --graph-n 4 --shots 10000
   ```

8. **Quick sanity check with low shot count:**
   ```bash
   python main.py --graph-n 3 --shots 100
   ```

9. **Batch solve an extended range of complete graphs:**
   ```bash
   python main.py --n-range 2 7
   ```

10. **Solve for a star graph topology:**
    ```bash
    python main.py --graph-edges "0,1;0,2;0,3;0,4"
    ```

### Arguments

| Argument | Type | Description |
| :--- | :--- | :--- |
| `--graph-n` | `int` | Number of vertices for a complete graph. |
| `--n-range` | `int int` | Start and end range for solving multiple complete graphs. |
| `--graph-edges`| `str` | Semicolon-separated list of comma-separated vertex pairs (e.g., `"0,1;1,2"`). |
| `--shots` | `int` | Number of circuit executions (default: 1024). |
| `--plot` | `flag` | Show the measurement histogram after the run. |
| `--include-statevector` | `flag` | Include full statevector in results (CPU/Memory intensive). |
| `--include-theoretical` | `flag` | Include theoretical probability distribution (CPU intensive). |

> [!TIP]
> **Performance for Larger Graphs**: For graphs with more than 15-20 qubits, avoid using `--include-statevector` or `--include-theoretical` as these calculations scale exponentially on the CPU and can significantly slow down the overall runtime.

## Module Overview

### `main.py`
The entry point of the application. It handles CLI argument parsing, orchestrates the iterative "pivot" search (decreasing the target cover size until no solution is found), and manages the timestamped output directory structure.

### `solver/`
Contains the core quantum logic and data models.

- **`engine.py`**: The `VertexCoverSolverEngine` class. It manages the Qiskit environment, transpilation, and job execution using the `SamplerV2` primitive. It also triggers result post-processing and artifact exporting.
- **`circuit_builder.py`**: The `VertexCoverPenaltyCircuitBuilder` class. Implements the quantum circuit:
    - **Popcount**: Calculates the number of selected vertices using a binary incrementer.
    - **Edge Coverage Penalty**: Adds large penalties to the counter for each uncovered edge to ensure feasibility.
    - **Comparator**: Uses a Cuccaro comparator to compare the total count (vertices + penalties) against the pivot.
    - **Diffuser**: Standard Grover diffuser for amplitude amplification.
- **`models.py`**: Defines `SolverConfig` (input parameters) and `SimulationResults` (output data) as Python dataclasses.
- **`utils.py`**: Provides classical helper functions for graph generation (`complete_graph_edges`), Hamming weight calculation, and manual feasibility verification.

### `reporting/`
- **`exporter.py`**: The `ResultExporter` class. Saves the execution context to the `outputs/` folder, including:
    - `config.json` / `results.json`: Input and output data.
    - `graph.png`: Visualization of the problem graph.
    - `distribution.png`: Histogram of measurement results (counts).
    - `distribution_quasi.png`: Visualization of quasi-probabilities derived from shots.
    - `distribution_theoretical.png`: Theoretical probability distribution (only if flagged).
    - `circuit.txt` / `circuit.png`: The generated quantum circuit.

## Outputs

All runs generate a unique folder in `outputs/run_YYYYMMDD_HHMMSS/`. Inside, results are grouped by graph label (e.g., `K_3`) and by the specific `pivot_n` tested during the search process.

A `run_summary.json` is generated at the end of each run, providing the found minimum vertex cover size for each task.
