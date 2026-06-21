import numpy as np
import matplotlib.pyplot as plt
import math
import os
from scipy.special import comb


STYLE_CONFIG = {
    'Cherif et al. (2024)':  {'color': 'red',    'marker': 's', 'linestyle': '--', 'linewidth': 2},
    'Wang et al. (2023)':    {'color': 'green',  'marker': '^', 'linestyle': '-.', 'linewidth': 2},
    'Jiang & Yan (2023)':    {'color': 'orange', 'marker': 'd', 'linestyle': ':',  'linewidth': 2},
    'Dicke-state':           {'color': 'blue',   'marker': 'o', 'linestyle': '-',  'linewidth': 2},
    'Arithmetic-based':      {'color': 'purple', 'marker': '*', 'linestyle': '-',  'linewidth': 2},
}


def generate_qubit_scaling_chart():
    k = 2

    n_values = []
    v130_values = []
    v140_values = []
    q_cherif_values = []
    q_wang_values = []
    q_jiang_values = []

    for n in range(1, 19):
        m = n * (n - 1) // 2

        v130 = n + 2 * math.ceil(math.log2(n + (n + 1) * m)) + 3
        v140 = n + m + 2

        q_cherif = n + m + comb(n, k + 1) + 1
        q_wang = n + m + ((n + 1) * (n + 2) / 2) + 1
        q_jiang = n + math.ceil(math.log2(n)) + 2 * m + 1

        n_values.append(n)
        v130_values.append(v130)
        v140_values.append(v140)
        q_cherif_values.append(q_cherif)
        q_wang_values.append(q_wang)
        q_jiang_values.append(q_jiang)

    plt.figure(figsize=(10, 6))

    plt.plot(n_values, q_cherif_values, label='Cherif et al. (2024)', **STYLE_CONFIG['Cherif et al. (2024)'])
    plt.plot(n_values, q_wang_values, label='Wang et al. (2023)', **STYLE_CONFIG['Wang et al. (2023)'])
    plt.plot(n_values, q_jiang_values, label='Jiang & Yan (2023)', **STYLE_CONFIG['Jiang & Yan (2023)'])
    plt.plot(n_values, v140_values, label='Dicke-state', **STYLE_CONFIG['Dicke-state'])
    plt.plot(n_values, v130_values, label='Arithmetic-based', **STYLE_CONFIG['Arithmetic-based'])

    plt.title('Qubit Utilization Comparison on Fully Connected Graphs', fontsize=16)
    plt.xlabel('Number of Vertices (n)', fontsize=14)
    plt.ylabel('Total Qubits ($Q_{total}$)', fontsize=14)
    plt.legend(title='Method', fontsize=12)
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.xticks(np.arange(min(n_values), max(n_values)+1, 1.0))
    plt.tight_layout()

    output_file = "chart_qubit_scaling_comparison.png"
    plt.savefig(output_file, dpi=300)
    print(f"Saved: {output_file}")
    plt.close()


def generate_depth_scaling_chart():
    n_values = np.arange(4, 26)

    cherif_depths = []
    wang_depths = []
    jiang_depths = []
    dicke_depths = []
    arithmetic_depths = []

    for n in n_values:
        m = n * (n - 1) // 2
        k = n // 2

        cherif = 12*m + 4*math.comb(n, k+1) + n
        cherif_depths.append(cherif)

        wang = 4*m + 8*(n**2) + 14*n + 5
        wang_depths.append(wang)

        t_jiang = np.ceil(np.log2(n)) if n > 0 else 1
        jiang = 2*n*t_jiang + 12*m + n
        jiang_depths.append(jiang)

        d_gdsp = 2*n*(k**2) - (k**3)/3 - 5*(k**2) + 8*n*k - 14*k/3 - 15*n + 22
        dicke = 2*d_gdsp + 10*n + 28*m + 11
        dicke_depths.append(dicke)

        t_arith = np.ceil(np.log2((n+1)*(m+1)))
        lp_arith = np.ceil(np.log2(n+1))
        arithmetic = 0.5*n*t_arith*(t_arith+1) + 0.5*m*lp_arith*t_arith*(t_arith+1) + 6*t_arith + 4*n + 5
        arithmetic_depths.append(arithmetic)

    plt.figure(figsize=(10, 6))

    plt.plot(n_values, cherif_depths, label='Cherif et al. (2024)', **STYLE_CONFIG['Cherif et al. (2024)'])
    plt.plot(n_values, wang_depths, label='Wang et al. (2023)', **STYLE_CONFIG['Wang et al. (2023)'])
    plt.plot(n_values, jiang_depths, label='Jiang & Yan (2023)', **STYLE_CONFIG['Jiang & Yan (2023)'])
    plt.plot(n_values, dicke_depths, label='Dicke-state', **STYLE_CONFIG['Dicke-state'])
    plt.plot(n_values, arithmetic_depths, label='Arithmetic-based', **STYLE_CONFIG['Arithmetic-based'])

    plt.yscale('log')
    plt.title('Circuit Depth Comparison per Grover Iteration ($D_{iter}$)', fontsize=16)
    plt.xlabel('Number of Vertices (n)', fontsize=14)
    plt.ylabel('Gate Count per Grover Iteration ($D_{iter}$)', fontsize=14)
    plt.legend(title='Method', fontsize=12)
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.tight_layout()

    output_file = "circuit_depth_comparison.png"
    plt.savefig(output_file, dpi=300)
    print(f"Saved: {output_file}")
    plt.close()


def main():
    generate_qubit_scaling_chart()
    generate_depth_scaling_chart()
    print("Done. Both charts generated.")


if __name__ == "__main__":
    main()
