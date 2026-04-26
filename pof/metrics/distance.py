"""Multi-source BFS distance from each node to the nearest tainted predecessor.

We walk the *reverse* graph: an address `a` is at distance `k` if some tainted
node `t` reaches `a` along a directed path of length `k` in the original graph.
That matches the AML intuition — "how many hops did the money travel from the
darknet market before it landed at this address?".
"""

from __future__ import annotations

from collections import deque
from typing import Iterable

import networkx as nx

UNREACHABLE = -1


def distance_to_tainted(
    g: nx.DiGraph, sources: Iterable[str] | None = None
) -> dict[str, int]:
    """Hop distance from each node to the nearest tainted source.

    `sources` defaults to all nodes with severity > 0. Tainted sources have
    distance 0. Nodes unreachable from any source get `UNREACHABLE` (-1).
    """
    if sources is None:
        sources = [n for n, d in g.nodes(data=True) if d.get("severity", 0.0) > 0]
    sources = [s for s in sources if s in g]

    dist: dict[str, int] = {n: UNREACHABLE for n in g.nodes}
    queue: deque[str] = deque()
    for s in sources:
        dist[s] = 0
        queue.append(s)

    while queue:
        u = queue.popleft()
        for v in g.successors(u):
            if dist[v] == UNREACHABLE:
                dist[v] = dist[u] + 1
                queue.append(v)
    return dist
