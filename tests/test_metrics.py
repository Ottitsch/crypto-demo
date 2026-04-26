"""Hand-computed expected values for the four metrics on tiny graphs."""

from __future__ import annotations

import math

import pytest

from pof.metrics import (
    AggregateWeights,
    aggregate_score,
    direct_exposure,
    distance_to_tainted,
    haircut_taint,
)
from pof.metrics.distance import UNREACHABLE


def test_distance_linear(linear_chain):
    d = distance_to_tainted(linear_chain)
    assert d == {"T": 0, "A": 1, "B": 2, "C": 3}


def test_distance_unreachable(mixing_graph):
    d = distance_to_tainted(mixing_graph)
    assert d["T1"] == 0
    assert d["T2"] == 0
    assert d["M"] == 1
    assert d["X"] == 2
    assert d["Clean"] == UNREACHABLE


def test_direct_exposure_linear(linear_chain):
    e = direct_exposure(linear_chain)
    assert e["T"] == 0.0  # no incoming
    assert e["A"] == 1.0  # 100% from T (severity 1.0)
    assert e["B"] == 0.0  # A is not tainted (severity 0)
    assert e["C"] == 0.0


def test_direct_exposure_mixing(mixing_graph):
    e = direct_exposure(mixing_graph)
    # M: (1.0*100 + 0.5*100) / 200 = 0.75
    assert e["M"] == pytest.approx(0.75)
    # X: M and Clean both have severity 0, so direct exposure = 0
    assert e["X"] == 0.0
    assert e["Clean"] == 0.0


def test_haircut_linear(linear_chain):
    h = haircut_taint(linear_chain, damping=1.0)
    # full propagation along a chain with no dilution
    assert h["T"] == pytest.approx(1.0)
    assert h["A"] == pytest.approx(1.0)
    assert h["B"] == pytest.approx(1.0)
    assert h["C"] == pytest.approx(1.0)


def test_haircut_mixing(mixing_graph):
    h = haircut_taint(mixing_graph, damping=1.0)
    assert h["T1"] == pytest.approx(1.0)  # pinned
    assert h["T2"] == pytest.approx(0.5)  # pinned
    # M = 100/200 * 1.0 + 100/200 * 0.5 = 0.75
    assert h["M"] == pytest.approx(0.75)
    # X = 200/300 * 0.75 + 100/300 * 0 = 0.5
    assert h["X"] == pytest.approx(0.5)
    assert h["Clean"] == pytest.approx(0.0)


def test_aggregate_score_combines_components():
    dist = {"a": 0, "b": 1, "c": -1}
    direct = {"a": 1.0, "b": 0.5, "c": 0.0}
    haircut = {"a": 1.0, "b": 0.5, "c": 0.0}
    w = AggregateWeights()
    s = aggregate_score(dist, direct, haircut, w)

    # a: 0.4 * exp(0) + 0.3*1 + 0.3*1 = 1.0  -> 100
    assert s["a"] == pytest.approx(100.0)
    # b: 0.4 * exp(-1/3) + 0.3*0.5 + 0.3*0.5
    expected_b = 100 * (0.4 * math.exp(-1 / 3) + 0.3 * 0.5 + 0.3 * 0.5)
    assert s["b"] == pytest.approx(expected_b, abs=1e-3)
    # c: distance unreachable -> 0 contribution; direct/haircut 0 too
    assert s["c"] == pytest.approx(0.0)
