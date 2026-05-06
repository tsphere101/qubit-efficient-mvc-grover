#!/bin/bash
# Quick verification script — runs a single graph per architecture
set -e
cd "$(dirname "$0")/.."
source .venv/bin/activate 2>/dev/null || { echo "Run 'make env' first"; exit 1; }

echo "=== Arithmetic (K3) ==="
cd src/mvc-solver-1.3.0
python main.py --graph-n 3 --shots 256 --grover-iteration 1 2>&1 | grep -E "best_pivot|success|qubits|depth"
cd ../..

echo ""
echo "=== Dicke-state (K3) ==="
cd src/mvc-solver-1.4.0
python main.py --graph-n 3 --shots 256 2>&1 | grep -E "best_pivot|success|qubits|depth"
cd ../..

echo ""
echo "=== Weighted (K3 w=1,2,3) ==="
cd src/mvc-solver-1.5.0
python main.py --vertex-weights "1,2,3" --shots 256 2>&1 | grep -E "best_pivot|success|qubits|depth"
cd ../..

echo ""
echo "=== QAOA dry-run (K3-K5, p=1) ==="
python scripts/dry_run_qaoa.py

echo ""
echo "=== All checks passed ==="
