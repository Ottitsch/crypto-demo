"""1-hop direct exposure: fraction of incoming value from tainted predecessors,
weighted by the predecessor's severity.

For each address `a`:

    direct_exposure(a) = sum_{p in pred(a)} severity(p) * value(p, a)
                        / sum_{p in pred(a)} value(p, a)

If `a` has no incoming edges, direct exposure is 0.0.
"""

from __future__ import annotations

import networkx as nx


def direct_exposure(g: nx.DiGraph) -> dict[str, float]:
    out: dict[str, float] = {}
    for n in g.nodes:
        total = 0
        tainted = 0.0
        for pred, _, data in g.in_edges(n, data=True):
            v = data.get("value_sat", 0)
            total += v
            sev = g.nodes[pred].get("severity", 0.0)
            tainted += sev * v
        out[n] = (tainted / total) if total > 0 else 0.0
    return out
