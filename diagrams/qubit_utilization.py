import numpy as np
import matplotlib.pyplot as plt
import math
import os
from scipy.special import comb

# 1. Configuration
k = 2  # Parameter for Cherif et al. equation

n_values = []
m_values = []

# Version lists
v130_values = []
v140_values = []

# Competitor lists
q_cherif_values = []
q_wang_values = []
q_jiang_values = []

# 2. Generate the data
for n in range(1, 19):
    # Fully connected graph: m = n * (n - 1) / 2
    m = n * (n - 1) // 2
    
    # --- Formulations ---
    # v1.3.0: Arithmetic-based
    v130 = n + 2 * math.ceil(math.log2(n + (n + 1) * m)) + 3
    
    # v1.4.0: GDSP
    v140 = n + m + 2

    # --- Competitors ---
    # Cherif et al. (2024)
    q_cherif = n + m + comb(n, k + 1) + 1
    
    # Wang et al. (2023)
    q_wang = n + m + ((n + 1) * (n + 2) / 2) + 1
    
    # Jiang and Yan (2023)
    q_jiang = n + math.ceil(math.log2(n)) + 2 * m + 1
    
    # Store data
    n_values.append(n)
    v130_values.append(v130)
    v140_values.append(v140)
    q_cherif_values.append(q_cherif)
    q_wang_values.append(q_wang)
    q_jiang_values.append(q_jiang)

# 3. Create the 2D Line Chart
plt.figure(figsize=(10, 6))

# --- PLOTTING ORDER DETERMINES LEGEND ORDER ---

# 1. Cherif et al. (2024)
plt.plot(n_values, q_cherif_values, label='Cherif et al. (2024)', color='red', marker='s', linestyle='--', linewidth=2)

# 2. Wang et al. (2023)
plt.plot(n_values, q_wang_values, label='Wang et al. (2023)', color='green', marker='^', linestyle='-.', linewidth=2)

# 3. Jiang and Yan (2023)
plt.plot(n_values, q_jiang_values, label='Jiang and Yan (2023)', color='orange', marker='d', linestyle=':', linewidth=2)

# 4. Dicke-state (formerly v1.4.0)
plt.plot(n_values, v140_values, label='Dicke-state', color='blue', marker='o', linestyle='-', linewidth=2)

# 5. Arithmetic-based (formerly v1.3.0)
plt.plot(n_values, v130_values, label='Arithmetic-based', color='purple', marker='*', linestyle='-', linewidth=2)

# --- Final Chart Styling ---

plt.title('Qubit Utilization Comparison on Fully Connected Graphs', fontsize=16)
plt.xlabel('Number of Vertices (n)', fontsize=14)
plt.ylabel('Total Qubits ($Q_{total}$)', fontsize=14)
plt.legend(title='Method', fontsize=12)

# Add grid
plt.grid(True, linestyle=':', alpha=0.6)

# Set integer ticks for x-axis
plt.xticks(np.arange(min(n_values), max(n_values)+1, 1.0))

# Save and show
plt.tight_layout()
output_file = "chart_qubit_scaling_comparison.jpg"
plt.savefig(output_file, dpi=300)
print(f"Chart saved as {output_file}")
plt.show()