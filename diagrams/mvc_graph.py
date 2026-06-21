import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.lines import Line2D

# Create a graph with nodes 0, 1, 2, 3, 4, 5
G = nx.Graph()
edges = [(0, 1), (0, 2), (1, 2), (2, 3), (3, 4), (4, 5)]
G.add_edges_from(edges)

# Minimum Vertex Cover for this graph
# Picking {0, 2, 4} covers all edges:
# (0,1) -> 0, (0,2) -> 0/2, (1,2) -> 2, (2,3) -> 2, (3,4) -> 4, (4,5) -> 4
mvc_nodes = {0, 2, 4}

# Define layout
pos = nx.shell_layout(G)

# Node colors: Highlight MVC nodes
node_colors = ['red' if node in mvc_nodes else 'skyblue' for node in G.nodes()]

# Edge colors
edge_colors = ['black' for _ in G.edges()]

# Figure size and high resolution
plt.figure(figsize=(12, 9))

# Draw the graph
nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=1200, edgecolors='black')
nx.draw_networkx_edges(G, pos, edge_color=edge_colors, width=2.5)
nx.draw_networkx_labels(G, pos, font_size=14, font_family='sans-serif', font_weight='bold')

# Create a legend with updated labels
legend_elements = [
    Line2D([0], [0], marker='o', color='w', label='Vertex in subset',
           markerfacecolor='red', markersize=12, markeredgecolor='black'),
    Line2D([0], [0], marker='o', color='w', label='Vertex not in subset',
           markerfacecolor='skyblue', markersize=12, markeredgecolor='black')
]
plt.legend(handles=legend_elements, loc='upper right', fontsize=12)

# Updated Title
plt.title("Minimum Vertex Cover", fontsize=18)
plt.axis('off')

# Save the plot
plt.savefig('mvc_graph.jpg', bbox_inches='tight', dpi=300)
plt.close()