# MVC QAOA Benchmark Suite

A systematic, reproducible benchmark suite for solving the **Minimum Vertex Cover** (MVC) problem with the **Quantum Approximate Optimisation Algorithm** (QAOA).  The suite runs QAOA on a diverse set of graph topologies (cliques, cycles, stars, paths, and custom graphs), compares p=1, p=2, and p=3 circuit depths, and saves every result in a structured, timestamped directory.

---

## Directory Layout

```
.
├── README.md                 # This file
├── main.py                   # Entry point — runs the full benchmark
├── src/                      # Core library (pure Python, no CLI logic)
│   ├── graphs.py             # Graph generators (cliques, cycles, stars, paths)
│   ├── qubo.py               # MVC QUBO formulation + cost evaluation
│   ├── ising.py              # QUBO → Ising (Pauli-Z) mapping
│   ├── circuit.py            # QAOA circuit builder for arbitrary Ising terms
│   ├── exact.py              # Brute-force solver for small instances
│   ├── optimizer.py          # Classical optimisation wrapper (COBYLA, restarts)
│   ├── simulator.py          # AerSimulator execution + result analysis
│   └── reporter.py           # JSON / text / PNG output helpers
└── experiments/
    └── run_YYYYMMDD_HHMMSS/  # One timestamped run
        ├── run_config.json
        ├── benchmark_summary.json
        ├── benchmark_table.md
        ├── scaling_plot.png
        ├── approximation_ratio.png
        ├── K3/
        │   ├── graph.jpg               # NetworkX-rendered graph image
        │   ├── p1/
        │   │   ├── circuit.txt         # Qiskit text diagram (fold=-1)
        │   │   ├── circuit.png         # Matplotlib diagram
        │   │   ├── convergence.png     # Optimiser cost vs iteration
        │   │   ├── distribution.png    # Measurement histogram
        │   │   ├── exact_solution.json # Brute-force ground truth
        │   │   └── results.json        # Complete experiment data
        │   ├── p2/
        │   │   └── ...
        │   └── p3/
        │       └── ...
        ├── K4/
        │   └── ...
        └── ...
```

---

## How to Run

```bash
# From inside the mvc_qaoa/ directory:
python main.py
```

The script creates a new timestamped folder under `experiments/` and populates it with all artifacts.  No arguments are required — everything is configured via the constants at the top of `main.py`.

**Key hyperparameters** (editable in `main.py`):
- `PS = [1, 2, 3]` — QAOA layers to test
- `SHOTS_PER_EVAL = 1024` — shots per cost-function call during optimisation
- `SHOTS_FINAL = 4096` — shots for the final verification simulation
- `MAXITER = 80` — COBYLA iteration budget per restart
- `RANDOM_RESTARTS = 2` — number of random initial guesses

---

## Source-Code Walkthrough

### `src/graphs.py` — Graph Definitions

**Why this file exists:**  Before we can formulate a QUBO we need a graph.  Rather than hard-coding edges in `main.py`, every topology lives here as a small generator function.  This makes it trivial to add new graphs without touching the solver logic.

**`clique(n)`**  
Generates all `n(n-1)/2` edges of a complete graph `K_n`.  Cliques are the densest possible graphs — they stress-test the circuit builder because every pair of vertices requires a two-qubit `ZZ` term.

**`cycle(n)`**  
Generates a ring graph `C_n` where each vertex connects only to its two neighbours.  Cycles have uniform low degree, so the QUBO penalty weight is small and the Ising Hamiltonian is sparse.

**`star(n)`**  
Generates a hub-and-spoke graph `S_n` with one central vertex connected to all others.  Stars are interesting because the central vertex dominates the QUBO — it has high degree while leaves have degree 1.  This asymmetry tests whether QAOA can correctly identify the hub as part of the cover.

**`path(n)`**  
Generates a linear chain `P_n`.  Paths are the sparsest connected graphs.  They test whether QAOA works when the minimum cover is spread along the chain (every other vertex).

**`BENCHMARK_GRAPHS`**  
A single list-of-dicts that declares every graph in the suite.  Adding a new benchmark is as simple as appending a dictionary with `"name"`, `"n"`, and `"edges"`.

---

### `src/qubo.py` — MVC QUBO Formulation

**The core idea:**  We want to encode MVC as a quadratic unconstrained binary optimisation (QUBO) problem so that the *ground state* of the resulting Ising Hamiltonian corresponds exactly to the minimum vertex cover.

**`build_mvc_qubo(n, edges, penalty)`**  
Constructs the QUBO matrix `Q` for:

```
C(x) = Σ_i x_i  +  P · Σ_{(i,j)∈E} (1 - x_i)(1 - x_j)
```

The first term minimises the number of selected vertices.  The second term is a *penalty* that adds `P` whenever an edge is uncovered.  **The critical insight:** if `P` is larger than the maximum vertex degree, then *no* invalid cover can have a lower cost than a valid one.  The function auto-computes `P = max_degree + 1` when not supplied, guaranteeing exactness.

The diagonal entries `Q[i,i]` become `1 - P·degree(i)` because each vertex `i` appears in `degree(i)` penalty terms.  The off-diagonal entries `Q[i,j]` become `P/2` for every edge `(i,j)`.

**`qubo_cost(bitstring, Q)`**  
Evaluates `x^T Q x` for a measured bitstring.  Uses little-endian indexing to match Qiskit's convention.

**`is_valid_cover(bitstring, edges)`**  
A simple sanity check: for every edge, at least one endpoint must be `1`.

**`cover_size(bitstring)`**  
Counts the Hamming weight — the number of vertices in the cover.

---

### `src/ising.py` — QUBO → Ising Mapping

**The core idea:**  QAOA circuits evolve under Pauli operators, not binary variables.  We must translate the QUBO matrix into an Ising Hamiltonian `H_P = Σ h_i Z_i + Σ J_{ij} Z_i Z_j`.

**`qubo_to_ising(Q)`**  
Substitutes `x_i = (1 - Z_i)/2` into the QUBO and collects like terms.  This is purely algebraic:
- Each diagonal `Q_ii` contributes a `Z_i` term and a constant.
- Each off-diagonal `Q_ij` contributes a `Z_i Z_j` term, two `Z_i`/`Z_j` terms, and a constant.

The function returns `(terms, constant)`.  The constant is irrelevant for optimisation (it shifts every energy equally) and is dropped when building the circuit.

**`ising_to_json(terms)`**  
Serialises the Ising terms to a JSON-friendly list.  Each entry records the qubit indices, the coefficient, and whether it is a single-qubit (`Z`) or two-qubit (`ZZ`) term.  This makes the output human-readable and easy to audit.

---

### `src/circuit.py` — QAOA Circuit Builder

**The core idea:**  Once we have the Ising Hamiltonian, we need a function that turns it into a concrete `QuantumCircuit`.  This is the bridge between mathematics and executable code.

**`build_qaoa_circuit(terms, gammas, betas, num_qubits)`**  
Builds a `p`-layer QAOA circuit where `p = len(gammas) = len(betas)`.

The circuit follows the standard ansatz:
1. Initialise all qubits in `|+⟩` with `H` gates.
2. For each layer `k = 1..p`:
   - **Problem unitary** `U(H_P, γ_k) = exp(-i γ_k H_P)`:
     - Single-qubit term `h_i Z_i` → `RZ(2·h_i·γ_k)` on qubit `i`
     - Two-qubit term `J_{ij} Z_i Z_j` → `CX(i,j)·RZ(2·J_{ij}·γ_k)·CX(i,j)`
   - **Mixer unitary** `U(H_M, β_k) = exp(-i β_k H_M)`:
     - Apply `RX(2·β_k)` on every qubit
3. Measure all qubits.

**Why the `2·coeff·γ` factor?**  Because Qiskit's `RZ(θ)` implements `exp(-i θ/2 · Z)`.  To get `exp(-i γ · c · Z)` we need `θ = 2·c·γ`.  The same logic applies to the two-qubit `ZZ` rotations.

---

### `src/exact.py` — Brute-Force Verification

**The core idea:**  For small graphs (`n ≤ 7`) we can enumerate all `2^n` bitstrings classically.  This gives us the *ground truth* against which we compare QAOA's approximate solution.

**`solve_exact(n, edges, Q)`**  
Loops over every possible bitstring, computes its QUBO cost, checks validity, and collects statistics.  Returns:
- `optimal_cost` — the lowest cost among valid covers
- `optimal_size` — the size of the minimum cover
- `optimal_covers` — all bitstrings achieving the optimum
- `num_valid_covers` — how many bitstrings are valid covers
- `all_results` — the top 16 bitstrings sorted by cost

This serves two purposes: (1) it proves the QUBO formulation is correct, and (2) it provides the denominator for the approximation ratio.

---

### `src/optimizer.py` — Classical Optimisation Loop

**The core idea:**  QAOA is a *variational* algorithm — the angles `γ, β` are not known analytically.  We treat the quantum computer as a black-box cost function and use a classical optimiser to minimise the expected QUBO cost.

**`optimize_qaoa(objective_fn, p, method, maxiter, shots_per_eval, random_restarts)`**  
Wraps `scipy.optimize.minimize` with multiple random restarts.

**Why random restarts?**  The QAOA cost landscape is non-convex and has many local minima.  A single initial guess can get stuck.  By running `RANDOM_RESTARTS` times and keeping the best result, we dramatically improve the probability of finding a good minimum.

**The callback function** records the cost after every iteration into a `history` list.  This list is later plotted as the convergence curve.

**Initial guess strategy:**  `γ` is sampled from `[0.1, 1.5]` and `β` from `[0.3, 1.2]`.  These ranges were chosen empirically — they avoid the trivial regions near 0 and π while staying in the basin of attraction for most small graphs.

---

### `src/simulator.py` — Execution & Analysis

**The core idea:**  After optimisation, we run the circuit one final time with the best angles and analyse the measurement statistics.

**`simulate_and_analyse(circuit, Q, edges, shots)`**  
Runs the circuit on `AerSimulator`, then computes:
- `expected_cost` — weighted average QUBO cost over all measured states
- `valid_probability` — fraction of shots that landed on valid covers
- `best_valid` — the lowest-cost valid state observed
- `top_8` — the eight most frequent bitstrings with their costs, validity, and sizes

This is richer than simply reporting "the most frequent state" because it tells us whether the distribution is concentrated on good solutions or spread across invalid states.

---

### `src/reporter.py` — Output Generation

**The core idea:**  Science is only reproducible if the artifacts are systematic and inspectable.  Every experiment produces the same set of files in the same structure.

**`save_json(data, path)`**  
Pretty-prints any dictionary to JSON with `indent=2`.  Handles NumPy arrays via `default=str`.

**`save_circuit_text(circuit, path)`**  
Saves the Qiskit text diagram with `fold=-1`.  This means the circuit is printed on a single line per qubit — no wrapping.  This is essential for inspecting gate sequences programmatically (e.g., with `grep`).

**`save_circuit_image(circuit, path)`**  
Renders the circuit as a PNG using Qiskit's Matplotlib backend.

**`plot_convergence(history, optimal_cost, path)`**  
Plots the optimiser's cost trajectory with a dashed line marking the true optimal cost.  This visual diagnostic tells you at a glance whether the optimiser got stuck or converged.

**`plot_distribution(results, path)`**  
Plots a histogram of the most frequent measured states.  Valid covers are coloured blue; invalid states are grey.  This immediately shows whether QAOA learned to respect the feasibility constraint.

---

### `main.py` — Benchmark Orchestrator

**The core idea:**  This is the *glue* that ties all the modules together.  It defines the experiment protocol, loops over every graph and every `p`, and generates cross-graph summary plots.

**`run_single_experiment(graph_def, p, out_dir)`**  
Executes the full pipeline for one `(graph, p)` pair:
1. Build QUBO → 2. Map to Ising → 3. Solve exactly → 4. Build circuit → 5. Optimise → 6. Simulate → 7. Save everything.

Each step is isolated and its intermediate results are saved.  If an experiment crashes, the others continue unaffected.

**`run_benchmark_suite()`**  
Creates the timestamped output directory, runs `run_single_experiment` for every graph in `BENCHMARK_GRAPHS` and every `p` in `PS`, then aggregates a `benchmark_summary.json` and generates summary plots.

**`generate_summary_plots(summary, base_dir)`**  
Creates two cross-graph comparison figures:
- **Scaling plot** — circuit depth and CNOT count vs graph name, comparing `p=1` vs `p=2`
- **Approximation ratio plot** — cost quality and valid-state probability vs graph name

**`generate_markdown_report(summary, base_dir)`**  
Writes a Markdown table summarising every experiment.  This is the fastest way to get an overview without opening JSON files.

---

## Experiment Output Reference

### Per-experiment files (`{graph}/p{p}/`)

| File | Contents |
|------|----------|
| `circuit.txt` | Qiskit text diagram (`fold=-1`), inspectable with any text editor |
| `circuit.png` | Matplotlib-rendered circuit image |
| `convergence.png` | Optimiser cost trajectory with optimal-cost reference line |
| `distribution.png` | Histogram of measured states (blue = valid, grey = invalid) |
| `landscape.png` | **p=1:** full 2D (γ, β) heatmap with optimizer path and red optimum dot. **p≥2:** 2D slice of (γ₁, β₁) plus 1D curvature slices for every parameter |
| `exact_solution.json` | Brute-force ground truth: optimal cost, size, and all optimal covers |
| `results.json` | Master record: metadata, graph info, QUBO/Ising coefficients, circuit stats, optimisation history, simulation counts, and metrics |

#### `results.json` schema

Below is a detailed reference for every top-level key inside `results.json`.

**`metadata`** — Experiment configuration
| Property | Meaning |
|---|---|
| `graph_name` | Identifier of the graph (e.g. `C5`, `K6`). |
| `p` | Number of QAOA layers. |
| `timestamp` | ISO-8601 time when the experiment finished. |
| `shots_per_eval` | Shots used for each quantum evaluation during optimisation. |
| `shots_final` | Shots used for the final verification simulation. |
| `optimizer` | Classical optimiser used (`COBYLA`, `SPSA`, etc.). |
| `maxiter` | Maximum iterations allowed per random restart. |
| `random_restarts` | How many random initial guesses were tried. |

**`graph`** — Problem instance
| Property | Meaning |
|---|---|
| `n_vertices` | Number of vertices (`n`). |
| `edges` | List of undirected edges `[u, v]`. |
| `num_edges` | Total edge count (`m`). |
| `density` | Graph density = `2m / (n(n-1))`. |

**`qubo`** — QUBO formulation
| Property | Meaning |
|---|---|
| `penalty` | Weight `P` applied to uncovered edges (`max_degree + 1`). |
| `matrix` | The symmetric QUBO matrix `Q`. |
| `ising_terms` | Pauli-Z representation of the problem Hamiltonian (`Z` and `ZZ` terms). |
| `constant_offset` | Global constant dropped from the Hamiltonian. |

**`circuit`** — Resource metrics
| Property | Meaning |
|---|---|
| `depth` | Circuit depth using dummy angles before optimisation. |
| `total_gates` | Total gate count. |
| `gate_breakdown` | Count of each gate type (`h`, `rz`, `cx`, `rx`, `measure`). |
| `two_qubit_count` | Number of CNOT (`cx`) gates. |
| `qubit_count` | Number of qubits (= `n_vertices`). |
| `num_parameters` | Total variational parameters = `2p`. |

**`optimization`** — Classical optimiser output
| Property | Meaning |
|---|---|
| `best_gammas` | Optimised problem-unitary angles `[γ₁, …, γ_p]`. |
| `best_betas` | Optimised mixer-unitary angles `[β₁, …, β_p]`. |
| `best_cost` | Lowest expected QUBO cost found by the optimiser. |
| `history` | List of expected costs recorded at each iteration. |
| `iterations_used` | Actual number of iterations in `history`. |
| `time_seconds` | Wall-clock time for optimisation. |
| `success` | Whether the optimiser finished without error. |

**`simulation`** — Final simulation with optimal angles
| Property | Meaning |
|---|---|
| `shots` | Number of shots in the final simulation. |
| `num_unique_states` | Number of distinct bitstrings measured. |
| `expected_cost` | Average QUBO cost over all measured shots. |
| `valid_probability` | Total probability that a measured state is a valid vertex cover. |
| `top_8` | The 8 most probable measured states. Each entry contains `bitstring`, `count`, `probability`, `cost`, `valid`, and `size`. |

**`metrics`** — Aggregated quality indicators
| Property | Meaning |
|---|---|
| `optimal_cost` | Exact minimum QUBO cost from brute-force enumeration. |
| `best_observed_cost` | Lowest QUBO cost among *valid* states actually measured. |
| `best_observed_size` | Vertex-cover size of that best observed state. |
| `best_observed_bitstring` | The bitstring achieving `best_observed_cost`. |
| `approximation_ratio` | `best_observed_cost / optimal_cost` (`1.0` = exact optimum found). |
| `success_probability` | Probability of measuring *any* optimal-cover state. |
| `valid_probability` | Same as `simulation.valid_probability`. |
| `expected_cost` | Same as `simulation.expected_cost` (higher precision). |

**`exact`** — Brute-force ground truth
| Property | Meaning |
|---|---|
| `optimal_cost` | Minimum possible QUBO cost. |
| `optimal_size` | Size of a minimum vertex cover. |
| `optimal_covers` | All bitstrings that achieve the optimal cost and are valid. |
| `num_valid_covers` | Total number of valid vertex covers for the graph. |

### Summary files (`experiments/run_*/`)

| File | Contents |
|------|----------|
| `run_config.json` | Hyperparameters used for this run |
| `benchmark_summary.json` | Flat list of every experiment's key metrics |
| `benchmark_table.md` | Human-readable Markdown table |
| `scaling_plot.png` | Depth and CNOT count across all graphs |
| `approximation_ratio.png` | Quality and validity across all graphs |

---

## Asymptotic Resource Analysis

This section derives the exact scaling laws for the QAOA circuit used in the benchmark.  All formulas are expressed in terms of the graph $G=(V,E)$ where $|V|$ is the number of vertices and $|E|$ is the number of edges.

### Qubit Count

Each binary variable $x_i \in \{0,1\}$ is encoded on one qubit.  Therefore the qubit requirement is trivially:

$$\boxed{\text{Qubits} = |V| = \Theta(|V|)}$$

There is no auxiliary qubit overhead in the standard QAOA ansatz.

### Gate Count

The Ising Hamiltonian $H_P$ contains exactly:
- $|V|$ single-qubit $Z_i$ terms (one per vertex)
- $|E|$ two-qubit $Z_i Z_j$ terms (one per edge)

For a circuit with $p$ QAOA layers:

| Resource | Exact count | Asymptotic |
|---|---|---|
| **CNOT gates** | $2p \cdot |E|$ | $\Theta(p \cdot |E|)$ |
| **Single-qubit gates** | $\|V\|$ (H init) $+ 2p \cdot \|V\|$ ($p$ layers of $Rz + Rx$) | $\Theta(p \cdot \|V\|)$ |
| **Total gates** | $\|V\| + 2p(\|V\| + \|E\|)$ | $\Theta(p \cdot (\|V\| + \|E\|))$ |

The factor of 2 on CNOTs comes from the decomposition $e^{-i\theta Z_i Z_j} = \text{CNOT}(i,j) \cdot Rz(2\theta) \cdot \text{CNOT}(i,j)$.

### Circuit Depth

Depth is the length of the longest path in the gate-dependency DAG.  The exact depth depends on how many gates can be executed in parallel.

**Current implementation (sequential edge ordering):**
- Single-qubit $Rz$ terms: all act on disjoint qubits → depth **1** per layer
- Two-qubit $ZZ$ terms: each edge introduces a 3-gate chain (CNOT–Rz–CNOT).  Because edges are processed sequentially, the per-layer depth scales with the number of edges.

From our benchmark data the empirical depth formulas are:

| Graph family | p=1 depth | p-layer depth |
|---|---|---|
| Complete graph $K_n$ | $\approx 6n - 5$ | $\Theta(p \cdot n)$ |
| Cycle $C_n$ | $\approx 3n + 1$ | $\Theta(p \cdot n)$ |
| Star $S_n$ | $\approx 3n + 1$ | $\Theta(p \cdot n)$ |
| Path $P_n$ | $\approx 3n + 1$ | $\Theta(p \cdot n)$ |

In all cases:
$$\boxed{\text{Depth (current)} = \Theta(p \cdot |V|)}$$

**Theoretical lower bound (optimal scheduling):**

By Vizing's theorem, the edges of any graph can be coloured with at most $\Delta + 1$ colours where $\Delta$ is the maximum degree.  All edges in one colour class are vertex-disjoint and therefore their $ZZ$ unitaries can be applied in parallel.  This reduces the per-layer depth from $O(|E|)$ to $O(\Delta)$:

$$\boxed{\text{Depth (optimal)} = O(p \cdot \Delta)}$$

For sparse graphs ($\Delta \ll |V|$) this is a dramatic improvement.  For example, on a cycle $C_n$ where $\Delta = 2$, optimal scheduling would give $O(p)$ depth instead of the empirical $\Theta(p \cdot n)$.

### Summary Table

| Resource | Scaling | Notes |
|---|---|---|
| Qubits | $\Theta(\|V\|)$ | One per vertex; no ancillas |
| CNOTs | $\Theta(p \cdot \|E\|)$ | 2 per edge per layer |
| Single-qubit gates | $\Theta(p \cdot \|V\|)$ | $H$ init + $p$ layers of $Rz + Rx$ |
| Depth (current) | $\Theta(p \cdot \|V\|)$ | Sequential edge processing |
| Depth (optimal) | $O(p \cdot \Delta)$ | With edge-colouring parallelism |
| Parameters | $2p$ | $p$ gammas + $p$ betas |

---

## Interpreting the Metrics

- **Approximation Ratio** = `best_observed_cost / optimal_cost`.  `1.0` means QAOA found the true minimum.  Values > 1.0 indicate sub-optimal solutions.
- **Valid Probability** = fraction of shots that measured a valid vertex cover.  High values mean the penalty term is working well; low values suggest the mixer is exploring too many invalid states.
- **Expected Cost** = average QUBO cost over the full distribution.  This is what the classical optimiser actually minimises.

---

## Extending the Suite

**Add a new graph:**  Edit `src/graphs.py` and append to `BENCHMARK_GRAPHS`:
```python
{"name": "MyGraph", "n": 5, "edges": [(0,1), (1,2), (2,3)]}
```

**Change the optimiser:**  Edit `main.py` and pass `method="SPSA"` or `method="Nelder-Mead"` to `optimize_qaoa()`.

**Test deeper circuits:**  Change `PS = [1, 2, 3]` in `main.py`.  Be aware that `p=3` on `K7` creates a very deep circuit.

**Run on real hardware:**  Replace `AerSimulator()` in `src/optimizer.py` and `src/simulator.py` with an IBM Quantum backend instance.  Increase `shots_per_eval` to at least 4096 to combat noise.
