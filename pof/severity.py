"""Category -> severity weight table.

Severity is a number in [0, 1] that captures how "tainted" funds from an entity
of a given category are considered to be. The values below are illustrative —
production deployments should calibrate these against their own risk appetite
and regulatory guidance.

The taxonomy mirrors the GraphSense TagPack `category` and `abuse` fields. When
both are set, `abuse` takes precedence (it is more specific).
"""

from __future__ import annotations

SEVERITY: dict[str, float] = {
    # abuse-class (always high)
    "ransomware": 1.0,
    "sextortion": 0.95,
    "extortion": 0.95,
    "scam": 0.8,
    "fraud": 0.8,
    "phishing": 0.8,
    "ponzi_scheme": 0.8,
    "malware": 0.8,
    "theft": 0.85,
    "service_hack": 0.85,
    # category-class
    "darknet_market": 0.9,
    "market": 0.6,           # generic "market" — ambiguous, mid-weight
    "mixing_service": 0.5,
    "mixer": 0.5,
    "coinjoin": 0.5,
    "gambling": 0.3,
    # benign / regulated
    "exchange": 0.0,
    "miner": 0.0,
    "mining": 0.0,
    "mining_pool": 0.0,
    "pool": 0.0,
    "service": 0.0,
    "merchant_services": 0.0,
    "wallet_service": 0.0,
    "faucet": 0.0,
    "other": 0.0,
}


def severity_for(category: str | None, abuse: str | None = None) -> float:
    """Return the severity weight for a (category, abuse) pair.

    `abuse` wins over `category` when both are set, since abuse classification
    is more specific. Unknown labels fall back to 0.0 (treated as benign).
    """
    for key in (abuse, category):
        if key:
            normalized = key.strip().lower().replace(" ", "_")
            if normalized in SEVERITY:
                return SEVERITY[normalized]
    return 0.0
