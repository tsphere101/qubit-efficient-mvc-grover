import os, json, matplotlib.pyplot as plt
from dataclasses import asdict
import networkx as nx
from qiskit.visualization import plot_histogram

class ResultExporter:
    @staticmethod
    def save_artifacts(config, results, circuit, transpiled_circuit, statevector=None):
        if not config.output_dir: return
        os.makedirs(config.output_dir, exist_ok=True)

        # 1. Save Config
        with open(os.path.join(config.output_dir, "config.json"), "w") as f:
            clean_config = {k: v for k, v in asdict(config).items() if k != 'backend'}
            json.dump(clean_config, f, indent=4)
            ResultExporter.console_log(f"Config saved to {os.path.join(config.output_dir, 'config.json')}")

        # 2. Save Results
        class QuantumJSONEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, complex):
                    return {'real': obj.real, 'imag': obj.imag}
                import numpy as np
                if isinstance(obj, (np.complex128, np.complex64)):
                    return {'real': float(obj.real), 'imag': float(obj.imag)}
                if isinstance(obj, (np.float64, np.float32)):
                    return float(obj)
                if isinstance(obj, (np.int64, np.int32)):
                    return int(obj)
                return super().default(obj)

        with open(os.path.join(config.output_dir, "results.json"), "w") as f:
            json.dump(asdict(results), f, indent=4, cls=QuantumJSONEncoder)
            ResultExporter.console_log(f"Results saved to {os.path.join(config.output_dir, 'results.json')}")

        # 3. Save Problem Graph
        plt.figure(figsize=(8, 6))
        G = nx.Graph()
        G.add_edges_from(config.edges)
        
        # Add all nodes even if they don't have edges
        for i in range(config.num_vertices):
            G.add_node(i)
            
        labels = {i: f"{i}\n(w={config.vertex_weights[i]})" for i in G.nodes() if i < len(config.vertex_weights)}
        nx.draw(G, labels=labels, with_labels=True, node_color='skyblue', node_size=1200, font_weight='bold')
        plt.title(f"Problem Graph (Pivot={config.pivot_number})")
        plt.savefig(os.path.join(config.output_dir, "graph.png")); plt.close()
        ResultExporter.console_log(f"Problem graph saved to {os.path.join(config.output_dir, 'graph.png')}")

        # 4. Save Measured Distribution
        if (results.counts):
            plt.figure(figsize=(10, 6))
            plot_histogram(results.counts)
            plt.title(f"Measured Distribution (Pivot={config.pivot_number})")
            plt.tight_layout()
            plt.savefig(os.path.join(config.output_dir, "distribution.png")); plt.close()
            ResultExporter.console_log(f"Measured distribution saved to {os.path.join(config.output_dir, 'distribution.png')}")

        # 4b. Save Quasi Probability Distribution
        if (results.quasi_probabilities):
            plt.figure(figsize=(10, 6))
            plot_histogram(results.quasi_probabilities)
            plt.title(f"Quasi Probability Distribution (Pivot={config.pivot_number})")
            plt.tight_layout()
            plt.savefig(os.path.join(config.output_dir, "distribution_quasi.png")); plt.close()
            ResultExporter.console_log(f"Quasi distribution saved to {os.path.join(config.output_dir, 'distribution_quasi.png')}")

        # 4c. Save Theoretical Probability Distribution
        if (results.theoretical_probabilities):
            plt.figure(figsize=(10, 6))
            plot_histogram(results.theoretical_probabilities)
            plt.title(f"Theoretical Probability Distribution (Pivot={config.pivot_number})")
            plt.tight_layout()
            plt.savefig(os.path.join(config.output_dir, "distribution_theoretical.png")); plt.close()
            ResultExporter.console_log(f"Theoretical distribution saved to {os.path.join(config.output_dir, 'distribution_theoretical.png')}")

        # 5. Save Circuit Text
        with open(os.path.join(config.output_dir, "circuit.txt"), "w") as f:
            f.write(str(circuit.draw(output='text', fold=-1)))
            ResultExporter.console_log(f"Circuit saved to {os.path.join(config.output_dir, 'circuit.txt')}")
        
        try:
            circuit.draw(output='mpl', fold=-1).savefig(os.path.join(config.output_dir, "circuit.png"))
            transpiled_circuit.draw(output='mpl', fold=-1).savefig(os.path.join(config.output_dir, "transpiled_circuit.png"))
            ResultExporter.console_log(f"Circuit saved to {os.path.join(config.output_dir, 'circuit.png')}")
            ResultExporter.console_log(f"Transpiled circuit saved to {os.path.join(config.output_dir, 'transpiled_circuit.png')}")
        except: ResultExporter.console_log("Failed to save circuit images")
    @staticmethod
    def console_log(s: str):
        print(s)