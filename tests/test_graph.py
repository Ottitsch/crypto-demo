"""Tests for the graph builder.

These use small hand-built mempool.space-format dicts (turned into Tx objects)
rather than real BTC data — we are testing the proportional-attribution math,
not Bitcoin itself.
"""

from __future__ import annotations

import pandas as pd

from pof.explorer import Tx, TxIO
from pof.graph import build_graph, edge_list, tainted_nodes


def make_tx(txid, ins, outs):
    return Tx(
        txid=txid,
        inputs=[TxIO(address=a, value_sat=v) for a, v in ins],
        outputs=[TxIO(address=a, value_sat=v) for a, v in outs],
    )


def test_proportional_edge_value_single_input():
    """Single input -> two outputs: each output edge equals the output value."""
    txs = [make_tx("t1", [("A", 1000)], [("B", 600), ("C", 400)])]
    el = edge_list(txs)
    assert set(zip(el["src"], el["dst"], el["value_sat"])) == {
        ("A", "B", 600),
        ("A", "C", 400),
    }


def test_proportional_edge_value_multi_input():
    """Two inputs (60/40 split) -> one 1000 sat output: edges 600/400."""
    txs = [make_tx("t1", [("A", 600), ("B", 400)], [("C", 1000)])]
    el = edge_list(txs).sort_values(["src", "dst"]).reset_index(drop=True)
    assert el["value_sat"].tolist() == [600, 400]
    assert el["src"].tolist() == ["A", "B"]
    assert el["dst"].tolist() == ["C", "C"]


def test_coinbase_inputs_skipped():
    """Inputs with no address (coinbase) should not produce edges."""
    txs = [make_tx("cb", [(None, 0)], [("Miner", 5_000_000_000)])]
    el = edge_list(txs)
    assert el.empty


def test_op_return_outputs_skipped():
    """Outputs with no address (OP_RETURN) should not produce edges."""
    txs = [make_tx("t1", [("A", 1000)], [("B", 800), (None, 0)])]
    el = edge_list(txs)
    assert el["dst"].tolist() == ["B"]


def test_build_graph_aggregates_repeated_edges():
    txs = [
        make_tx("t1", [("A", 100)], [("B", 100)]),
        make_tx("t2", [("A", 200)], [("B", 200)]),
    ]
    g = build_graph(txs)
    assert g["A"]["B"]["value_sat"] == 300
    assert g["A"]["B"]["tx_count"] == 2


def test_build_graph_annotates_with_tags():
    txs = [make_tx("t1", [("A", 100)], [("B", 100)])]
    tags = pd.DataFrame(
        {"label": ["xx"], "category": ["darknet_market"], "abuse": [None],
         "confidence": [80], "severity": [0.9], "source": ["s"]},
        index=pd.Index(["A"], name="address"),
    )
    g = build_graph(txs, tags=tags)
    assert g.nodes["A"]["severity"] == 0.9
    assert g.nodes["B"]["severity"] == 0.0
    assert tainted_nodes(g) == ["A"]
