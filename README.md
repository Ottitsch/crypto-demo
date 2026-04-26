# Proof of Funds — Bitcoin Risk Quantification Demo

A small, self-contained demo of how a cryptoasset service provider can quantify
the risk of an incoming Bitcoin transaction (Know-Your-Transaction / AML), using
[GraphSense TagPacks](https://github.com/graphsense/graphsense-tagpacks) as the
ground truth for known-bad entities.

## What it does

1. Loads entity labels (darknet markets, ransomware, scams, exchanges, ...) from
   GraphSense TagPacks.
2. Pulls a sampled Bitcoin transaction subgraph around tagged seed addresses
   from the [mempool.space](https://mempool.space/docs/api) public REST API
   (responses are cached locally for reproducibility).
3. Computes four complementary risk metrics per address:
   - **BFS distance** — hops to nearest tainted predecessor
   - **Direct exposure** — 1-hop tainted-value share
   - **Haircut taint** — multi-hop proportional propagation
   - **Aggregate score** — category-weighted 0–100 blend of the above
4. Presents the methodology, score distributions, and a worked case study in a
   Jupyter notebook.

## Quickstart

```bash
pip install -e ".[dev,notebook]"

# 1. Pull the real GraphSense TagPacks (~46k tagged BTC addresses).
git clone https://github.com/graphsense/graphsense-tagpacks \
    data/tagpacks/graphsense-tagpacks

# 2. Crawl a subgraph around the seeds in data/seeds.txt and score it.
#    Responses are cached to data/cache/explorer.sqlite — re-runs are free.
python -m pof.precompute --seeds data/seeds.txt --hops 2

# 3. Open the notebook for the narrative + plots.
jupyter notebook notebooks/01_proof_of_funds.ipynb

# Tests:
make test
```

## Repository layout

```
pof/                              # the library
  tagpacks.py                     # TagPack YAML loader & validator
  explorer.py                     # mempool.space client (cached)
  graph.py                        # build address-level transaction graph
  severity.py                     # category -> severity weight table
  metrics/
    distance.py                   # multi-source BFS distance
    direct_exposure.py            # 1-hop tainted value share
    haircut.py                    # multi-hop taint propagation
    aggregate.py                  # weighted 0–100 score
  precompute.py                   # CLI: load -> crawl -> score -> parquet
data/
  tagpacks/                       # cloned GraphSense TagPacks repo
  cache/                          # explorer response cache (sqlite)
  results/                        # precomputed scores (parquet)
  seeds.txt                       # tagged seed addresses to crawl from
notebooks/
  01_proof_of_funds.ipynb         # the narrative deliverable
tests/                            # unit tests with hand-built fixtures
```

## Limitations

- Sampled subgraph (≤50k addresses) — not a full chain analysis.
- No address clustering beyond optional co-spend (no change-address heuristics).
- Severity weights are illustrative; tune for your own risk appetite.
- Bitcoin only.

See the notebook's "Limitations" section for the long version.
