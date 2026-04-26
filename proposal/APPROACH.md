# Proof of Funds: Implementation Brief

## Objective

We will build a Bitcoin Proof of Funds prototype for KYT / AML screening. The
system will start from known high-risk addresses, crawl their transaction
neighbourhood, and assign each address an explainable risk score.

## Project brief

| Item | Description |
|---|---|
| Context | Cryptoasset service providers must quantify risk for incoming transactions as part of AML / KYT procedures. |
| Questions | How can we quantify risk, for example by distance from darknet markets? How can scores be precomputed for large graphs? |
| Tasks | Define risk metrics, compute exposure per entity, and analyze the resulting risk distribution. |

## Data we found

| Data | Use in the prototype |
|---|---|
| GraphSense TagPacks | Open address labels for ransomware, darknet markets, scams, hacks, exchanges, miners, and services. |
| Seed addresses | 6 tagged Bitcoin addresses: Locky ransomware, investment / gift-BTC scams, and the 2016 Bitfinex hack. |
| mempool.space API | Public transaction data for crawling the local neighbourhood around the seeds. |

## Core approach

| Step | What we will do | Output |
|---|---|---|
| 1. Label risk sources | Use GraphSense TagPacks to identify addresses linked to ransomware, darknet markets, hacks, scams, and services. | Tagged seed addresses |
| 2. Build local graph | Fetch transactions around the seeds and convert value flow into a weighted directed graph. | Address graph |
| 3. Score exposure | Combine graph distance, direct tainted value, and multi-hop taint propagation. | 0-100 risk score |
| 4. Analyze results | Export the score table and inspect the distribution in a notebook. | Case study + plots |

## Risk metrics

| Metric | Meaning |
|---|---|
| Distance | How many hops separate an address from known high-risk funds. |
| Direct exposure | How much incoming value comes directly from risky predecessors. |
| Haircut taint | How taint propagates through the graph over multiple hops. |
| Aggregate score | A weighted 0-100 score used to prioritize manual review. |

The score should be explainable. A compliance analyst should be able to see
whether risk comes from proximity, direct value exposure, or indirect taint.

## What we will deliver

| Deliverable | Purpose |
|---|---|
| Python package | Reusable implementation for loading labels, building graphs, and computing risk metrics. |
| Notebook | Readable explanation of the pipeline and score distribution. |
| Risk table | One row per address with metric columns and final score. |

## Scope boundaries

| Boundary | Reason |
|---|---|
| Bitcoin only | Keeps the first prototype focused on one transaction model and one data source. |
| Bounded crawl | Makes the demo reproducible, but may miss distant taint paths. |
| No full clustering | Change-address and entity clustering heuristics are future work. |
| Prototype weights | Severity weights are illustrative and not production policy. |
