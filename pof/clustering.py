"""Address clustering heuristics for Bitcoin entity resolution.

Bitcoin forensics commonly groups addresses into "entities" (wallets controlled
by the same actor) using on-chain heuristics. This module implements:

1. **Common-input-ownership (co-spend):** all input addresses in a single
   transaction are assumed to belong to the same entity.  This is the standard
   Heuristic 1 from Meiklejohn et al. (2013).

2. **Change-address detection (basic):** if a transaction has exactly two
   outputs and one of them is a never-before-seen address that receives the
   "change" (total_in - primary_out - fee), that address is grouped with the
   input addresses.  This is a simplified version of Heuristic 2.

The grouping is maintained via a Union-Find (disjoint-set) data structure for
near-linear performance on large address sets.
"""

from __future__ import annotations

from typing import Iterable

import networkx as nx

from pof.explorer import Tx


class UnionFind:
    """Weighted-union + path-compression disjoint-set."""

    def __init__(self) -> None:
        self._parent: dict[str, str] = {}
        self._rank: dict[str, int] = {}

    def find(self, x: str) -> str:
        if x not in self._parent:
            self._parent[x] = x
            self._rank[x] = 0
        root = x
        while self._parent[root] != root:
            root = self._parent[root]
        while self._parent[x] != root:
            self._parent[x], x = root, self._parent[x]
        return root

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self._rank[ra] < self._rank[rb]:
            ra, rb = rb, ra
        self._parent[rb] = ra
        if self._rank[ra] == self._rank[rb]:
            self._rank[ra] += 1

    def clusters(self) -> dict[str, list[str]]:
        """Return {representative: [members]} for all known addresses."""
        groups: dict[str, list[str]] = {}
        for addr in self._parent:
            root = self.find(addr)
            groups.setdefault(root, []).append(addr)
        return groups

    def mapping(self) -> dict[str, str]:
        """Return {address: representative} for every known address."""
        return {addr: self.find(addr) for addr in self._parent}


def cluster_addresses(
    txs: Iterable[Tx],
    *,
    use_change_heuristic: bool = True,
) -> dict[str, str]:
    """Group addresses into entities and return a mapping address -> representative.

    Parameters
    ----------
    txs : iterable of Tx
        Transactions to analyze.
    use_change_heuristic : bool
        If True, also apply the basic change-address heuristic (Heuristic 2).
    """
    uf = UnionFind()
    addr_tx_count: dict[str, int] = {}

    tx_list = list(txs)

    for tx in tx_list:
        for io in (*tx.inputs, *tx.outputs):
            if io.address:
                addr_tx_count[io.address] = addr_tx_count.get(io.address, 0) + 1

    for tx in tx_list:
        input_addrs = [io.address for io in tx.inputs if io.address]
        if len(input_addrs) < 2:
            if input_addrs:
                uf.find(input_addrs[0])
            continue

        anchor = input_addrs[0]
        for addr in input_addrs[1:]:
            uf.union(anchor, addr)

        if not use_change_heuristic:
            continue

        output_addrs = [io for io in tx.outputs if io.address]
        if len(output_addrs) != 2:
            continue

        total_in = sum(io.value_sat for io in tx.inputs if io.address)
        for out_io in output_addrs:
            is_new = addr_tx_count.get(out_io.address, 0) <= 1
            is_smaller = out_io.value_sat < total_in * 0.5
            if is_new and is_smaller:
                uf.union(anchor, out_io.address)
                break

    for tx in tx_list:
        for io in (*tx.inputs, *tx.outputs):
            if io.address:
                uf.find(io.address)

    return uf.mapping()


def collapse_graph(
    g: nx.DiGraph,
    clusters: dict[str, str],
) -> nx.DiGraph:
    """Collapse a per-address graph into a per-entity graph.

    Nodes that map to the same representative are merged. Edge weights
    (``value_sat``, ``tx_count``) are summed. Node attributes are taken from
    the member with the highest severity (so the entity inherits the worst tag).
    Self-loops (intra-entity transfers) are dropped.
    """
    entity_g = nx.DiGraph()

    for node, data in g.nodes(data=True):
        rep = clusters.get(node, node)
        if rep not in entity_g:
            entity_g.add_node(rep, **dict(data), _member_count=1)
        else:
            existing = entity_g.nodes[rep]
            existing["_member_count"] = existing.get("_member_count", 1) + 1
            if data.get("severity", 0.0) > existing.get("severity", 0.0):
                existing.update({k: v for k, v in data.items() if k != "_member_count"})

    for u, v, data in g.edges(data=True):
        ru, rv = clusters.get(u, u), clusters.get(v, v)
        if ru == rv:
            continue
        if entity_g.has_edge(ru, rv):
            ed = entity_g[ru][rv]
            ed["value_sat"] = ed.get("value_sat", 0) + data.get("value_sat", 0)
            ed["tx_count"] = ed.get("tx_count", 0) + data.get("tx_count", 0)
        else:
            entity_g.add_edge(ru, rv, value_sat=data.get("value_sat", 0), tx_count=data.get("tx_count", 0))

    return entity_g
