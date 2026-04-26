"""Category-weighted aggregate score in [0, 100]."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping

from pof.metrics.distance import UNREACHABLE


@dataclass(frozen=True)
class AggregateWeights:
    distance: float = 0.4
    direct: float = 0.3
    haircut: float = 0.3
    distance_decay_hops: float = 3.0


def _distance_component(d: int, decay: float) -> float:
    """exp(-d/decay), with unreachable nodes (-1) mapping to 0."""
    if d == UNREACHABLE or d < 0:
        return 0.0
    return math.exp(-d / decay)


def aggregate_score(
    distance: Mapping[str, int],
    direct: Mapping[str, float],
    haircut: Mapping[str, float],
    weights: AggregateWeights | None = None,
) -> dict[str, float]:
    """Combine the three component metrics into a single 0–100 score.

    All inputs must be keyed by the same set of addresses; missing entries
    default to 0 (or UNREACHABLE for distance).
    """
    w = weights or AggregateWeights()
    addrs = set(distance) | set(direct) | set(haircut)
    out: dict[str, float] = {}
    for a in addrs:
        d_comp = _distance_component(distance.get(a, UNREACHABLE), w.distance_decay_hops)
        e_comp = float(direct.get(a, 0.0))
        h_comp = float(haircut.get(a, 0.0))
        raw = w.distance * d_comp + w.direct * e_comp + w.haircut * h_comp
        out[a] = round(100 * max(0.0, min(1.0, raw)), 4)
    return out
