"""Multi-hop haircut taint propagation.

This is the classic GraphSense-style proportional taint flow: the tainted
fraction at each address equals the value-weighted average of its predecessors'
tainted fractions. Tainted source nodes are pinned to their severity weight.

We implement this as a Jacobi fixed-point iteration on the row-stochastic
incoming-value matrix:

    x_{k+1}[a] = severity[a]                      if severity[a] > 0  (pinned)
                 sum_p P[p, a] * x_k[p]            otherwise

where P[p, a] = value(p, a) / sum_q value(q, a).

Converges quickly on small subgraphs; we cap at `max_iters` to be safe.
"""

from __future__ import annotations

import numpy as np
import networkx as nx
from scipy.sparse import csr_matrix


def haircut_taint(
    g: nx.DiGraph,
    *,
    max_iters: int = 50,
    tol: float = 1e-6,
    damping: float = 1.0,
) -> dict[str, float]:
    """Return the steady-state tainted fraction for every node.

    `damping` < 1.0 mimics PageRank-style decay over hops (useful when the
    graph contains cycles); set to 1.0 for the textbook haircut.
    """
    nodes = list(g.nodes)
    if not nodes:
        return {}
    idx = {n: i for i, n in enumerate(nodes)}
    n = len(nodes)

    severity = np.array(
        [float(g.nodes[v].get("severity", 0.0)) for v in nodes], dtype=float
    )
    pinned = severity > 0  # tainted sources

    # Build transition matrix P[p, a] = value(p, a) / total_in(a).
    rows, cols, data = [], [], []
    in_totals = np.zeros(n)
    for p, a, ed in g.edges(data=True):
        v = float(ed.get("value_sat", 0))
        if v <= 0:
            continue
        in_totals[idx[a]] += v
        rows.append(idx[p])
        cols.append(idx[a])
        data.append(v)
    if data:
        # Normalize each column by total incoming value at the destination.
        cols_arr = np.array(cols)
        data_arr = np.array(data, dtype=float)
        nz = in_totals[cols_arr] > 0
        data_arr[nz] /= in_totals[cols_arr][nz]
        # Matrix M shape (n, n): M[p, a] = share of a's inflow coming from p.
        M = csr_matrix((data_arr, (rows, cols)), shape=(n, n))
    else:
        M = csr_matrix((n, n))

    x = severity.copy()
    for _ in range(max_iters):
        # x_new[a] = sum_p M[p, a] * x[p] = (x @ M)[a]
        x_new = damping * (x @ M)
        x_new[pinned] = severity[pinned]
        x_new = np.clip(x_new, 0.0, 1.0)
        if np.max(np.abs(x_new - x)) < tol:
            x = x_new
            break
        x = x_new

    return {nodes[i]: float(x[i]) for i in range(n)}
