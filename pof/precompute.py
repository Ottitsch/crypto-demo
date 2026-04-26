"""End-to-end CLI: load tagpacks, build graph, score every address.

Usage:
    python -m pof.precompute --seeds data/seeds.txt --hops 2 \\
        --out data/results/scores.parquet
    python -m pof.precompute --offline   # use only cached responses
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

from pof.explorer import Explorer, crawl_neighborhood
from pof.graph import build_graph
from pof.metrics import aggregate_score, direct_exposure, distance_to_tainted, haircut_taint
from pof.tagpacks import discover_tagpack_files, load_tagpacks

DEFAULT_TAGPACKS = Path("data/tagpacks/graphsense-tagpacks/packs")
DEFAULT_OUT = Path("data/results/scores.parquet")


def score_graph(g) -> pd.DataFrame:
    """Run all four metrics over the graph and return one row per address."""
    dist = distance_to_tainted(g)
    direct = direct_exposure(g)
    haircut = haircut_taint(g)
    score = aggregate_score(dist, direct, haircut)

    rows = []
    for n, data in g.nodes(data=True):
        rows.append(
            {
                "address": n,
                "label": data.get("label"),
                "category": data.get("category"),
                "abuse": data.get("abuse"),
                "severity": float(data.get("severity", 0.0)),
                "distance": int(dist.get(n, -1)),
                "direct_exposure": float(direct.get(n, 0.0)),
                "haircut": float(haircut.get(n, 0.0)),
                "score": float(score.get(n, 0.0)),
            }
        )
    return pd.DataFrame(rows).set_index("address")


def run(
    *,
    seeds: list[str],
    tagpack_dir: Path,
    out: Path,
    hops: int,
    max_tx_per_addr: int,
    offline: bool,
) -> pd.DataFrame:
    log = logging.getLogger("pof.precompute")

    tagpack_files = discover_tagpack_files(tagpack_dir)
    log.info("loading %d tagpack files from %s", len(tagpack_files), tagpack_dir)
    tags = load_tagpacks(tagpack_files)
    log.info("loaded %d tagged addresses", len(tags))

    if not seeds:
        raise SystemExit("--seeds is required (no addresses found)")
    explorer = Explorer(offline=offline)
    log.info(
        "crawling %d seeds, hops=%d, max_tx_per_addr=%d, offline=%s",
        len(seeds), hops, max_tx_per_addr, offline,
    )
    txs = crawl_neighborhood(
        explorer, seeds, hops=hops, max_tx_per_addr=max_tx_per_addr
    )
    log.info("collected %d transactions", len(txs))

    g = build_graph(txs, tags=tags)
    log.info("graph: %d nodes, %d edges", g.number_of_nodes(), g.number_of_edges())

    scores = score_graph(g)
    out.parent.mkdir(parents=True, exist_ok=True)
    scores.to_parquet(out)
    log.info("wrote %d scored addresses to %s", len(scores), out)
    return scores


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Precompute risk scores for a Bitcoin subgraph.")
    p.add_argument("--seeds", type=Path, default=Path("data/seeds.txt"), help="File with one BTC address per line.")
    p.add_argument("--tagpacks", type=Path, default=DEFAULT_TAGPACKS, help="Directory of TagPack YAML files.")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output parquet path.")
    p.add_argument("--hops", type=int, default=2, help="BFS depth around seeds.")
    p.add_argument("--max-tx-per-addr", type=int, default=25, help="Cap transactions fetched per address.")
    p.add_argument("--offline", action="store_true", help="Only use the explorer cache; never hit the network.")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    seeds: list[str] = []
    if args.seeds and args.seeds.exists():
        seeds = [
            line.strip()
            for line in args.seeds.read_text().splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
    run(
        seeds=seeds,
        tagpack_dir=args.tagpacks,
        out=args.out,
        hops=args.hops,
        max_tx_per_addr=args.max_tx_per_addr,
        offline=args.offline,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
