import time
from qiskit_aer import AerSimulator
from qiskit_ibm_runtime import SamplerV2 as Sampler
from qiskit.transpiler import generate_preset_pass_manager
from qiskit.quantum_info import Statevector
from .models import SolverConfig, SimulationResults
from .circuit_builder import VertexCoverPenaltyCircuitBuilder
from .utils import is_valid_cover, get_popcount, get_weight_sum
from reporting.exporter import ResultExporter

class VertexCoverSolverEngine:
    def __init__(self, config: SolverConfig):
        self.config = config

    def solve(self, dry_run=False) -> SimulationResults:
        builder = VertexCoverPenaltyCircuitBuilder(self.config)
        circuit = builder.build()
        
        backend = self.config.backend if self.config.backend else AerSimulator()
        sampler = Sampler(mode=backend)
        pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
        transpiled_circuit = pm.run(circuit)

        if dry_run:
            ResultExporter.save_artifacts(self.config, SimulationResults(
                counts={}, good_states={}, all_edge_covered_states={}, pop_count_less_than_pivot_states={}, elapsed_time=0,
                circuit_depth=circuit.depth(), transpiled_depth=transpiled_circuit.depth(),
                qubits_used=len(circuit.qubits), operations=circuit.count_ops()
            ), circuit, transpiled_circuit, statevector=None)
            return SimulationResults(
                counts={}, good_states={}, all_edge_covered_states={}, pop_count_less_than_pivot_states={}, elapsed_time=0,
                circuit_depth=circuit.depth(), transpiled_depth=transpiled_circuit.depth(),
                qubits_used=len(circuit.qubits), operations=circuit.count_ops()
            )
        
        start_time = time.time()
        job = sampler.run([(transpiled_circuit, [], self.config.shots)])
        result = job.result()[0]
        counts = result.data[self.config.classical_register_name].get_counts()
        elapsed_time = time.time() - start_time

        quasi_probabilities = {s: c / self.config.shots for s, c in counts.items()}
        
        theoretical_probabilities = None
        filtered_statevector = None
        sv = None

        if self.config.calculate_theoretical_probabilities or self.config.calculate_statevector:
            circuit_no_meas = circuit.copy()
            circuit_no_meas.remove_final_measurements()
            sv = Statevector(circuit_no_meas)
            
            if self.config.calculate_theoretical_probabilities:
                prob_dict = sv.probabilities_dict()
                theoretical_probabilities = {s: p for s, p in prob_dict.items() if p > 1e-10}
            
            if self.config.calculate_statevector:
                sv_dict = sv.to_dict()
                if theoretical_probabilities:
                    filtered_statevector = {s: sv_dict[s] for s in theoretical_probabilities}
                else:
                    prob_dict = sv.probabilities_dict()
                    significant_probs = {s: p for s, p in prob_dict.items() if p > 1e-10}
                    filtered_statevector = {s: sv_dict[s] for s in significant_probs}

        good_states = None
        if self.config.calculate_good_states:
            good_states = {
                s: c for s, c in counts.items()
                if is_valid_cover(s, self.config.edges, self.config.num_vertices)
                and get_weight_sum(s, self.config.vertex_weights) < self.config.pivot_number
            }
        all_edge_covered_states = None
        if self.config.calculate_good_states:
            all_edge_covered_states = {
                s: c for s, c in counts.items()
                if is_valid_cover(s, self.config.edges, self.config.num_vertices)
            }

        pop_count_less_than_pivot_states = None
        if self.config.calculate_good_states:
            pop_count_less_than_pivot_states = {
                s: c for s, c in counts.items()
                if get_popcount(s) < self.config.pivot_number
            }

        res = SimulationResults(
            counts=counts, 
            good_states=good_states, 
            all_edge_covered_states=all_edge_covered_states, 
            pop_count_less_than_pivot_states=pop_count_less_than_pivot_states,
            quasi_probabilities=quasi_probabilities,
            theoretical_probabilities=theoretical_probabilities,
            statevector=filtered_statevector,
            elapsed_time=elapsed_time,
            circuit_depth=circuit.depth(), transpiled_depth=transpiled_circuit.depth(),
            qubits_used=len(circuit.qubits), operations=circuit.count_ops()
        )
        
        ResultExporter.save_artifacts(self.config, res, circuit, transpiled_circuit, statevector=sv)
        return res