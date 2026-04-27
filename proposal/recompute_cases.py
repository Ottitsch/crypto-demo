"""Re-run precompute for each case with deeper crawl (hops=3) for richer data."""
from __future__ import annotations

import logging
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("pof.tagpacks").setLevel(logging.ERROR)

from pof.cases import CASES
from pof.precompute import run
import pandas as pd

PROJECT = Path(__file__).resolve().parent.parent
RESULTS = PROJECT / "data" / "results"
TAGPACKS = PROJECT / "data" / "tagpacks" / "graphsense-tagpacks" / "packs"

CASE_HOPS = {
    "wannacry": 2,
    "twitter_hack": 3,
    "colonial_pipeline": 3,
    "bitfinex_hack": 3,
}

for slug, case in CASES.items():
    hops = CASE_HOPS.get(slug, 2)
    out_addr = RESULTS / f"case_{slug}_scores.parquet"
    out_entity = RESULTS / f"case_{slug}_entity_scores.parquet"

    print(f"\n{'='*60}", flush=True)
    print(f"  Case: {case.name}", flush=True)
    print(f"  Seeds: {len(case.seed_addresses)}, Hops: {hops}", flush=True)
    print(f"{'='*60}", flush=True)

    try:
        print(f"  -> Address-level scoring...", flush=True)
        run(
            seeds=case.seed_addresses,
            tagpack_dir=TAGPACKS,
            out=out_addr,
            hops=hops,
            max_tx_per_addr=25,
            offline=False,
            entity_clustering=False,
        )

        print(f"  -> Entity-level scoring...", flush=True)
        run(
            seeds=case.seed_addresses,
            tagpack_dir=TAGPACKS,
            out=out_entity,
            hops=hops,
            max_tx_per_addr=25,
            offline=False,
            entity_clustering=True,
        )

        df_a = pd.read_parquet(out_addr)
        df_e = pd.read_parquet(out_entity)
        nz_a = (df_a["score"] > 0.1).sum()
        nz_e = (df_e["score"] > 0.1).sum()
        print(f"  Result: {len(df_a):,} addrs ({nz_a} non-zero), {len(df_e):,} entities ({nz_e} non-zero)", flush=True)
    except Exception as e:
        print(f"  ERROR: {e}", flush=True)
        import traceback
        traceback.print_exc()

print("\nDone! All cases recomputed.", flush=True)
