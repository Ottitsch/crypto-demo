"""Build a directed, value-weighted address graph from a list of transactions.

For each transaction, every input address gets an outbound edge to every output
address. The edge value is `output_value * (input_value / total_input_value)`,
which is the standard proportional-attribution simplification used when full
UTXO-level taint tracking is out of scope.

If multiple transactions create the same edge, weights are summed.
"""

from __future__ import annotations

from typing import Iterable

import networkx as nx
import pandas as pd

from pof.explorer import Tx


def edge_list(txs: Iterable[Tx]) -> pd.DataFrame:
    """Return the proportional-attribution edge list as a DataFrame.

    Columns: ``src``, ``dst``, ``value_sat``, ``txid``.
    Coinbase inputs (no address) and OP_RETURN outputs (no address) are
    skipped — they are not addresses we can score.
    """
    rows: list[dict] = []
    for tx in txs:
        in_total = sum(io.value_sat for io in tx.inputs if io.address)
        if in_total <= 0:
            continue  # coinbase or all-unspendable inputs
        for vin in tx.inputs:
            if not vin.address or vin.value_sat <= 0:
                continue
            in_share = vin.value_sat / in_total
            for vout in tx.outputs:
                if not vout.address or vout.value_sat <= 0:
                    continue
                rows.append(
                    {
                        "src": vin.address,
                        "dst": vout.address,
                        "value_sat": int(vout.value_sat * in_share),
                        "txid": tx.txid,
                    }
                )
    if not rows:
        return pd.DataFrame(columns=["src", "dst", "value_sat", "txid"])
    return pd.DataFrame(rows)


def build_graph(
    txs: Iterable[Tx],
    tags: pd.DataFrame | None = None,
) -> nx.DiGraph:
    """Build a `networkx.DiGraph` from transactions, optionally annotated with tags.

    Edges carry ``value_sat`` (sum across contributing tx) and ``tx_count``.
    Nodes carry ``label``, ``category``, ``abuse``, ``severity`` if a tag exists.
    """
    edges = edge_list(txs)
    g = nx.DiGraph()

    if not edges.empty:
        agg = (
            edges.groupby(["src", "dst"], sort=False)
            .agg(value_sat=("value_sat", "sum"), tx_count=("txid", "nunique"))
            .reset_index()
        )
        for row in agg.itertuples(index=False):
            g.add_edge(row.src, row.dst, value_sat=int(row.value_sat), tx_count=int(row.tx_count))

    # Ensure every address mentioned in any tx is a node, even if isolated.
    for tx in txs:
        for io in (*tx.inputs, *tx.outputs):
            if io.address:
                g.add_node(io.address)

    if tags is not None and not tags.empty:
        for addr, row in tags.iterrows():
            if addr in g:
                g.nodes[addr].update(
                    {
                        "label": row.get("label"),
                        "category": row.get("category"),
                        "abuse": row.get("abuse"),
                        "severity": float(row.get("severity", 0.0)),
                    }
                )
    # Default severity 0.0 for untagged nodes; helpful for downstream metrics.
    for n, data in g.nodes(data=True):
        data.setdefault("severity", 0.0)

    return g


def tainted_nodes(g: nx.DiGraph, threshold: float = 0.0) -> list[str]:
    """Return nodes whose severity exceeds `threshold` (default: any > 0)."""
    return [n for n, d in g.nodes(data=True) if d.get("severity", 0.0) > threshold]
