from qiskit import QuantumCircuit
import matplotlib.pyplot as plt

# Initialize a circuit with 3 qubits (to show multi-qubit gates)
qc = QuantumCircuit(3)

# --- 1. Basic Single-Qubit Pauli Gates ---
qc.x(0) # Not gate (Flips |0> to |1>)
qc.y(0) # Pauli-Y
qc.z(0) # Pauli-Z (Phase flip)

# --- 2. Supervision & Phase Gates ---
qc.h(1) # Hadamard (Creates superposition)
qc.s(1) # S gate (Phase gate, sqrt of Z)
qc.t(1) # T gate (45 degree phase)

# --- 3. Rotation Gates (using 3.14159/2 as an example angle)
import numpy as np
qc.rx(np.pi/2, 2)
qc.ry(np.pi/2, 2)
qc.rz(np.pi/2, 2)

qc.barrier() # Visual separator

# --- 4. Multi-Qubit Gates (Entanglement) ---
qc.cx(0, 1)   # CNOT (Control: 0, Target: 1)
qc.cy(0, 1)   # Controlled-Y
qc.cz(0, 1)   # Controlled-Z
qc.swap(1, 2) # Swaps states of qubit 1 and 2
qc.ccx(0, 1, 2) # Toffoli gate (Controlled-Controlled-NOT)
qc.draw(output='mpl')
plt.savefig('quantum_gates.jpg', bbox_inches='tight', dpi=300)
plt.close()