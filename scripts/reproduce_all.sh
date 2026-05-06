#!/bin/bash
# ============================================================================
# Full reproduction script for "Qubit-Efficient Quantum Circuit for the 
# Minimum Vertex Cover Problem using Grover's Algorithm"
#
# Usage: bash scripts/reproduce_all.sh
#
# This runs ALL experiments end-to-end. Estimated time: several hours.
# Use make <target> for selective reproduction (see Makefile).
# ============================================================================
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
cd "$REPO_DIR"

echo "=========================================="
echo "  Setting up environment..."
echo "=========================================="
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo ""
echo "=========================================="
echo "  1. Scaling charts (Fig 1, Fig 6)"
echo "=========================================="
python manuscript/generate_scaling_charts.py

echo ""
echo "=========================================="
echo "  2. Arithmetic solver benchmarks"
echo "=========================================="
cd src/mvc-solver-1.3.0
python main.py --graph-n 3 --shots 1024 --grover-iteration 1
python main.py --graph-n 4 --shots 1024 --grover-iteration 1
python main.py --graph-n 5 --shots 1024 --grover-iteration 1
python main.py --graph-n 6 --shots 1024 --grover-iteration 1 --dry-run
python main.py --graph-n 7 --shots 1024 --grover-iteration 1 --dry-run
cd "$REPO_DIR"

echo ""
echo "=========================================="
echo "  3. Dicke-state solver benchmarks"
echo "=========================================="
cd src/mvc-solver-1.4.0
python main.py --graph-n 3 --shots 1024
python main.py --graph-n 4 --shots 1024
python main.py --graph-n 5 --shots 1024
python main.py --graph-n 6 --shots 1024
cd "$REPO_DIR"

echo ""
echo "=========================================="
echo "  4. Weighted solver benchmarks"
echo "=========================================="
cd src/mvc-solver-1.5.0
python main.py --vertex-weights "1,2,3" --shots 1024 --skip-k
python main.py --graph-edges "0,1;1,2;2,3" --vertex-weights "1,2,3,4" --shots 1024
cd "$REPO_DIR"

echo ""
echo "=========================================="
echo "  5. QAOA benchmarks (full: 15 graphs × p=1,2,3)"
echo "     This step takes several hours."
echo "=========================================="
cd src/mvc_qaoa
python main.py
cd "$REPO_DIR"

echo ""
echo "=========================================="
echo "  6. QAOA vs Grover comparison figures"
echo "=========================================="
cd src/mvc_qaoa/experiments
python generate_success_comparison.py
python generate_transpiled_comparison.py
python generate_comparison.py
cd "$REPO_DIR"

echo ""
echo "=========================================="
echo "  7. Compiling paper"
echo "=========================================="
cd manuscript
latexmk -pdf -pdflatex='pdflatex -interaction=nonstopmode' tqe.tex
cd "$REPO_DIR"

echo ""
echo "=========================================="
echo "  All done! Paper at manuscript/tqe.pdf"
echo "=========================================="
