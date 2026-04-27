"""Tests for the validation module."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pof.validation import evaluate_scores


def _make_scores(addr_score_pairs: list[tuple[str, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        [{"address": a, "score": s} for a, s in addr_score_pairs]
    ).set_index("address")


class TestEvaluateScores:
    def test_perfect_separation(self):
        """All positives score 100, all negatives score 0 -> AUC ~ 1.0."""
        df = _make_scores([
            ("bad1", 100.0), ("bad2", 100.0),
            ("good1", 0.0), ("good2", 0.0), ("good3", 0.0),
        ])
        result = evaluate_scores(
            df,
            positive_addrs={"bad1", "bad2"},
            negative_addrs={"good1", "good2", "good3"},
            thresholds=[50.0],
        )
        assert result["auc"] > 0.95
        assert result["threshold_metrics"][50.0]["precision"] == 1.0
        assert result["threshold_metrics"][50.0]["recall"] == 1.0

    def test_no_separation(self):
        """All addresses have the same score -> AUC ~ 0.5."""
        df = _make_scores([
            ("bad1", 50.0), ("bad2", 50.0),
            ("good1", 50.0), ("good2", 50.0),
        ])
        result = evaluate_scores(
            df,
            positive_addrs={"bad1", "bad2"},
            negative_addrs={"good1", "good2"},
            thresholds=[50.0],
        )
        assert 0.3 < result["auc"] < 0.7

    def test_empty_positive_set(self):
        df = _make_scores([("a", 50.0)])
        result = evaluate_scores(df, positive_addrs=set(), negative_addrs={"a"})
        assert result["auc"] == 0.0
        assert result["n_positive"] == 0

    def test_default_negatives(self):
        """When negative_addrs is None, non-positive addresses are treated as negative."""
        df = _make_scores([("bad", 90.0), ("ok1", 10.0), ("ok2", 5.0)])
        result = evaluate_scores(df, positive_addrs={"bad"}, thresholds=[50.0])
        assert result["n_negative"] == 2
        assert result["threshold_metrics"][50.0]["recall"] == 1.0

    def test_threshold_metrics_structure(self):
        df = _make_scores([("a", 80.0), ("b", 20.0)])
        result = evaluate_scores(
            df, positive_addrs={"a"}, negative_addrs={"b"},
            thresholds=[25.0, 50.0, 75.0],
        )
        for t in [25.0, 50.0, 75.0]:
            m = result["threshold_metrics"][t]
            assert set(m.keys()) == {"tp", "fp", "tn", "fn", "precision", "recall", "f1"}
            assert m["tp"] + m["fn"] == 1  # one positive
            assert m["fp"] + m["tn"] == 1  # one negative
