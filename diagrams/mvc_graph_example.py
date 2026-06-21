import networkx as nx
import matplotlib.pyplot as plt

# 1. Use the Petersen Graph
G = nx.petersen_graph()

# 2. A verified Minimum Vertex Cover (Size 6)
# This set covers every edge, including the inner star connections.
mvc = {0, 1, 3, 6, 7, 8, 9} 

# --- 3. COVERAGE CHECK LOGIC ---
uncovered_edges = []
for u, v in G.edges():
    if u not in mvc and v not in mvc:
        uncovered_edges.append((u, v))

if not uncovered_edges:
    print("✅ Success: All edges are covered!")
else:
    print(f"❌ Warning: {len(uncovered_edges)} edges are NOT covered!")
    print(f"Uncovered edges: {uncovered_edges}")

# 4. Setup the visualization
plt.figure(figsize=(10, 8))
pos = nx.shell_layout(G, nlist=[range(5, 10), range(5)], rotate=0)

# Draw edges
nx.draw_networkx_edges(G, pos, width=2, edge_color='#bdc3c7')

# Highlight uncovered edges in yellow/bold if they exist
if uncovered_edges:
    nx.draw_networkx_edges(G, pos, edgelist=uncovered_edges, width=5, edge_color='#f1c40f')

# Draw non-selected nodes
nx.draw_networkx_nodes(G, pos, 
                       nodelist=set(G.nodes()) - mvc, 
                       node_color='#ecf0f1', 
                       node_size=800, 
                       edgecolors='#7f8c8d', 
                       linewidths=2)

# Draw the Vertex Cover nodes
nx.draw_networkx_nodes(G, pos, 
                       nodelist=mvc, 
                       node_color='#e74c3c', 
                       node_size=1000, 
                       edgecolors='#c0392b', 
                       linewidths=2)

nx.draw_networkx_labels(G, pos, font_size=12, font_weight='bold')

# plt.title(f"Minimum Vertex Cover (Size: {len(mvc)})", fontsize=15)
plt.axis('off')

# Save and Show
plt.savefig("mvc-graph-example.png", dpi=300, bbox_inches='tight')