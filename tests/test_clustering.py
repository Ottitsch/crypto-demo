"""Tests for address clustering heuristics."""

from __future__ import annotations

import networkx as nx

from pof.clustering import UnionFind, cluster_addresses, collapse_graph
from pof.explorer import Tx, TxIO


def _tx(txid: str, ins: list[tuple], outs: list[tuple]) -> Tx:
    return Tx(
        txid=txid,
        inputs=[TxIO(address=a, value_sat=v) for a, v in ins],
        outputs=[TxIO(address=a, value_sat=v) for a, v in outs],
    )


class TestUnionFind:
    def test_single_element(self):
        uf = UnionFind()
        assert uf.find("a") == "a"

    def test_union_and_find(self):
        uf = UnionFind()
        uf.union("a", "b")
        assert uf.find("a") == uf.find("b")

    def test_transitive(self):
        uf = UnionFind()
        uf.union("a", "b")
        uf.union("b", "c")
        assert uf.find("a") == uf.find("c")

    def test_clusters(self):
        uf = UnionFind()
        uf.union("a", "b")
        uf.find("c")  # isolated
        groups = uf.clusters()
        reps = list(groups.keys())
        assert len(reps) == 2
        ab_rep = uf.find("a")
        assert set(groups[ab_rep]) == {"a", "b"}

    def test_mapping(self):
        uf = UnionFind()
        uf.union("x", "y")
        m = uf.mapping()
        assert m["x"] == m["y"]


class TestClusterAddresses:
    def test_co_spend_groups_inputs(self):
        """Two inputs in the same tx -> same entity."""
        txs = [_tx("t1", [("A", 500), ("B", 500)], [("C", 1000)])]
        clusters = cluster_addresses(txs, use_change_heuristic=False)
        assert clusters["A"] == clusters["B"]
        assert clusters["C"] != clusters["A"]

    def test_single_input_no_merge(self):
        txs = [_tx("t1", [("A", 1000)], [("B", 600), ("C", 400)])]
        clusters = cluster_addresses(txs, use_change_heuristic=False)
        assert clusters["A"] != clusters["B"]
        assert clusters["A"] != clusters["C"]

    def test_transitive_co_spend(self):
        """A+B in tx1, B+C in tx2 -> A, B, C same entity."""
        txs = [
            _tx("t1", [("A", 500), ("B", 500)], [("X", 1000)]),
            _tx("t2", [("B", 300), ("C", 700)], [("Y", 1000)]),
        ]
        clusters = cluster_addresses(txs, use_change_heuristic=False)
        assert clusters["A"] == clusters["B"] == clusters["C"]

    def test_change_heuristic_groups_change_output(self):
        """Two outputs, one is new+small -> grouped with inputs as change."""
        txs = [_tx("t1", [("A", 500), ("B", 500)], [("C", 800), ("D", 200)])]
        clusters = cluster_addresses(txs, use_change_heuristic=True)
        # D is smaller (200 < 500) and only appears once -> change address
        assert clusters["D"] == clusters["A"]

    def test_change_heuristic_disabled(self):
        txs = [_tx("t1", [("A", 500), ("B", 500)], [("C", 800), ("D", 200)])]
        clusters = cluster_addresses(txs, use_change_heuristic=False)
        assert clusters["D"] != clusters["A"]


class TestCollapseGraph:
    def test_merges_nodes_and_sums_edges(self):
        g = nx.DiGraph()
        g.add_edge("A", "C", value_sat=100, tx_count=1)
        g.add_edge("B", "C", value_sat=200, tx_count=1)
        g.add_edge("C", "D", value_sat=300, tx_count=2)
        for n in g.nodes:
            g.nodes[n]["severity"] = 0.0

        clusters = {"A": "A", "B": "A", "C": "C", "D": "D"}  # A and B merged
        eg = collapse_graph(g, clusters)

        assert eg.has_edge("A", "C")
        assert eg["A"]["C"]["value_sat"] == 300  # 100 + 200
        assert eg["A"]["C"]["tx_count"] == 2
        assert eg.has_edge("C", "D")

    def test_drops_self_loops(self):
        g = nx.DiGraph()
        g.add_edge("A", "B", value_sat=100, tx_count=1)
        for n in g.nodes:
            g.nodes[n]["severity"] = 0.0

        clusters = {"A": "X", "B": "X"}
        eg = collapse_graph(g, clusters)
        assert eg.number_of_edges() == 0

    def test_inherits_worst_severity(self):
        g = nx.DiGraph()
        g.add_node("A", severity=0.0, label="clean")
        g.add_node("B", severity=0.9, label="bad", category="scam")

        clusters = {"A": "A", "B": "A"}
        eg = collapse_graph(g, clusters)
        assert eg.nodes["A"]["severity"] == 0.9
        assert eg.nodes["A"]["label"] == "bad"

    def test_preserves_total_edge_weight(self):
        """Total value flowing between two entity groups is preserved."""
        g = nx.DiGraph()
        g.add_edge("A1", "B1", value_sat=100, tx_count=1)
        g.add_edge("A1", "B2", value_sat=50, tx_count=1)
        g.add_edge("A2", "B1", value_sat=75, tx_count=1)
        for n in g.nodes:
            g.nodes[n]["severity"] = 0.0

        clusters = {"A1": "EA", "A2": "EA", "B1": "EB", "B2": "EB"}
        eg = collapse_graph(g, clusters)

        assert eg["EA"]["EB"]["value_sat"] == 225  # 100 + 50 + 75
        assert eg["EA"]["EB"]["tx_count"] == 3
