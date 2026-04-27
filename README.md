# Proof of Funds — Bitcoin Risk Quantification

A self-contained prototype demonstrating how a cryptoasset service provider can
quantify the risk of an incoming Bitcoin transaction (Know-Your-Transaction /
AML), using [GraphSense TagPacks](https://github.com/graphsense/graphsense-tagpacks)
as the ground truth for known-bad entities.

## What it does

1. **Loads entity labels** (darknet markets, ransomware, scams, exchanges, ...)
   from GraphSense TagPacks.
2. **Pulls a sampled Bitcoin transaction subgraph** around tagged seed addresses
   from the [mempool.space](https://mempool.space/docs/api) public REST API
   (responses are cached locally for reproducibility).
3. **Clusters addresses into entities** using the common-input-ownership heuristic
   and basic change-address detection (Meiklejohn et al., 2013).
4. **Computes four complementary risk metrics** per address/entity:
   - **BFS distance** — hops to nearest tainted predecessor
   - **Direct exposure** — 1-hop tainted-value share
   - **Haircut taint** — multi-hop proportional propagation (sparse-matrix fixed-point iteration)
   - **Aggregate score** — category-weighted 0–100 blend of the above
5. **Investigates real criminal cases** — WannaCry, Twitter Hack, Colonial Pipeline,
   Bitfinex Hack — with publicly known addresses from DOJ filings.
6. **Validates risk scores** against OFAC sanctions and Ransomwhere ground truth
   (precision/recall, ROC/AUC).
7. **Presents results** in Jupyter notebooks, an interactive Streamlit dashboard,
   and a LaTeX report.

## Prerequisites

- **Python 3.10+** (uses modern type hints like `dict[str, str] | None`)
- **Git** (to clone GraphSense TagPacks)
- **LaTeX distribution** (optional, only needed to compile the report)
  - Windows: [MiKTeX](https://miktex.org/download) — install via `winget install MiKTeX.MiKTeX`
  - Linux/macOS: TeX Live — `sudo apt install texlive-full` or `brew install --cask mactex`

## Quickstart

```bash
# 0. Clone this repo and enter it.
git clone <repo-url> crypto-demo
cd crypto-demo

# 1. Install the package with all dependencies.
pip install -e ".[all]"

# 2. Pull the real GraphSense TagPacks (~46k tagged BTC addresses).
git clone --depth 1 https://github.com/graphsense/graphsense-tagpacks data/tagpacks/graphsense-tagpacks

# 3. Crawl a subgraph around the seeds and score it (with entity clustering).
#    This hits the mempool.space API; first run takes ~10–30 min.
#    Responses are cached in data/cache/ — subsequent runs are fast.
python -m pof.precompute --seeds data/seeds.txt --hops 2

# 4. Open the notebooks.
jupyter notebook notebooks/01_proof_of_funds.ipynb
jupyter notebook notebooks/02_case_studies.ipynb
jupyter notebook notebooks/03_validation_and_comparison.ipynb

# 5. Launch the interactive dashboard.
streamlit run pof/dashboard.py

# 6. Run tests.
python -m pytest -v
```

### Generating the report (optional)

```bash
# Generate the 7 publication-quality figures (requires precomputed results from step 3).
python proposal/generate_figures.py

# Compile the LaTeX report (run twice to resolve cross-references).
cd proposal
pdflatex -interaction=nonstopmode report.tex
pdflatex -interaction=nonstopmode report.tex
```

### Windows notes

- Use PowerShell or Git Bash.
- If `pytest` is not found, use `python -m pytest -v`.
- If `streamlit` is not found, use `python -m streamlit run pof/dashboard.py`.
- MiKTeX may prompt to install missing packages on first LaTeX compile —
  run `initexmf --set-config-value=[MPM]AutoInstall=1` to auto-install.

## Repository layout

```
pof/                              # the library
  clustering.py                   # Union-Find entity clustering (co-spend + change heuristic)
  cases.py                        # registry of real forensic cases (WannaCry, Twitter, etc.)
  validation.py                   # OFAC/Ransomwhere ground-truth validation + ROC/AUC
  dashboard.py                    # Streamlit interactive investigation dashboard
  tagpacks.py                     # TagPack YAML loader & validator
  explorer.py                     # mempool.space client (cached)
  graph.py                        # build address/entity-level transaction graph
  severity.py                     # category -> severity weight table
  metrics/
    distance.py                   # multi-source BFS distance
    direct_exposure.py            # 1-hop tainted value share
    haircut.py                    # multi-hop taint propagation
    aggregate.py                  # weighted 0–100 score
  precompute.py                   # CLI: load -> crawl -> cluster -> score -> parquet
data/
  seeds.txt                       # tagged seed addresses to crawl from
  ofac/                           # OFAC SDN sanctioned BTC addresses (pre-extracted)
  tagpacks/custom/                # custom TagPack YAMLs for Twitter Hack + Colonial Pipeline
  tagpacks/graphsense-tagpacks/   # cloned GraphSense repo (gitignored, see step 2)
  cache/                          # explorer response cache — sqlite (gitignored)
  results/                        # precomputed scores — parquet + figures (gitignored)
notebooks/
  01_proof_of_funds.ipynb         # methodology narrative deliverable
  02_case_studies.ipynb           # real forensic case investigations
  03_validation_and_comparison.ipynb  # OFAC validation + addr vs entity comparison
tests/                            # unit tests with hand-built fixtures
proposal/
  report.tex                      # LaTeX report (compile with pdflatex)
  generate_figures.py             # generates 7 figures from precomputed results
  generate_final_report.py        # legacy reportlab-based PDF generator
  APPROACH.md                     # project plan
```

## Features

### Entity Clustering
Addresses are grouped into entities using two standard Bitcoin forensics
heuristics:
- **Common-input-ownership (Heuristic 1):** all input addresses in the same
  transaction are assumed to belong to the same wallet.
- **Change-address detection (Heuristic 2):** single-use outputs receiving the
  "change" from a transaction are grouped with the input addresses.

### Forensic Case Studies
Four real criminal cases with publicly known BTC addresses:
- **WannaCry (2017)** — ransomware, 3 hardcoded payment addresses
- **Twitter Hack (2020)** — BTC doubling scam via compromised accounts
- **Colonial Pipeline (2021)** — DarkSide ransomware, DOJ-traced seizure
- **Bitfinex Hack (2016)** — largest DOJ cryptocurrency seizure

### Validation
Risk scores are validated against external ground truth:
- **OFAC SDN list** — US Treasury sanctioned cryptocurrency addresses
- **Ransomwhere** — crowdsourced ransomware payment tracker
- Metrics: ROC/AUC, precision/recall at multiple thresholds, confusion matrices

### Interactive Dashboard
Streamlit-based investigation tool with 4 tabs:
- **Investigation** — paste an address, see its risk score and graph
- **Case Studies** — explore pre-computed forensic case results
- **Distributions** — compare score distributions across cases
- **Validation** — ROC curves and threshold analysis

## Data Sources (all free, no API keys)

| Source | URL | Format |
|--------|-----|--------|
| GraphSense TagPacks | github.com/graphsense/graphsense-tagpacks | YAML |
| mempool.space | mempool.space/api | JSON REST |
| OFAC SDN list | treasury.gov/ofac/downloads/sanctions/1.0/sdn_advanced.xml | XML |
| OFAC pre-extracted BTC | github.com/0xB10C/ofac-sanctioned-digital-currency-addresses | TXT |
| Ransomwhere | api.ransomwhe.re/export | JSON |
| DOJ court documents | justice.gov (press releases) | Addresses hardcoded in `cases.py` |

## Limitations

- Sampled subgraph (bounded BFS) — not a full chain analysis.
- Entity clustering uses basic heuristics; sophisticated users can defeat these.
- Severity weights are illustrative; tune for your own risk appetite.
- Bitcoin only.
- mempool.space rate limit (~4 req/s); the explorer caches all responses permanently.

See the notebooks' "Limitations" sections for the long version.
