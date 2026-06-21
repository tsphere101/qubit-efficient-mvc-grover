import matplotlib.pyplot as plt
import numpy as np

# Updated Data from JSON
labels = ['K3', 'K4', 'K5', 'K6']
gate_data = {
    'X': [41, 62, 85, 111],
    'H': [18, 25, 28, 31],
    'CX': [18, 26, 26, 26],
    'CCX': [20, 36, 52, 72],
    'CP': [16, 36, 42, 48]
}

x = np.arange(len(labels))  # label locations
width = 0.15  # width of bars

fig, ax = plt.subplots(figsize=(12, 7))

# Plot bars for each gate type
rects1 = ax.bar(x - 2*width, gate_data['X'], width, label='X', color='#1f77b4')
rects2 = ax.bar(x - width, gate_data['H'], width, label='H', color='#ff7f0e')
rects3 = ax.bar(x, gate_data['CX'], width, label='CX', color='#2ca02c')
rects4 = ax.bar(x + width, gate_data['CCX'], width, label='CCX', color='#d62728')
rects5 = ax.bar(x + 2*width, gate_data['CP'], width, label='CP', color='#9467bd')

# Add labels and titles
ax.set_ylabel('Gate Count', fontsize=12, fontweight='bold')
ax.set_title('Quantum Gate Composition by Graph Size (K3-K6)', fontsize=14, fontweight='bold', pad=20)
ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=11, fontweight='bold')
ax.legend(title="Gate Types", fontsize=10)

ax.grid(axis='y', linestyle='--', alpha=0.7)

# Add text labels on top of bars
def autolabel(rects):
    for rect in rects:
        height = rect.get_height()
        ax.annotate('{}'.format(height),
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=9)

autolabel(rects1)
autolabel(rects2)
autolabel(rects3)
autolabel(rects4)
autolabel(rects5)

plt.tight_layout()
plt.savefig('gate_composition_k3_k6.png', dpi=300)
plt.show()