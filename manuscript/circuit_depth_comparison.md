## 1. Cherif et al. (2024): A simplified quantum approach using Grover's algorithm

For a graph with $n$ vertices and $m$ edges, the gate count per Grover iteration relies heavily on the required vertex cover size $k$. The gate count is:

$$D_{iter} = \underbrace{12m}_{\text{OR gates for edge cover (fwd+rev)}} + \underbrace{4\binom{n}{k+1}}_{\text{Size constraint check (fwd+rev)}} + \underbrace{O(n)}_{\text{comparator + diffuser + kickback}}$$

Where:

- **$k$**: The target size of the vertex cover subset being checked.
- **$\binom{n}{k+1}$**: The number of subsets evaluated to penalize subsets larger than $k$.
- **$G$**: Number of Grover iterations.

**Asymptotic notation per iteration:**

$$D_{iter} = O\!\big( m + \textstyle\binom{n}{k+1} \big)$$

**Total circuit depth:**

$$D_{total}(n, m, k, G) = O(n) + G \cdot D_{iter}$$

**Variable definitions:**
| Symbol | Name | Formula |
|--------|------|---------|
| $n$ | Number of vertices | Input parameter |
| $m$ | Number of edges | Input parameter |
| $k$ | Target vertex cover size | Input parameter |
| $G$ | Grover iterations | $\approx \frac{\pi}{4}\sqrt{\frac{2^n}{N_{valid}}}$ |

**Scaling examples (Assuming $k = \lfloor n/2 \rfloor$ for worst-case combinatorics):**
| Graph | $n$ | $m$ | $k$ | $D_{iter}$ (asymptotic) |
|-------|-----|-----|-----|------------------------|
| $K_4$ | 4 | 6 | 2 | $O(m + \binom{n}{k+1})$ |
| $K_8$ | 8 | 28 | 4 | $O(m + \binom{n}{k+1})$ |
| $K_{10}$ | 10 | 45 | 5 | $O(m + \binom{n}{k+1})$ |

> **Note:** The dominant term $4\binom{n}{k+1}$ introduces an exponential hardware scaling factor relative to the combination size. While edge checking is highly efficient ($O(m)$), the subset-size penalty causes severe depth blowup for large $n$.

---

## 2. Wang et al. (2023): Quantum speedup for solving the MVCP

For a graph with $n$ vertices and $m$ edges, this paper provides an exact polynomial gate count formula for their logic-gate-based screening and counting architecture:

$$D_{iter} = \underbrace{4m + 8n^2 + 10n + 3}_{\text{Oracle screening \& counting (fwd+rev)}} + \underbrace{4n + 2}_{\text{diffuser \& kickback}} = 4m + 8n^2 + 14n + 5$$

Where:

- **$8n^2$**: Dominated by the double-loop CCNOT gates required for subset size counting ($O(n^2)$ complexity).
- **$4m$**: Gates required for the multi-controlled edge-coverage verification.
- **$G$**: Number of Grover iterations.

**Asymptotic notation per iteration:**

$$D_{iter} = O\!\big( n^2 \big)$$

_(Since $m \le \frac{n(n-1)}{2}$, the $n^2$ term is strictly dominant over $m$.)_

**Total circuit depth:**

$$D_{total}(n, m, G) = O(n) + G \cdot D_{iter} = O(n^2 \sqrt{2^n})$$

**Variable definitions:**
| Symbol | Name | Formula |
|--------|------|---------|
| $n$ | Number of vertices | Input parameter |
| $m$ | Number of edges | Input parameter |
| $G$ | Grover iterations | $\approx \frac{\pi}{4}\sqrt{\frac{2^n}{N_{valid}}}$ |

**Scaling examples:**
| Graph | $n$ | $m$ | $D_{iter}$ (Exact count formula) | $D_{iter}$ (asymptotic) |
|-------|-----|-----|----------------------------------|-------------------------|
| $K_4$ | 4 | 6 | $4(6) + 8(16) + 14(4) + 5 = 213$ | $O(n^2)$ |
| $K_8$ | 8 | 28 | $4(28) + 8(64) + 14(8) + 5 = 741$ | $O(n^2)$ |
| $K_{10}$ | 10 | 45 | $4(45) + 8(100) + 14(10) + 5 = 1125$ | $O(n^2)$ |

> **Note:** This architecture fully polynomializes the oracle depth (avoiding exponential combination checks) by utilizing dynamic CCNOT-based quantum counting. It scales smoothly up to large graphs, bottlenecked primarily by the $O(n^2)$ counting loop.

---

## 3. Jiang & Yan (2023): Novel Quantum Circuit Designs for the Oracle

For a graph with $n$ vertices and $m$ edges, the gate count per Grover iteration relies on their improved "quantum counter" and "quantum semaphore" designs:

$$D_{iter} = \underbrace{2 \cdot n \cdot D_{cnt}(t)}_{\text{Improved counter (fwd+rev)}} + \underbrace{12m}_{\text{Semaphores (fwd+rev)}} + \underbrace{O(n)}_{\text{comparator + diffuser + kickback}}$$

Where:

- **$t = \lceil \log_2(n) \rceil$**: Counting qubit bit width.
- **$D_{cnt}(t)$**: The depth of their optimized quantum counter per increment ($O(t)$). Their improved counter saves $2t-2$ X-gates and reduces depth by $t$ per increment compared to standard designs.
- **$12m$**: Each of the $m$ edges requires 2 semaphores. Each semaphore uses 3 gates (2 CX + 1 X). Forward and reverse operations: $2 \times (2 \times 3) = 12$ gates per edge.
- **$G$**: Number of Grover iterations.

**Asymptotic notation per iteration:**

$$D_{iter} = O\!\big( n \cdot \log n + m \big)$$

**Total circuit depth:**

$$D_{total}(n, m, G) = O(n) + G \cdot D_{iter} = O\Big((n \log n + m) \sqrt{2^n}\Big)$$

**Variable definitions:**
| Symbol | Name | Formula |
|--------|------|---------|
| $n$ | Number of vertices | Input parameter |
| $m$ | Number of edges | Input parameter |
| $t$ | Counting bit width | $\lceil \log_2(n) \rceil$ |
| $G$ | Grover iterations | $\approx \frac{\pi}{4}\sqrt{\frac{2^n}{N_{valid}}}$ |

**Scaling examples:**
| Graph | $n$ | $m$ | $t$ | $D_{iter}$ (asymptotic) |
|-------|-----|-----|-----|------------------------|
| $K_4$ | 4 | 6 | 2 | $O(n \log n + m)$ |
| $K_8$ | 8 | 28 | 3 | $O(n \log n + m)$ |
| $K_{10}$ | 10 | 45 | 4 | $O(n \log n + m)$ |

> **Note:** By switching to a logarithmic counting register (reducing size-check overhead from $O(n^2)$ to $O(n \log n)$) and implementing a flat $O(m)$ semaphore setup for edges, this paper provides the most asymptotically efficient oracle depth of the three.

---

# Our Architectures

---

## 4. Dicke-State Architecture

For a graph with $n$ vertices and $m$ edges, the gate count per Grover iteration is:

$$D_{iter} = \underbrace{2 \cdot D_{GDSP}}_{\text{diffuser (fwd+rev)}} + \underbrace{8n + 28m + 8}_{\text{oracle (fwd+rev) + kickback}} + \underbrace{2n + 3}_{\text{diffuser reflection}}$$

Where $D_{GDSP}$ is the Generalized Dicke State Preparation gate count (from Narisada et al. 2023, Algorithm 2):

$$D_{GDSP}(n, k) = 2nk^2 - \frac{k^3}{3} - 5k^2 + 8nk - \frac{14k}{3} - 15n + 22$$

**Asymptotic notation:**

$$D_{GDSP}(n, k) = O(nk^2)$$

$$D_{iter} = O(nk^2 + m)$$

**Total circuit depth:**

$$D_{total}(n, m, k, G) = O(nk^2) + G \cdot O(nk^2 + m)$$

**Variable definitions:**
| Symbol | Name | Formula |
|--------|------|---------|
| $n$ | Number of vertices | Input parameter |
| $m$ | Number of edges | Input parameter |
| $k$ | Dicke state weight threshold | Pivot value ($k = w$ in the algorithm) |
| $D_{GDSP}(n,k)$ | GDSP gate count | $2nk^2 - \frac{k^3}{3} + O(nk + k^2 + n)$ |
| $G$ | Grover iterations | $\approx \frac{\pi}{4}\sqrt{\frac{2^n}{\binom{n}{\leq k}}}$ |

**Scaling examples:**
| Graph | $n$ | $m$ | $k$ | $D_{GDSP}$ | $D_{iter}$ (dominant) |
|-------|-----|-----|-----|------------|----------------------|
| $K_4$ | 4 | 6 | 2 | 52 | $O(nk^2)$ |
| $K_8$ | 8 | 28 | 4 | 432 | $O(nk^2)$ |
| $K_{10}$ | 10 | 45 | 5 | 920 | $O(nk^2)$ |

> **Note:** The Dicke State Preparation dominates the circuit depth ($O(nk^2)$), while the oracle scales only linearly with edges ($O(m)$). This makes the Dicke-state architecture particularly efficient when $k \ll n$ (i.e., when searching for small vertex covers). The search space reduction from $2^n$ to $\sum_{i=0}^{k}\binom{n}{i}$ also reduces Grover iterations significantly.

---

## 5. Arithmetic-Based Architecture

For a graph with $n$ vertices and $m$ edges, the gate count per Grover iteration is:

$$D_{iter} = \underbrace{\frac{n \cdot t(t+1)}{2}}_{\text{popcount (fwd+rev)}} + \underbrace{\frac{m \cdot l_p \cdot t(t+1)}{2}}_{\text{penalty adder (fwd+rev)}} + \underbrace{6t + 4n + 5}_{\text{comparator + diffuser + kickback}}$$

Where:
- **$t = \lceil \log_2((n+1)(m+1)) \rceil$**: Binary counter bit width
- **$l_p = \lceil \log_2(n+1) \rceil$**: Penalty bit width
- **$G$**: Number of Grover iterations

**Asymptotic notation:**

$$D_{iter} = O\!\big( m \cdot \log n \cdot \log^2(nm) \big)$$

**Total circuit depth:**

$$D_{total}(n, m, G) = O(n) + G \cdot D_{iter}$$

**Variable definitions:**
| Symbol | Name | Formula |
|--------|------|---------|
| $n$ | Number of vertices | Input parameter |
| $m$ | Number of edges | Input parameter |
| $t$ | Counter bit width | $\lceil \log_2((n+1)(m+1)) \rceil$ |
| $l_p$ | Penalty bit width | $\lceil \log_2(n+1) \rceil$ |
| $G$ | Grover iterations | $\approx \frac{\pi}{4}\sqrt{\frac{2^n}{N_{valid}}}$ |

**Scaling examples:**
| Graph | $n$ | $m$ | $t$ | $D_{iter}$ (asymptotic) |
|-------|-----|-----|-----|------------------------|
| $K_4$ | 4 | 6 | 6 | $O(m \cdot \log n \cdot \log^2(nm))$ |
| $K_8$ | 8 | 28 | 8 | $O(m \cdot \log n \cdot \log^2(nm))$ |
| $K_{10}$ | 10 | 45 | 9 | $O(m \cdot \log n \cdot \log^2(nm))$ |

> **Note:** The dominant term $\frac{m \cdot l_p \cdot t(t+1)}{2}$ scales with both the number of edges and the counter bit width, making this architecture most efficient for sparse graphs. The edge validation overhead scales as $O(\log m)$ instead of $O(m)$ ancilla qubits, trading increased circuit depth for reduced qubit count.

---

## 6. Weighted Arithmetic Architecture

For a graph with $n$ vertices and $m$ edges, the gate count per Grover iteration is:

$$D_{iter} = \underbrace{\frac{n \cdot t(t+1)}{2}}_{\text{weight sum (fwd+rev)}} + \underbrace{\frac{2m \cdot p \cdot t(t+1)}{2}}_{\text{penalty adder (fwd+rev)}} + \underbrace{6t + 4n + 5}_{\text{comparator + diffuser + kickback}}$$

Where:
- **$W = \sum_{i=0}^{n-1} w_i$**: Total weight of all vertices
- **$P = W + 1$**: Penalty amount (ensures invalid covers exceed the pivot)
- **$t = \lceil \log_2(W + m \cdot P) \rceil$**: Binary counter bit width
- **$p = \lceil \log_2(P) \rceil$**: Penalty bit width
- **$G$**: Number of Grover iterations

**Asymptotic notation:**

$$D_{iter} = O\!\big( (n + m \cdot \log W) \cdot \log^2(nm) \big)$$

For **unit weights** ($W = n$, $p = \lceil \log_2(n+1) \rceil$):

$$D_{iter} = O\!\big( m \cdot \log n \cdot \log^2(nm) \big)$$

**Total circuit depth:**

$$D_{total}(n, m, G) = O(n) + G \cdot D_{iter}$$

**Variable definitions:**
| Symbol | Name | Formula |
|--------|------|---------|
| $n$ | Number of vertices | Input parameter |
| $m$ | Number of edges | Input parameter |
| $W$ | Total vertex weight | $\sum w_i$ |
| $P$ | Penalty amount | $W + 1$ |
| $t$ | Counter bit width | $\lceil \log_2(W + m \cdot P) \rceil$ |
| $p$ | Penalty bit width | $\lceil \log_2(P) \rceil$ |
| $G$ | Grover iterations | $\approx \frac{\pi}{4}\sqrt{\frac{2^n}{N_{valid}}}$ |

**Scaling examples (unit weights):**
| Graph | $n$ | $m$ | $t$ | $p$ | $D_{iter}$ (asymptotic) |
|-------|-----|-----|-----|-----|------------------------|
| $K_4$ | 4 | 6 | 7 | 3 | $O(m \cdot \log n \cdot \log^2(nm))$ |
| $K_8$ | 8 | 28 | 9 | 4 | $O(m \cdot \log n \cdot \log^2(nm))$ |
| $K_{10}$ | 10 | 45 | 10 | 4 | $O(m \cdot \log n \cdot \log^2(nm))$ |

> **Note:** For unit weights, the weighted arithmetic architecture has similar asymptotic complexity to the unweighted arithmetic architecture. The key difference is that v1.5.0 supports weighted vertex covers and the Skip-K optimization, which reduces the number of pivots searched. The $m \cdot \log W$ term in the penalty adder reflects the cost of handling per-edge penalty contributions with weighted vertices.
