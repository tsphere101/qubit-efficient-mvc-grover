import math
import unittest
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from qiskit.circuit.library import RYGate
from generalized_dicke_state import create_generalized_dicke_state

class TestGeneralizedDickeState(unittest.TestCase):
    """Unit tests for the Generalized Dicke State preparation circuit."""

    def verify_state(self, n, k):
        """Helper to simulate circuit and verify weight distribution."""
        qc = create_generalized_dicke_state(n, k)
        state = Statevector.from_instruction(qc)
        probabilities = state.probabilities_dict()
        # Filter out numerical noise
        probabilities = {k: v for k, v in probabilities.items() if v > 1e-10}
        
        # Calculate expected probability for any valid state
        # Total valid states = Sum of combinations nCr for r from 0 to k
        num_valid_basis_states = sum(math.comb(n, r) for r in range(k + 1))
        expected_prob = 1.0 / num_valid_basis_states

        # 1. Check that all observed states have weight <= k
        for basis_binary, prob in probabilities.items():
            weight = basis_binary.count('1')
            self.assertLessEqual(weight, k, 
                f"State |{basis_binary}> has weight {weight} which is > k={k} (prob={prob:.4e})")
            
            # 2. Check that the probability is uniform (within numerical tolerance)
            self.assertAlmostEqual(prob, expected_prob, places=6,
                msg=f"State |{basis_binary}> has incorrect probability.")

        # 3. Check that we haven't missed any valid states
        self.assertEqual(len(probabilities), num_valid_basis_states,
            f"Expected {num_valid_basis_states} basis states, but found {len(probabilities)}")

    def test_edge_cases(self):
        """Test minimal qubits and k=0 boundaries."""
        # k=0 should result in |0...0> with probability 1.0
        qc = create_generalized_dicke_state(3, 0)
        self.assertAlmostEqual(Statevector.from_instruction(qc).probabilities_dict()['000'], 1.0)
        
        # n=k should result in a uniform superposition of all 2^n states
        self.verify_state(3, 3)

    def test_small_circuits(self):
        """Iterate through a range of n and k values."""
        for n in range(1, 10):
            for k in range(1, n + 1):
                with self.subTest(n=n, k=k):
                    self.verify_state(n, k)

    def test_invalid_input(self):
        """Ensure the function raises error for k > n."""
        with self.assertRaises(ValueError):
            create_generalized_dicke_state(2, 5)

if __name__ == "__main__":
    unittest.main()