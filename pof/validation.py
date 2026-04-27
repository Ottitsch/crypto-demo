"""Validation against external ground-truth sources (OFAC, Ransomwhere).

This module loads known-bad addresses from free public datasets and evaluates
how well the risk scores separate them from known-clean entities. Metrics
include ROC/AUC, precision/recall at multiple thresholds, and confusion
matrices.
"""

from __future__ import annotations

import io
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

OFAC_SDN_URL = (
    "https://www.treasury.gov/ofac/downloads/sanctions/1.0/sdn_advanced.xml"
)
RANSOMWHERE_URL = "https://api.ransomwhe.re/export"


# ---------------------------------------------------------------------------
# OFAC SDN loader
# ---------------------------------------------------------------------------

def load_ofac_addresses(source: str | Path | None = None) -> set[str]:
    """Parse BTC addresses from the OFAC SDN Advanced XML.

    ``source`` can be a local file path or a URL. Falls back to the default
    Treasury URL if *None*. Bitcoin addresses are identified by the
    ``Digital Currency Address`` id type with asset ``XBT``.
    """
    if source is None:
        source = OFAC_SDN_URL

    path = Path(source) if not str(source).startswith("http") else None
    if path and path.exists():
        tree = ET.parse(path)
        root = tree.getroot()
    else:
        import requests
        resp = requests.get(str(source), timeout=120)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)

    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag.split("}")[0] + "}"

    addresses: set[str] = set()

    for feature in root.iter(f"{ns}Feature"):
        ftype = feature.find(f"{ns}FeatureType")
        if ftype is None:
            continue
        ftype_text = (ftype.text or "").strip()
        if "Digital Currency Address" not in ftype_text:
            continue

        version_detail = feature.find(f".//{ns}VersionDetail")
        if version_detail is not None:
            detail_text = (version_detail.text or "").strip()
        else:
            detail_text = ""

        is_btc = False
        for vid in feature.iter(f"{ns}VersionID"):
            vid_text = (vid.text or "").strip().upper()
            if vid_text in ("XBT", "BTC", "BITCOIN"):
                is_btc = True
                break

        if not is_btc:
            for comment in feature.iter(f"{ns}Comment"):
                ctxt = (comment.text or "").upper()
                if "XBT" in ctxt or "BTC" in ctxt or "BITCOIN" in ctxt:
                    is_btc = True
                    break

        if is_btc and detail_text:
            addresses.add(detail_text)

    log.info("loaded %d BTC addresses from OFAC SDN", len(addresses))
    return addresses


def load_ofac_addresses_txt(path: str | Path) -> set[str]:
    """Load OFAC BTC addresses from a plain-text file (one address per line).

    Skips blank lines and lines starting with ``#``. This is the preferred
    loader when using the pre-extracted list from
    ``0xB10C/ofac-sanctioned-digital-currency-addresses``.
    """
    p = Path(path)
    if not p.exists():
        log.warning("OFAC text file not found: %s", p)
        return set()
    addrs: set[str] = set()
    for line in p.read_text(encoding="utf-8").splitlines():
        a = line.strip()
        if a and not a.startswith("#"):
            addrs.add(a)
    log.info("loaded %d BTC addresses from %s", len(addrs), p.name)
    return addrs


# ---------------------------------------------------------------------------
# Ransomwhere loader
# ---------------------------------------------------------------------------

def load_ransomwhere(
    source: str | Path | None = None,
    cache_path: Path | None = None,
) -> pd.DataFrame:
    """Load the Ransomwhere dataset (address + family + transactions).

    Returns a DataFrame with at least columns ``address`` and ``family``.
    If *cache_path* is given and exists, reads from cache instead of fetching.
    """
    if cache_path and cache_path.exists():
        return pd.read_parquet(cache_path)

    if source is None:
        source = RANSOMWHERE_URL

    path = Path(source) if not str(source).startswith("http") else None
    if path and path.exists():
        df = pd.read_json(path)
    else:
        import requests
        resp = requests.get(str(source), timeout=120)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and "result" in data:
            data = data["result"]
        df = pd.DataFrame(data)

    if "address" not in df.columns and "addr" in df.columns:
        df = df.rename(columns={"addr": "address"})

    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(cache_path)
        log.info("cached ransomwhere data to %s", cache_path)

    log.info("loaded %d ransomwhere records", len(df))
    return df


def ransomwhere_addresses(df: pd.DataFrame) -> set[str]:
    """Extract unique BTC addresses from a Ransomwhere DataFrame."""
    if "address" in df.columns:
        return set(df["address"].dropna().unique())
    return set()


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate_scores(
    scores_df: pd.DataFrame,
    positive_addrs: set[str],
    negative_addrs: set[str] | None = None,
    *,
    score_col: str = "score",
    thresholds: Sequence[float] = (25.0, 50.0, 75.0),
) -> dict:
    """Evaluate risk scores against ground-truth labels.

    Parameters
    ----------
    scores_df : DataFrame
        Must have an ``address`` index (or column) and a ``score`` column.
    positive_addrs : set
        Addresses known to be high-risk (OFAC, ransomware, etc.).
    negative_addrs : set or None
        Addresses known to be benign (exchanges, services). If None, all
        non-positive addresses in the scores are treated as negative.
    score_col : str
        Column name for the risk score.
    thresholds : sequence of float
        Score thresholds at which to compute precision/recall.

    Returns
    -------
    dict with keys:
        roc_points : list of (fpr, tpr, threshold) tuples
        auc : float
        threshold_metrics : dict[threshold -> {tp, fp, tn, fn, precision, recall, f1}]
        n_positive, n_negative : int
    """
    df = scores_df.copy()
    if "address" in df.columns:
        df = df.set_index("address")

    all_addrs = set(df.index)
    pos_in_graph = positive_addrs & all_addrs
    if negative_addrs is not None:
        neg_in_graph = negative_addrs & all_addrs
    else:
        neg_in_graph = all_addrs - positive_addrs

    if not pos_in_graph or not neg_in_graph:
        return {
            "roc_points": [],
            "auc": 0.0,
            "threshold_metrics": {},
            "n_positive": len(pos_in_graph),
            "n_negative": len(neg_in_graph),
        }

    labeled = pos_in_graph | neg_in_graph
    sub = df.loc[df.index.isin(labeled), score_col].copy()
    y_true = np.array([1 if a in pos_in_graph else 0 for a in sub.index])
    y_score = sub.values.astype(float)

    n_pos = int(y_true.sum())
    n_neg = len(y_true) - n_pos

    sorted_idx = np.argsort(-y_score, kind="mergesort")
    scores_sorted = y_score[sorted_idx]
    y_sorted = y_true[sorted_idx]

    distinct_thresholds = np.concatenate([[scores_sorted[0] + 1], scores_sorted])
    roc_points: list[tuple[float, float, float]] = [(0.0, 0.0, float(distinct_thresholds[0]))]

    tp_cum = 0
    fp_cum = 0
    i = 0
    n = len(scores_sorted)
    while i < n:
        j = i
        while j < n and scores_sorted[j] == scores_sorted[i]:
            if y_sorted[j] == 1:
                tp_cum += 1
            else:
                fp_cum += 1
            j += 1
        fpr = fp_cum / n_neg if n_neg > 0 else 0.0
        tpr = tp_cum / n_pos if n_pos > 0 else 0.0
        roc_points.append((float(fpr), float(tpr), float(scores_sorted[i])))
        i = j

    if roc_points[-1] != (1.0, 1.0, 0.0):
        roc_points.append((1.0, 1.0, 0.0))

    fprs = [pt[0] for pt in roc_points]
    tprs = [pt[1] for pt in roc_points]
    auc = float(np.trapz(tprs, fprs))

    threshold_metrics: dict[float, dict] = {}
    for t in thresholds:
        pred = (y_score >= t).astype(int)
        tp = int(((pred == 1) & (y_true == 1)).sum())
        fp = int(((pred == 1) & (y_true == 0)).sum())
        fn = int(((pred == 0) & (y_true == 1)).sum())
        tn = int(((pred == 0) & (y_true == 0)).sum())
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        threshold_metrics[float(t)] = {
            "tp": tp, "fp": fp, "tn": tn, "fn": fn,
            "precision": precision, "recall": recall, "f1": f1,
        }

    return {
        "roc_points": roc_points,
        "auc": auc,
        "threshold_metrics": threshold_metrics,
        "n_positive": len(pos_in_graph),
        "n_negative": len(neg_in_graph),
    }


# ---------------------------------------------------------------------------
# Plotting helpers (matplotlib)
# ---------------------------------------------------------------------------

def plot_roc(eval_result: dict, *, ax=None):
    """Plot a ROC curve from evaluate_scores output."""
    import matplotlib.pyplot as plt

    if ax is None:
        _, ax = plt.subplots(figsize=(6, 6))

    roc = eval_result["roc_points"]
    if not roc:
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        return ax

    fprs = [p[0] for p in roc]
    tprs = [p[1] for p in roc]
    ax.plot(fprs, tprs, linewidth=2)
    ax.plot([0, 1], [0, 1], "k--", alpha=0.3)
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title(f"ROC Curve (AUC = {eval_result['auc']:.3f})")
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    return ax


def plot_threshold_analysis(eval_result: dict, *, ax=None):
    """Plot precision, recall, F1 across thresholds."""
    import matplotlib.pyplot as plt

    if ax is None:
        _, ax = plt.subplots(figsize=(8, 4))

    roc = eval_result["roc_points"]
    if not roc:
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        return ax

    ts = sorted(eval_result["threshold_metrics"].keys())
    prec = [eval_result["threshold_metrics"][t]["precision"] for t in ts]
    rec = [eval_result["threshold_metrics"][t]["recall"] for t in ts]
    f1s = [eval_result["threshold_metrics"][t]["f1"] for t in ts]

    ax.plot(ts, prec, "o-", label="Precision")
    ax.plot(ts, rec, "s-", label="Recall")
    ax.plot(ts, f1s, "^-", label="F1")
    ax.set_xlabel("Score Threshold")
    ax.set_ylabel("Value")
    ax.set_title("Metrics at Score Thresholds")
    ax.legend()
    ax.set_xlim(0, 100)
    ax.set_ylim(-0.05, 1.05)
    return ax
