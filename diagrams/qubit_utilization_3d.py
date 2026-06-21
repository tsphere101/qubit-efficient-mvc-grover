import numpy as np
import pandas as pd
import plotly.graph_objects as go
import math
from scipy.special import comb 

# 1. Configuration
k = 2  # Parameter for Cherif et al. equation

n_values = []
m_values = []
q_purposed_values = []
q_cherif_values = []
q_wang_values = []

# 2. Generate the data
for n in range(1, 19):
    m_limit = n * (n - 1) // 2
    for m in range(n, m_limit + 1):
        # Purposed Equation
        q_purp = n + m + 2 * math.ceil(math.log2(n + 1)) + 4
        
        # Cherif et al. Equation: n + m + (n choose k+1) + 1
        q_cherif = n + m + comb(n, k + 1) + 1
        
        # Wang et al. Equation: n + m + (n+1)(n+2)/2 + 1
        q_wang = n + m + ((n + 1) * (n + 2) / 2) + 1
        
        n_values.append(n)
        m_values.append(m)
        q_purposed_values.append(q_purp)
        q_cherif_values.append(q_cherif)
        q_wang_values.append(q_wang)

# 3. Create a DataFrame
df = pd.DataFrame({
    'n': n_values,
    'm': m_values,
    'purposed': q_purposed_values,
    'Cherif': q_cherif_values,
    'Wang': q_wang_values
})

# 4. Create the interactive 3D Scatter Plot
fig = go.Figure()

# Trace 1: Purposed
fig.add_trace(go.Scatter3d(
    x=df['n'], y=df['m'], z=df['purposed'],
    mode='markers',
    name='purposed',
    marker=dict(size=4, color='blue', opacity=0.7),
    text=[f"n:{n}, m:{m}<br>Q:{q:.1f}" for n, m, q in zip(df['n'], df['m'], df['purposed'])],
    hoverinfo='text'
))

# Trace 2: Cherif et al.
fig.add_trace(go.Scatter3d(
    x=df['n'], y=df['m'], z=df['Cherif'],
    mode='markers',
    name='Cherif et al.',
    marker=dict(size=4, color='red', opacity=0.7),
    text=[f"n:{n}, m:{m}<br>Q:{q:.1f}" for n, m, q in zip(df['n'], df['m'], df['Cherif'])],
    hoverinfo='text'
))

# Trace 3: Wang et al.
fig.add_trace(go.Scatter3d(
    x=df['n'], y=df['m'], z=df['Wang'],
    mode='markers',
    name='Wang et al.',
    marker=dict(size=4, color='green', opacity=0.7),
    text=[f"n:{n}, m:{m}<br>Q:{q:.1f}" for n, m, q in zip(df['n'], df['m'], df['Wang'])],
    hoverinfo='text'
))

# 5. Update layout with Equal Axis Spacing
fig.update_layout(
    title='3D Comparison: Purposed vs. Cherif et al. vs. Wang et al.',
    scene=dict(
        xaxis_title='n (Nodes)',
        yaxis_title='m (Edges)',
        zaxis_title='Q_total',
        # 'cube' ensures all axes are rendered with equal visual length
        aspectmode='cube', 
        camera=dict(eye=dict(x=1.6, y=1.6, z=1.2))
    ),
    margin=dict(l=0, r=0, b=0, t=50),
    legend=dict(yanchor="top", y=0.9, xanchor="left", x=0.1),
    width=1000,
    height=800
)

fig.show()