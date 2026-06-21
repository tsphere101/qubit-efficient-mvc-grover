# Qubit-Efficient MVC Grover — Makefile
# =====================================
# Targets:
#   all          — Run all experiments end-to-end
#   paper        — Compile LaTeX paper
#   qaoa         — Run QAOA comparison benchmarks
#   arithmetic   — Run arithmetic solver benchmarks
#   dicke        — Run Dicke-state solver benchmarks
#   weighted     — Run weighted arithmetic solver benchmarks
#   figures      — Generate all thesis figures
#   experiments  — Run thesis experiments with provenance manifests
#   provenance   — Generate PROVENANCE.md from manifests
#   clean        — Remove generated artifacts
#   env          — Set up Python virtual environment

SHELL := /bin/bash
.PHONY: all paper qaoa arithmetic dicke weighted figures experiments provenance clean env check

# Default Python
PYTHON := python3
VENV   := .venv
ACTIVATE := $(VENV)/bin/activate

# Thesis figures directory (relative path)
THESIS_FIG := ../overleaf/thesis-final-latex-v1/Figures/manuscript-images

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
# Figures — generate all thesis figures from code
# ------------------------------------------------------------------
figures: env
	@echo "Generating all thesis figures..."
	. $(ACTIVATE) && python diagrams/bloch_sphere.py
	. $(ACTIVATE) && python diagrams/quantum_gates.py
	. $(ACTIVATE) && python diagrams/mvc_graph.py
	. $(ACTIVATE) && python diagrams/mvc_graph_example.py
	. $(ACTIVATE) && python diagrams/gate_decomposition.py
	. $(ACTIVATE) && python diagrams/qubit_utilization.py
	. $(ACTIVATE) && python diagrams/qubit_utilization_3d.py
	. $(ACTIVATE) && python diagrams/simulation_runtime.py
	. $(ACTIVATE) && python diagrams/circuit_depth_comparison.py
	. $(ACTIVATE) && python diagrams/generate_scaling_charts.py
	. $(ACTIVATE) && python diagrams/fully_connected_graph.py
	. $(ACTIVATE) && python diagrams/box_circuit_generator.py
	. $(ACTIVATE) && python diagrams/cuccaro_comparator.py
	. $(ACTIVATE) && python diagrams/grover_reflection.py
	. $(ACTIVATE) && python diagrams/grovers_circuit.py
	@echo "Copying figures to thesis directory..."
	@mkdir -p $(THESIS_FIG)
	cp *.png *.jpg $(THESIS_FIG)/ 2>/dev/null || true
	@echo "Done."

# ------------------------------------------------------------------
# Experiments — run thesis experiments with provenance
# ------------------------------------------------------------------
experiments: env
	@echo "Running thesis experiments with provenance manifests..."
	. $(ACTIVATE) && python experiments/run_all.py --all

# ------------------------------------------------------------------
# Provenance — generate PROVENANCE.md from manifests
# ------------------------------------------------------------------
provenance: env
	@echo "Generating PROVENANCE.md..."
	. $(ACTIVATE) && python experiments/generate_provenance_map.py

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
