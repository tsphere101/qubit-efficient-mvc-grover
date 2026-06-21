import numpy as np
import matplotlib.pyplot as plt
import math

# Define the range of n (number of vertices)
# Stopping at n=25 because Cherif's combinatorial term becomes too massive
n_values = np.arange(4, 26)

# Lists to store the plotted values
cherif_depths = []
wang_depths = []
jiang_depths = []
dicke_depths = []
arithmetic_depths = []

for n in n_values:
    # Worst-case scenario: Complete graph K_n
    m = n * (n - 1) // 2
    # Combinatorial worst-case/mid-point
    k = n // 2  
    
    # 1. Cherif et al. (2024)
    # Assumes O(n) approx n
    cherif = 12*m + 4*math.comb(n, k+1) + n
    cherif_depths.append(cherif)
    
    # 2. Wang et al. (2023)
    wang = 4*m + 8*(n**2) + 14*n + 5
    wang_depths.append(wang)
    
    # 3. Jiang & Yan (2023)
    # Assumes D_cnt(t) = ceil(log2(n)) and O(n) approx n
    t_jiang = np.ceil(np.log2(n)) if n > 0 else 1
    jiang = 2*n*t_jiang + 12*m + n
    jiang_depths.append(jiang)
    
    # 4. Dicke-State Architecture
    d_gdsp = 2*n*(k**2) - (k**3)/3 - 5*(k**2) + 8*n*k - 14*k/3 - 15*n + 22
    dicke = 2*d_gdsp + 10*n + 28*m + 11
    dicke_depths.append(dicke)
    
    # 5. Arithmetic-Based Architecture
    t_arith = np.ceil(np.log2((n+1)*(m+1)))
    lp_arith = np.ceil(np.log2(n+1))
    arithmetic = 0.5*n*t_arith*(t_arith+1) + 0.5*m*lp_arith*t_arith*(t_arith+1) + 6*t_arith + 4*n + 5
    arithmetic_depths.append(arithmetic)

# Plotting the data
plt.figure(figsize=(10, 7), dpi=300)

plt.plot(n_values, cherif_depths, marker='o', label="1. Cherif et al.", linestyle='--')
plt.plot(n_values, wang_depths, marker='s', label="2. Wang et al.")
plt.plot(n_values, jiang_depths, marker='^', label="3. Jiang & Yan")
plt.plot(n_values, dicke_depths, marker='d', label="4. Dicke-State Architecture")
plt.plot(n_values, arithmetic_depths, marker='x', label="5. Arithmetic-Based Architecture")

# Chart Configurations
plt.yscale('log') # Log scale because of Cherif's binomial blowup
plt.xlabel('Number of Vertices ($n$) for Complete Graph $K_n$', fontsize=12)
plt.ylabel('Gate Count per Grover Iteration ($D_{iter}$)', fontsize=12)
plt.title('Circuit Depth Comparison per Iteration ($D_{iter}$) vs Graph Size', fontsize=14, fontweight='bold')
plt.grid(True, which="both", ls="--", alpha=0.5)
plt.legend(fontsize=11)
plt.tight_layout()

# Save or show the plot
plt.show()
