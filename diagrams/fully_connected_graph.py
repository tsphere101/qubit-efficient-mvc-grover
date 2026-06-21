import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.lines import Line2D

Ks = [3,4,5]
for k in Ks:
    G = nx.complete_graph(k)
    plt.figure(figsize=(6, 6))
    pos = nx.circular_layout(G)
    nx.draw(G, pos, with_labels=True, node_color='skyblue', node_size=800, font_size=12, font_weight='bold')
    # Use axes expansion to ensure nodes aren't clipped
    dataset_scaling_factor = 1.2
    x_values, y_values = zip(*pos.values())
    x_max, x_min = max(x_values), min(x_values)
    y_max, y_min = max(y_values), min(y_values)
    x_margin = (x_max - x_min) * 0.2
    y_margin = (y_max - y_min) * 0.2
    plt.xlim(x_min - x_margin, x_max + x_margin)
    plt.ylim(y_min - y_margin, y_max + y_margin)
    
    plt.title(f"Fully Connected Graph K{k}", fontsize=16, pad=20)
    plt.axis('on') # Turn axis on temporarily to check, but usually we want off for graphs.
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(f"K{k}.png", bbox_inches='tight')
    plt.close()
