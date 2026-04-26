from pathlib import Path

import pytest

from pof.tagpacks import (
    CONFIDENCE_LEVELS,
    TagPackError,
    _normalize_confidence,
    load_tagpack_file,
    load_tagpacks,
)


def write_pack(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "pack.yaml"
    p.write_text(body)
    return p


def test_header_inheritance(tmp_path):
    p = write_pack(
        tmp_path,
        """
title: t
source: https://example.org/t
currency: BTC
abuse: ransomware
confidence: forensic
tags:
  - address: addr1
    label: Sample A
  - address: addr2
    label: Sample B
    abuse: scam
""",
    )
    tags = load_tagpack_file(p)
    assert {t.address for t in tags} == {"addr1", "addr2"}
    assert tags[0].abuse == "ransomware"
    assert tags[1].abuse == "scam"  # tag overrides header
    assert tags[0].confidence == CONFIDENCE_LEVELS["forensic"] == 50


def test_drops_non_btc(tmp_path):
    p = write_pack(
        tmp_path,
        """
source: x
tags:
  - address: a
    label: keep
    currency: BTC
  - address: b
    label: drop
    currency: ETH
""",
    )
    tags = load_tagpack_file(p)
    assert {t.address for t in tags} == {"a"}


def test_currency_with_trailing_whitespace(tmp_path):
    # Some real packs have "currency: BTC " with a trailing space; we must accept it.
    p = write_pack(
        tmp_path,
        """
source: x
tags:
  - address: a
    label: keep
    currency: 'BTC '
""",
    )
    assert {t.address for t in load_tagpack_file(p)} == {"a"}


def test_missing_required_fields_skipped(tmp_path, caplog):
    p = write_pack(
        tmp_path,
        """
source: x
currency: BTC
tags:
  - address: a
    label: ok
  - address: b   # missing label
""",
    )
    tags = load_tagpack_file(p)
    assert {t.address for t in tags} == {"a"}


def test_load_tagpacks_dedupes_keeping_highest_severity(tmp_path):
    p1 = tmp_path / "p1.yaml"
    p1.write_text(
        """
source: a
currency: BTC
category: exchange
tags:
  - address: shared
    label: at-exchange
"""
    )
    p2 = tmp_path / "p2.yaml"
    p2.write_text(
        """
source: b
currency: BTC
abuse: ransomware
tags:
  - address: shared
    label: at-ransomware
"""
    )
    df = load_tagpacks([p1, p2])
    assert df.loc["shared", "abuse"] == "ransomware"
    assert df.loc["shared", "severity"] == 1.0


def test_normalize_confidence():
    assert _normalize_confidence("forensic") == 50
    assert _normalize_confidence("ledger_immanent") == 100
    assert _normalize_confidence(75) == 75
    assert _normalize_confidence("75") == 75
    assert _normalize_confidence(None) == 50
    assert _normalize_confidence("nonsense") == 50  # logged + defaulted
