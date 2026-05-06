# Qubit-Efficient MVC Grover — Makefile
# =====================================
# Targets:
#   all         — Run all experiments end-to-end
#   paper      — Compile LaTeX paper
#   qaoa       — Run QAOA comparison benchmarks
#   arithmetic — Run arithmetic solver benchmarks
#   dicke      — Run Dicke-state solver benchmarks
#   weighted   — Run weighted arithmetic solver benchmarks
#   figures    — Generate scaling comparison figures
#   clean      — Remove generated artifacts
#   env        — Set up Python virtual environment

SHELL := /bin/bash
.PHONY: all paper qaoa arithmetic dicke weighted figures clean env

# Default Python
PYTHON := python3
VENV   := .venv
ACTIVATE := $(VENV)/bin/activate

# ------------------------------------------------------------------
# Environment
# ------------------------------------------------------------------
env: requirements.txt
	$(PYTHON) -m venv $(VENV)
	. $(ACTIVATE) && pip install --upgrade pip
	. $(ACTIVATE) && pip install -r requirements.txt

# ------------------------------------------------------------------
# All experiments (sequential)
# ------------------------------------------------------------------
all: env arithmetic dicke weighted qaoa figures paper

# ------------------------------------------------------------------
# Paper compilation
# ------------------------------------------------------------------
paper:
	@echo "Compiling manuscript/tqe.tex..."
	cd manuscript && latexmk -pdf -pdflatex="pdflatex -interaction=nonstopmode" tqe.tex 2>&1 | tail -5

paper-clean:
	cd manuscript && latexmk -C

# ------------------------------------------------------------------
# QAOA comparison benchmarks (15 graphs × p=1,2,3)
# ------------------------------------------------------------------
qaoa: env
	@echo "Running QAOA benchmarks..."
	. $(ACTIVATE) && cd src/mvc_qaoa && python main.py \
		--shots 4096 --maxiter 80 --restarts 5 \
		--p-list 1 2 3
	@echo "Generating QAOA vs Grover comparison figures..."
	. $(ACTIVATE) && cd src/mvc_qaoa/experiments && \
		python generate_comparison.py && \
		python generate_success_comparison.py && \
		python generate_transpiled_comparison.py

# ------------------------------------------------------------------
# Arithmetic solver benchmarks (K3–K7)
# ------------------------------------------------------------------
arithmetic: env
	@echo "Running Arithmetic architecture benchmarks..."
	. $(ACTIVATE) && cd src/mvc-solver-1.3.0 && \
		for n in 3 4 5 6 7; do \
			echo "  K$$n..."; \
			python main.py --graph-n $$n --shots 1024 --grover-iteration 1; \
		done

# ------------------------------------------------------------------
# Dicke-state solver benchmarks (K3–K6; K7 requires >30 qubits)
# ------------------------------------------------------------------
dicke: env
	@echo "Running Dicke-state architecture benchmarks..."
	. $(ACTIVATE) && cd src/mvc-solver-1.4.0 && \
		for n in 3 4 5 6; do \
			echo "  K$$n..."; \
			python main.py --graph-n $$n --shots 1024; \
		done

# ------------------------------------------------------------------
# Weighted arithmetic solver benchmarks
# ------------------------------------------------------------------
weighted: env
	@echo "Running Weighted arithmetic architecture benchmarks..."
	. $(ACTIVATE) && cd src/mvc-solver-1.5.0 && \
		python main.py --vertex-weights "1,2,3" --shots 1024 --skip-k && \
		python main.py --graph-edges "0,1;1,2;2,3" --vertex-weights "1,2,3,4" --shots 1024 --skip-k

# ------------------------------------------------------------------
# Scaling figures
# ------------------------------------------------------------------
figures: env
	@echo "Generating qubit and depth scaling charts..."
	. $(ACTIVATE) && cd manuscript && python generate_scaling_charts.py
	@echo "Generating depth comparison chart..."
	. $(ACTIVATE) && cd manuscript && python circuit_depth_comparison.py

# ------------------------------------------------------------------
# Clean
# ------------------------------------------------------------------
clean:
	rm -rf $(VENV)
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "outputs" -exec rm -rf {} + 2>/dev/null || true
	cd manuscript && latexmk -C 2>/dev/null || true
	@echo "Cleaned."

# ------------------------------------------------------------------
# Verify installation
# ------------------------------------------------------------------
check:
	. $(ACTIVATE) && python -c "import qiskit; print('Qiskit', qiskit.__version__)"
	. $(ACTIVATE) && python -c "import networkx; print('NetworkX', networkx.__version__)"
	. $(ACTIVATE) && python -c "import matplotlib; print('Matplotlib', matplotlib.__version__)"
