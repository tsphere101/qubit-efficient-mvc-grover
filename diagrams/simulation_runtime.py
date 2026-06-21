import matplotlib.pyplot as plt
import numpy as np

# Data from benchmark results
graph_instances = ['K3', 'K4', 'K5', 'K6']
total_qubits = [12, 18, 23, 29]
execution_times = [0.005, 0.051, 1.219, 238.345]

# Create X-axis labels combining Instance and Qubit count
x_labels = [f"{g}\n({q} qubits)" for g, q in zip(graph_instances, total_qubits)]

# Initialize the plot
plt.figure(figsize=(10, 6))
plt.grid(True, which="both", ls="-", alpha=0.5)

# Plotting the line with markers
plt.plot(graph_instances, execution_times, marker='o', markersize=8, 
         linestyle='-', linewidth=2.5, color='#d62728', label='Execution Time')

# Set Y-axis to logarithmic scale (CRITICAL for this data)
plt.yscale('log')

# Adding Titles and Labels
plt.title('Simulation Runtime', fontsize=14, fontweight='bold', pad=20)
plt.xlabel('Graph Instance ($K_n$) and Total Qubits', fontsize=12)
plt.ylabel('Execution Time (Seconds) [Log Scale]', fontsize=12)

# Customize X-axis tick labels
plt.xticks(graph_instances, x_labels)

# Annotation for the "Simulation Ceiling"
plt.annotate('Simulation Ceiling\n(~200x jump)', 
             xy=('K6', 238.345), 
             xytext=('K4', 100),
             fontsize=11,
             fontweight='bold',
             color='black',
             arrowprops=dict(arrowstyle='->', lw=1.5, color='black'))

# Add data labels above the points
for i, time in enumerate(execution_times):
    plt.text(graph_instances[i], time * 1.2, f"{time:.3f}s", 
             ha='center', va='bottom', fontsize=10, fontweight='semibold')

# Adjust layout to prevent clipping
plt.tight_layout()

# Save to file
plt.savefig('simulation_runtime_scaling.png', dpi=300)
print("Chart generated and saved as 'simulation_runtime_scaling.png'")

# Display the plot
plt.show()