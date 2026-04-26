"""mempool.space REST client with on-disk caching.

We deliberately wrap a single, well-known public BTC explorer to keep the demo
free of API keys. Responses are cached in a sqlite file so repeated runs (and
the notebook) are deterministic and offline-friendly after the first fetch.

API reference: https://mempool.space/docs/api/rest
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import requests_cache

DEFAULT_BASE_URL = "https://mempool.space/api"
DEFAULT_CACHE_PATH = Path("data/cache/explorer.sqlite")
DEFAULT_RATE_LIMIT_S = 0.25  # 4 req/s
DEFAULT_TIMEOUT_S = 15

log = logging.getLogger(__name__)


@dataclass
class TxIO:
    address: str | None
    value_sat: int


@dataclass
class Tx:
    txid: str
    inputs: list[TxIO]
    outputs: list[TxIO]

    @classmethod
    def from_mempool_json(cls, raw: dict) -> "Tx":
        inputs = [
            TxIO(
                address=(vin.get("prevout") or {}).get("scriptpubkey_address"),
                value_sat=int((vin.get("prevout") or {}).get("value", 0)),
            )
            for vin in raw.get("vin", [])
        ]
        outputs = [
            TxIO(
                address=vout.get("scriptpubkey_address"),
                value_sat=int(vout.get("value", 0)),
            )
            for vout in raw.get("vout", [])
        ]
        return cls(txid=raw["txid"], inputs=inputs, outputs=outputs)


class Explorer:
    """Cached, rate-limited client for mempool.space-style endpoints."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        cache_path: str | Path = DEFAULT_CACHE_PATH,
        rate_limit_s: float = DEFAULT_RATE_LIMIT_S,
        offline: bool = False,
    ):
        self.base_url = base_url.rstrip("/")
        self.rate_limit_s = rate_limit_s
        self.offline = offline
        self._last_call = 0.0

        cache_path = Path(cache_path)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.session = requests_cache.CachedSession(
            cache_name=str(cache_path.with_suffix("")),
            backend="sqlite",
            expire_after=None,  # cache forever; explorer responses are immutable for confirmed tx
            allowable_methods=("GET",),
        )

    def _get(self, path: str) -> object:
        url = f"{self.base_url}/{path.lstrip('/')}"
        if self.offline:
            kwargs = {"only_if_cached": True}
        else:
            kwargs = {}
            elapsed = time.monotonic() - self._last_call
            if elapsed < self.rate_limit_s:
                time.sleep(self.rate_limit_s - elapsed)

        resp = self.session.get(url, timeout=DEFAULT_TIMEOUT_S, **kwargs)
        if self.offline and resp.status_code == 504:
            raise RuntimeError(
                f"Explorer in offline mode and {url} is not in the cache"
            )
        resp.raise_for_status()
        if not getattr(resp, "from_cache", False):
            self._last_call = time.monotonic()
        ctype = resp.headers.get("Content-Type", "")
        if "json" in ctype or resp.text.lstrip().startswith(("[", "{")):
            return resp.json()
        return resp.text

    def address_txs(self, address: str, max_txs: int = 50) -> list[Tx]:
        """Return up to `max_txs` confirmed transactions touching `address`.

        mempool.space returns the most-recent ~50 by default; for a demo this
        is plenty.
        """
        raw = self._get(f"address/{address}/txs")
        if not isinstance(raw, list):
            return []
        return [Tx.from_mempool_json(t) for t in raw[:max_txs]]

    def tx(self, txid: str) -> Tx:
        raw = self._get(f"tx/{txid}")
        return Tx.from_mempool_json(raw)


def crawl_neighborhood(
    explorer: Explorer,
    seeds: Iterable[str],
    *,
    hops: int = 2,
    max_tx_per_addr: int = 50,
) -> list[Tx]:
    """Breadth-first crawl out to `hops` hops around the seed addresses.

    Returns a deduplicated list of Tx objects across the visited frontier.
    Bounded by `max_tx_per_addr` per address per hop to keep the demo small.
    """
    visited_addrs: set[str] = set()
    seen_txids: set[str] = set()
    out: list[Tx] = []
    frontier: set[str] = {a for a in seeds if a}

    for hop in range(hops + 1):
        next_frontier: set[str] = set()
        log.info("crawl hop=%d frontier=%d", hop, len(frontier))
        for addr in sorted(frontier):
            if addr in visited_addrs:
                continue
            visited_addrs.add(addr)
            try:
                txs = explorer.address_txs(addr, max_txs=max_tx_per_addr)
            except Exception as e:  # noqa: BLE001 — demo, log and continue
                log.warning("fetch failed for %s: %s", addr, e)
                continue
            for tx in txs:
                if tx.txid in seen_txids:
                    continue
                seen_txids.add(tx.txid)
                out.append(tx)
                if hop < hops:
                    for io in (*tx.inputs, *tx.outputs):
                        if io.address and io.address not in visited_addrs:
                            next_frontier.add(io.address)
        frontier = next_frontier
        if not frontier:
            break
    return out


