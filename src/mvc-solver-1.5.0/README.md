# Quantum Minimum Vertex Cover Solver (v1.5.0)

A Python-based CLI tool that solves the Minimum Vertex Cover (MVC) and **Weighted Minimum Vertex Cover** problems using a quantum algorithm implemented in Qiskit. The solver leverages Grover's Search Algorithm combined with a quantum **weight-sum** and comparator circuit to find the smallest (or lowest weight) set of vertices that covers all edges in a given graph.

## Features

- **Quantum Search**: Uses Grover's algorithm to search for valid vertex covers.
- **Weighted Support**: Allows assigning individual weights to vertices to solve the Weighted MVC problem.
- **Skip-K Optimization**: Automatically skips redundant pivots if a smaller valid solution is found during measurement, accelerating the search process.
- **Hardware Agnostic**: Runs on local simulators (Aer) or IBM Quantum hardware.
- **Automated Experimentation**: Batch solve for ranges of complete graphs or provide custom graph edges.
- **Comprehensive Reporting**: Automatically saves circuits (text and image), measurement distributions, problem graphs, and JSON results/configs.

## Qubit Scaling (v1.5.0)

For a graph with $n$ vertices and $m$ edges, the total qubit requirement $Q_{total}$ is:

$$Q_{total} = n + 2 \lceil \log_2( (m+1)(\sum w_i + 1) ) \rceil + 3$$

Where $\sum w_i$ is the total weight sum of all vertices. If all vertices have weight 1 ($w_i=1$), the formula simplifies to:

$$Q_{total} = n + 2 \lceil \log_2( (m+1)(n + 1) ) \rceil + 3$$

### Why the $+1$ terms?
The $(m+1)$ and $(n+1)$ terms appear because the binary counter must accommodate the maximum possible sum without overflow or logic collisions:
- **$(n+1)$**: This is the **Penalty Amount ($P$)**. We use $\sum w_i + 1$ to ensure that any single uncovered edge adds a cost strictly greater than the maximum possible valid vertex weight sum. Without this $+1$, an invalid cover could have the same total weight as a valid one, causing the oracle to match both.
- **$(m+1)$**: This comes from binary **Bit Capacity**. To represent a maximum value $V_{max}$ in binary, we need $\lceil \log_2(V_{max} + 1) \rceil$ bits. Without this $+1$, the register would **overflow** (wrap around to 0) when calculating the maximum sum, leading the oracle to incorrectly identify "Very Bad" states as "Perfect" solutions.

#### Example: Why $n+1$?
In a 3-vertex graph with weights=1, if $P = 3$ (no $+1$):
- **Valid Cover** (3 nodes): Cost = 3.
- **Invalid Cover** (0 nodes, 1 uncovered edge): Cost = $0 + 1 \times 3 = 3$.
Both look identical to the oracle. With $P=4$, the invalid cost is 4, which is correctly rejected if the Pivot is 4.

#### Example: Why $m+1$?
If the maximum sum is 4 (binary `100`), we need 3 bits. If we used only 2 bits ($\lceil \log_2(4) \rceil = 2$):
- A 2-bit register can only hold up to 3.
- Adding to 4 causes an **overflow**: $4 \pmod 4 = 0$.
The oracle would see a cost of 0 for a state that actually costs 4, causing a false positive.

## Circuit Depth Scaling (v1.5.0)

For a graph with $n$ vertices and $m$ edges, the gate count per Grover iteration is:

$$D_{iter} = \underbrace{\frac{n \cdot t(t+1)}{2}}_{\text{weight sum (fwd+rev)}} + \underbrace{\frac{2m \cdot p \cdot t(t+1)}{2}}_{\text{penalty adder (fwd+rev)}} + \underbrace{6t + 4n + 5}_{\text{comparator + diffuser + kickback}}$$

Where:
- **$W = \sum_{i=0}^{n-1} w_i$**: Total weight of all vertices
- **$P = W + 1$**: Penalty amount (ensures invalid covers exceed the pivot)
- **$t = \lceil \log_2(W + m \cdot P) \rceil$**: Binary counter bit width
- **$p = \lceil \log_2(P) \rceil$**: Penalty bit width
- **$G$**: Number of Grover iterations

**Asymptotic notation:**

$$D_{iter} = O\!\big( (n + m \cdot \log W) \cdot \log^2(nm) \big)$$

For **unit weights** ($W = n$, $p = \lceil \log_2(n+1) \rceil$):

$$D_{iter} = O\!\big( m \cdot \log n \cdot \log^2(nm) \big)$$

**Total circuit depth:**

$$D_{total}(n, m, G) = O(n) + G \cdot D_{iter}$$

**Variable definitions:**
| Symbol | Name | Formula |
|--------|------|---------|
| $n$ | Number of vertices | Input parameter |
| $m$ | Number of edges | Input parameter |
| $W$ | Total vertex weight | $\sum w_i$ |
| $P$ | Penalty amount | $W + 1$ |
| $t$ | Counter bit width | $\lceil \log_2(W + m \cdot P) \rceil$ |
| $p$ | Penalty bit width | $\lceil \log_2(P) \rceil$ |
| $G$ | Grover iterations | $\approx \frac{\pi}{4}\sqrt{\frac{2^n}{N_{valid}}}$ |

**Scaling examples (unit weights):**
| Graph | $n$ | $m$ | $t$ | $p$ | $D_{iter}$ (asymptotic) |
|-------|-----|-----|-----|-----|------------------------|
| $K_4$ | 4 | 6 | 7 | 3 | $O(m \cdot \log n \cdot \log^2(nm))$ |
| $K_8$ | 8 | 28 | 9 | 4 | $O(m \cdot \log n \cdot \log^2(nm))$ |
| $K_{10}$ | 10 | 45 | 10 | 4 | $O(m \cdot \log n \cdot \log^2(nm))$ |

> **Note:** For unit weights, v1.5.0 has similar asymptotic complexity to v1.3.0. The key difference is that v1.5.0 supports weighted vertex covers and the Skip-K optimization, which reduces the number of pivots searched. The $m \cdot \log W$ term in the penalty adder reflects the cost of handling per-edge penalty contributions with weighted vertices.

## CLI Usage

Run the solver using `main.py` from the root of the `mvc-solver-1.5.0` directory.

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

**Solve for a Weighted MVC problem:**
```bash
python main.py --graph-edges "0,1;1,2;2,3" --vertex-weights "1,5,1,10"
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
| `--vertex-weights` | `str` | Comma-separated list of integer weights for each vertex (e.g., `"1,2,1"`). |
| `--skip-k` | `flag` | Enable Skip-K optimization to accelerate the search process. |

> [!TIP]
> **Performance for Larger Graphs**: For graphs with more than 15-20 qubits, avoid using `--include-statevector` or `--include-theoretical` as these calculations scale exponentially on the CPU and can significantly slow down the overall runtime.

## Module Overview

### `main.py`
The entry point of the application. It handles CLI argument parsing, orchestrates the iterative "pivot" search (decreasing the target cover size until no solution is found), and manages the timestamped output directory structure.

### `solver/`
Contains the core quantum logic and data models.

- **`engine.py`**: The `VertexCoverSolverEngine` class. It manages the Qiskit environment, transpilation, and job execution using the `SamplerV2` primitive. It also triggers result post-processing and artifact exporting.
- **`circuit_builder.py`**: The `VertexCoverPenaltyCircuitBuilder` class. Implements the quantum circuit:
    - **WeightSum**: Calculates the total weight of selected vertices by summing their individual weights into a binary counter.
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
