# Qubit-Efficient MVC Grover

Quantum circuit architectures for solving the Minimum Vertex Cover (MVC) problem using Grover's search algorithm.

## Directory Structure

```
.
├── manuscript/                     # LaTeX paper + figures
│   ├── tqe.tex                   # Paper source
│   ├── figures/                  # All figures (57 PNG)
│   ├── exported-items.bib        # Bibliography
│   └── generate_scaling_charts.py
├── src/
│   ├── mvc-solver-1.3.0/         # Arithmetic architecture
│   ├── mvc-solver-1.4.0/         # Dicke-state architecture
│   ├── mvc-solver-1.5.0/         # Weighted arithmetic architecture
│   ├── mvc_qaoa/                 # QAOA comparison benchmarks
│   └── prod/                     # Experiment archives
├── experiment-results/           # Raw CSV results
├── scripts/
│   ├── reproduce_all.sh          # Full end-to-end reproduction
│   ├── quick_verify.sh           # Quick verification
│   └── dry_run_qaoa.py           # QAOA circuit build check
├── Makefile                      # Build automation
└── requirements.txt              # Python dependencies
```

## Quick Start

```bash
# Set up environment
make env

# Run experiments selectively:
make arithmetic   # Arithmetic solver (K3-K7)
make dicke        # Dicke-state solver (K3-K6)
make weighted     # Weighted solver benchmarks
make qaoa         # QAOA comparison (15 graphs × p=1,2,3)

# Generate scaling figures
make figures

# Full reproduction (hours)
make all
```

## Architectures

| Version | Architecture | Oracle Strategy | Initial State | Edge Scaling |
|---------|-------------|----------------|---------------|-------------|
| v1.3.0 | Arithmetic | Penalty adder + Cuccaro comparator | Uniform | $O(\log m)$ |
| v1.4.0 | Dicke-state | Edge-check (MCX per edge) | $|D_{\le k}^n\rangle$ | $O(m)$ |
| v1.5.0 | Weighted | Weighted penalty + Cuccaro comparator | Uniform | $O(\log m)$ |

## Experiments

All experiments use Qiskit AerSimulator with configurable shots and Grover iterations.

### Arithmetic (v1.3.0)
```bash
cd src/mvc-solver-1.3.0
python main.py --graph-n 5 --shots 1024 --grover-iteration 1
python main.py --graph-n 5 --shots 2048 --grover-iteration 3
```

### Dicke-state (v1.4.0)
```bash
cd src/mvc-solver-1.4.0
python main.py --graph-n 5 --shots 1024
```

### Weighted (v1.5.0)
```bash
cd src/mvc-solver-1.5.0
python main.py --vertex-weights "1,2,3" --shots 1024 --skip-k
python main.py --graph-edges "0,1;1,2;2,3" --vertex-weights "1,2,3,4" --shots 1024
```

### QAOA Baseline
```bash
cd src/mvc_qaoa
python main.py  # Runs all 15 graphs × p=1,2,3
```

### Quick verification
```bash
bash scripts/quick_verify.sh
```
