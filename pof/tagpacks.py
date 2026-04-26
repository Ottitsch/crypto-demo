"""TagPack YAML loader.

A TagPack is a YAML document with a header (creator, source, currency, ...) and
a list of `tags`. Header fields propagate to each tag unless the tag overrides
them — this matches the real GraphSense schema. We only consume the per-tag
fields needed for risk scoring; unknown fields (e.g. `is_cluster_definer`,
`actor`, `lastmod`) are ignored.

Reference: https://github.com/graphsense/graphsense-tagpacks
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
import yaml

from pof.severity import severity_for

log = logging.getLogger(__name__)

REQUIRED_TAG_FIELDS = {"address", "label"}

# Official confidence-level mapping from
# https://github.com/graphsense/graphsense-tagpack-tool (src/tagpack/db/confidence.csv).
# Mapping confidence-id -> integer level in [0, 100].
CONFIDENCE_LEVELS: dict[str, int] = {
    "override": 100,
    "ownership": 100,
    "ledger_immanent": 100,
    "manual_transaction": 90,
    "service_api": 70,
    "forensic_investigation": 70,
    "authority_data": 60,
    "trusted_provider": 50,
    "service_data": 50,
    "forensic": 50,
    "untrusted_transaction": 40,
    "web_crawl": 20,
    "heuristic": 10,
    "unknown": 5,
}


def _normalize_confidence(value) -> int:
    """Accept either a numeric value or a confidence-level id string."""
    if value is None:
        return 50
    if isinstance(value, (int, float)):
        return int(value)
    key = str(value).strip().lower()
    if key in CONFIDENCE_LEVELS:
        return CONFIDENCE_LEVELS[key]
    try:
        return int(key)
    except ValueError:
        log.warning("unknown confidence value %r, defaulting to 50", value)
        return 50


@dataclass(frozen=True)
class Tag:
    address: str
    label: str
    source: str
    currency: str
    category: str | None
    abuse: str | None
    confidence: int

    @property
    def severity(self) -> float:
        return severity_for(self.category, self.abuse)


class TagPackError(ValueError):
    """Raised when a TagPack file fails validation."""


def _coerce_tag(raw: dict, *, header: dict) -> Tag:
    missing = REQUIRED_TAG_FIELDS - raw.keys()
    if missing:
        raise TagPackError(f"tag missing required fields: {sorted(missing)}")
    return Tag(
        address=str(raw["address"]).strip(),
        label=str(raw["label"]).strip(),
        source=str(raw.get("source", header.get("source", ""))).strip(),
        currency=str(raw.get("currency", header.get("currency", "BTC"))).strip().upper(),
        category=raw.get("category", header.get("category")),
        abuse=raw.get("abuse", header.get("abuse")),
        confidence=_normalize_confidence(raw.get("confidence", header.get("confidence"))),
    )


def load_tagpack_file(path: str | Path) -> list[Tag]:
    """Parse a single TagPack YAML file. Returns the list of Tag objects.

    Tags whose `currency` is not BTC are dropped (this demo is BTC-only).
    Files without a `tags` list are skipped with a warning instead of raising,
    so a noisy clone of the GraphSense repo doesn't abort the run.
    """
    path = Path(path)
    try:
        with path.open() as fh:
            doc = yaml.safe_load(fh) or {}
    except yaml.YAMLError as e:
        log.warning("skipping %s: YAML parse error: %s", path, e)
        return []

    if "tags" not in doc or not isinstance(doc["tags"], list):
        return []

    header = {k: v for k, v in doc.items() if k != "tags"}
    tags: list[Tag] = []
    for raw in doc["tags"]:
        if not isinstance(raw, dict):
            continue
        try:
            tag = _coerce_tag(raw, header=header)
        except TagPackError as e:
            log.warning("%s: %s", path, e)
            continue
        if tag.currency == "BTC":
            tags.append(tag)
    return tags


def load_tagpacks(paths: Iterable[str | Path]) -> pd.DataFrame:
    """Load one or more TagPack files into a DataFrame indexed by address.

    For addresses tagged in multiple packs, the row with the highest severity
    is kept (ties broken by highest confidence).
    """
    rows: list[dict] = []
    for p in paths:
        for tag in load_tagpack_file(p):
            rows.append(
                {
                    "address": tag.address,
                    "label": tag.label,
                    "source": tag.source,
                    "category": tag.category,
                    "abuse": tag.abuse,
                    "confidence": tag.confidence,
                    "severity": tag.severity,
                }
            )
    if not rows:
        return pd.DataFrame(
            columns=["label", "source", "category", "abuse", "confidence", "severity"]
        ).rename_axis("address")

    df = pd.DataFrame(rows)
    df = df.sort_values(["severity", "confidence"], ascending=False)
    df = df.drop_duplicates(subset="address", keep="first")
    return df.set_index("address")


def discover_tagpack_files(root: str | Path) -> list[Path]:
    """Recursively find *.yaml / *.yml files under `root`."""
    root = Path(root)
    return sorted(
        p for p in root.rglob("*") if p.suffix.lower() in {".yaml", ".yml"}
    )
