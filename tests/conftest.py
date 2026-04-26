"""Test fixtures.

Tests use small hand-built graphs to verify the *math* of the metrics. They do
not pretend to be real Bitcoin data — they are minimal structures (3-5 nodes)
with hand-computed expected values.
"""

from __future__ import annotations

import networkx as nx
import pandas as pd
import pytest

from pof.severity import severity_for


@pytest.fixture
def linear_chain():
    """T (severity 1.0) -> A -> B -> C, each edge value 100 sat.

    Hand-computed metrics:
        distance:        T=0, A=1, B=2, C=3
        direct_exposure: T=0, A=1.0, B=0.0, C=0.0
        haircut (damping=1.0): T=1.0, A=1.0, B=1.0, C=1.0
    """
    g = nx.DiGraph()
    g.add_edge("T", "A", value_sat=100)
    g.add_edge("A", "B", value_sat=100)
    g.add_edge("B", "C", value_sat=100)
    g.nodes["T"]["severity"] = 1.0
    for n in ("A", "B", "C"):
        g.nodes[n]["severity"] = 0.0
    return g


@pytest.fixture
def mixing_graph():
    """Two tainted sources merging into a clean address.

        T1 (sev 1.0) --100--> M
        T2 (sev 0.5) --100--> M    (M gets 200 in, half from T1 half from T2)
        M           --200--> X
        Clean       --100--> X     (X gets 300 in, 200 from M, 100 from Clean)

    Hand-computed:
        direct_exposure[M] = (1.0*100 + 0.5*100) / 200 = 0.75
        direct_exposure[X] = (sev(M)*200 + sev(Clean)*100) / 300
                           = (0*200 + 0*100) / 300 = 0.0
                           (M itself is not tagged so its severity is 0)
        haircut[T1] = 1.0 (pinned), haircut[T2] = 0.5 (pinned)
        haircut[M]  = 100/200 * 1.0 + 100/200 * 0.5 = 0.75
        haircut[X]  = 200/300 * 0.75 + 100/300 * 0 = 0.5
        haircut[Clean] = 0.0
        distance: T1=0, T2=0, M=1, X=2, Clean=-1 (no tainted predecessor reaches Clean)
    """
    g = nx.DiGraph()
    g.add_edge("T1", "M", value_sat=100)
    g.add_edge("T2", "M", value_sat=100)
    g.add_edge("M", "X", value_sat=200)
    g.add_edge("Clean", "X", value_sat=100)
    g.nodes["T1"]["severity"] = 1.0
    g.nodes["T2"]["severity"] = 0.5
    for n in ("M", "X", "Clean"):
        g.nodes[n]["severity"] = 0.0
    return g
