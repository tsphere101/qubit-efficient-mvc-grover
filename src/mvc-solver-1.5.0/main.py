#!/usr/bin/env python3
import os, argparse, json
from datetime import datetime
from qiskit.visualization import plot_histogram
import matplotlib.pyplot as plt

from solver.models import SolverConfig
from solver.engine import VertexCoverSolverEngine
from solver.utils import complete_graph_edges, get_weight_sum

def find_min_cover(edges, shots, vertex_weights=None, dynamic_threshold = True, verbose = True, base_output_dir = None, barrier = True, grover_iterations = None, dry_run = False, skip_k = False, **kwargs):
    nodes = set()
    for u, v in edges: nodes.add(u); nodes.add(v)
    num_vertices = max(nodes) + 1 if nodes else 0
    
    if vertex_weights is None:
        vertex_weights = [1] * num_vertices

    min_size, best_states = None, None
    total_weight_sum = sum(vertex_weights)
    pivot_that_choose_every_vertex = total_weight_sum + 1
    
    pivot = pivot_that_choose_every_vertex
    while pivot > 0:
        if verbose: print(f"Testing pivot={pivot}...")
        pivot_dir = os.path.join(base_output_dir, f"pivot_{pivot}") if base_output_dir else None

        config = SolverConfig(edges=edges, pivot_number=pivot, shots=shots, 
                              vertex_weights=vertex_weights,
                              calculate_good_states=True, output_dir=pivot_dir, barrier=barrier,
                              calculate_statevector=kwargs.get('calculate_statevector', False),
                              calculate_theoretical_probabilities=kwargs.get('calculate_theoretical_probabilities', False))
        if grover_iterations is not None:
             config.grover_iterations = grover_iterations
        res = VertexCoverSolverEngine(config).solve(dry_run=dry_run)
        
        total_good = sum(res.good_states.values()) if res.good_states else 0
        if verbose: print(f"  Good shots: {total_good}/{shots} ({(total_good/shots)*100:.2f}%)")
        
        threshold = 1/(2**num_vertices) if dynamic_threshold else 0.03
        if total_good > shots * threshold:
            min_size, best_states = pivot - 1, res.good_states
            
            if skip_k and res.good_states:
                # Find the minimum weight among measured valid states
                measured_min_w = min(get_weight_sum(s, vertex_weights) for s in res.good_states.keys())
                if measured_min_w < pivot - 1:
                    if verbose: print(f"  Skip-K: Found solution with weight {measured_min_w}, skipping to pivot {measured_min_w + 1}")
                    min_size = measured_min_w
                    pivot = measured_min_w + 1
                    continue
            pivot -= 1
        else: break
    return min_size, best_states

def main():
    parser = argparse.ArgumentParser(description="Quantum Minimum Vertex Cover Solver")
    parser.add_argument("--n-range", type=int, nargs=2)
    parser.add_argument("--graph-n", type=int)
    parser.add_argument("--graph-edges", type=str)
    parser.add_argument("--shots", type=int, default=1024)
    parser.add_argument("--plot", action="store_true")
    parser.add_argument("--no-barrier", action="store_true", help="Disable barriers in the circuit for better optimization")
    parser.add_argument("--grover-iteration", type=int, default=None, help="Number of Grover iterations to perform")
    parser.add_argument("--dry-run", action="store_true", help="Run the circuit compilation without executing it on the simulator")
    parser.add_argument("--include-statevector", action="store_true", help="Include statevector in results (expensive)")
    parser.add_argument("--include-theoretical", action="store_true", help="Include theoretical probabilities in results (expensive)")
    parser.add_argument("--vertex-weights", type=str, help="Comma-separated vertex weights (e.g., '1,2,1')")
    parser.add_argument("--skip-k", action="store_true", help="Skip pivots if a smaller solution is found during measurement")
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join("outputs", f"run_{timestamp}")
    os.makedirs(run_dir, exist_ok=True)

    summary = []
    if args.graph_n: tasks = [(f"K_{args.graph_n}", complete_graph_edges(args.graph_n))]
    elif args.n_range: tasks = [(f"K_{n}", complete_graph_edges(n)) for n in range(args.n_range[0], args.n_range[1] + 1)]
    elif args.graph_edges: 
        edges = [tuple(map(int, edge.split(","))) for edge in args.graph_edges.split(";")]
        tasks = [("graph", edges)]
    else: tasks = [(f"K_{3}", complete_graph_edges(3))] # default to 3-vertex graph

    vertex_weights = [int(w) for w in args.vertex_weights.split(",")] if args.vertex_weights else None
    for label, edges in tasks:
        print(f"\n--- Solving for {label} ---")
        g_dir = os.path.join(run_dir, str(label))
        min_size, best = find_min_cover(edges, args.shots, vertex_weights, True, True, g_dir, not args.no_barrier, args.grover_iteration, args.dry_run, 
                                        args.skip_k, 
                                        calculate_statevector=args.include_statevector, 
                                        calculate_theoretical_probabilities=args.include_theoretical)
        print(f"Result: {min_size}")
        
        top_state = max(best, key=best.get) if best else None
        summary.append({"task": label, "min_size": min_size, "top_state": top_state})

    with open(os.path.join(run_dir, "run_summary.json"), "w") as f:
        print(f"Saving summary to {os.path.join(run_dir, "run_summary.json")}")
        json.dump(summary, f, indent=4)

    if args.plot and best:
        plot_histogram(best); plt.show()

if __name__ == "__main__":
    main()