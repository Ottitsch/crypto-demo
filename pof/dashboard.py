"""Interactive Streamlit dashboard for Bitcoin risk investigation.

Run with:  streamlit run pof/dashboard.py
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

logging.basicConfig(level=logging.WARNING)

st.set_page_config(
    page_title="Proof of Funds — BTC Risk Dashboard",
    page_icon="🔍",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA = Path("data")
TAGPACKS_DIR = DATA / "tagpacks" / "graphsense-tagpacks" / "packs"
CACHE_PATH = DATA / "cache" / "explorer.sqlite"
RESULTS_DIR = DATA / "results"

# ---------------------------------------------------------------------------
# Cached loaders
# ---------------------------------------------------------------------------


@st.cache_resource
def load_tags():
    from pof.tagpacks import discover_tagpack_files, load_tagpacks

    files = discover_tagpack_files(TAGPACKS_DIR)
    return load_tagpacks(files)


@st.cache_resource
def get_explorer():
    from pof.explorer import Explorer

    return Explorer(cache_path=CACHE_PATH)


def _run_investigation(seeds: list[str], hops: int, max_tx: int, use_clustering: bool):
    """Run the full pipeline and return results dict."""
    from pof.clustering import cluster_addresses, collapse_graph
    from pof.explorer import crawl_neighborhood
    from pof.graph import build_graph, tainted_nodes
    from pof.precompute import score_graph

    tags = load_tags()
    explorer = get_explorer()

    txs = crawl_neighborhood(explorer, seeds, hops=hops, max_tx_per_addr=max_tx)
    g_addr = build_graph(txs, tags=tags)
    scores_addr = score_graph(g_addr)

    if use_clustering:
        clusters = cluster_addresses(txs)
        g_entity = collapse_graph(g_addr, clusters)
        scores_entity = score_graph(g_entity)
    else:
        clusters = {}
        g_entity = g_addr
        scores_entity = scores_addr

    return {
        "txs": txs,
        "g_addr": g_addr,
        "g_entity": g_entity,
        "scores_addr": scores_addr,
        "scores_entity": scores_entity,
        "clusters": clusters,
        "tainted": tainted_nodes(g_addr),
    }


# ---------------------------------------------------------------------------
# Tab 1: Investigation
# ---------------------------------------------------------------------------

def tab_investigation():
    st.header("Address Investigation")
    st.markdown("Paste one or more BTC addresses to investigate their risk exposure.")

    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        addr_input = st.text_area(
            "BTC Addresses (one per line)",
            height=100,
            placeholder="bc1q...\n1A1zP1...",
        )
    with col2:
        hops = st.slider("Crawl hops", 1, 3, 1)
        max_tx = st.slider("Max TX per address", 10, 50, 25)
    with col3:
        use_clustering = st.checkbox("Entity clustering", value=True)

    seeds = [s.strip() for s in addr_input.strip().splitlines() if s.strip()]

    if st.button("Investigate", type="primary") and seeds:
        with st.spinner(f"Crawling {len(seeds)} seed(s) at {hops} hop(s)..."):
            try:
                result = _run_investigation(seeds, hops, max_tx, use_clustering)
            except Exception as e:
                st.error(f"Investigation failed: {e}")
                return

        st.success(
            f"Crawled {len(result['txs'])} transactions, "
            f"{result['g_addr'].number_of_nodes()} addresses, "
            f"{len(result['tainted'])} tainted"
        )

        _show_score_summary(result)
        _show_graph_viz(result)
        _show_score_table(result)


def _show_score_summary(result):
    """Display score gauges for seed addresses."""
    df = result["scores_addr"]
    st.subheader("Risk Scores")

    cols = st.columns(min(4, len(df)))
    top = df.nlargest(4, "score")
    for i, (addr, row) in enumerate(top.iterrows()):
        with cols[i % len(cols)]:
            score = row["score"]
            if score >= 75:
                color = "🔴"
            elif score >= 40:
                color = "🟠"
            else:
                color = "🟢"
            st.metric(
                label=f"{color} {str(addr)[:16]}...",
                value=f"{score:.1f}/100",
                delta=f"dist={int(row['distance'])}, haircut={row['haircut']:.2f}",
            )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Score Breakdown (Top 10)**")
        st.dataframe(
            df.nlargest(10, "score")[["score", "distance", "direct_exposure", "haircut", "severity", "label", "category"]],
            use_container_width=True,
        )
    with col2:
        st.markdown("**Score Distribution**")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(6, 3))
        ax.hist(df["score"], bins=30, edgecolor="black", alpha=0.7)
        ax.set_xlabel("Score")
        ax.set_ylabel("Count")
        ax.axvline(x=75, color="red", linestyle="--", alpha=0.7, label="High risk (75)")
        ax.axvline(x=40, color="orange", linestyle="--", alpha=0.7, label="Medium risk (40)")
        ax.legend(fontsize=8)
        st.pyplot(fig)
        plt.close(fig)


def _show_graph_viz(result):
    """Render an interactive network graph."""
    try:
        from pyvis.network import Network
    except ImportError:
        st.info("Install `pyvis` for interactive graph visualization: `pip install pyvis`")
        return

    st.subheader("Transaction Graph")

    g = result["g_addr"]
    df = result["scores_addr"]

    max_nodes = st.slider("Max nodes to display", 50, 500, 150, key="graph_nodes")
    top_addrs = set(df.nlargest(max_nodes, "score").index)

    net = Network(height="500px", width="100%", directed=True, bgcolor="#0e1117", font_color="white")
    net.barnes_hut(gravity=-3000, central_gravity=0.3, spring_length=100)

    for node in top_addrs:
        if node not in g:
            continue
        score = df.loc[node, "score"] if node in df.index else 0
        sev = g.nodes[node].get("severity", 0)
        label_text = g.nodes[node].get("label", "")

        if sev > 0:
            color = "#ff4444"
        elif score >= 75:
            color = "#ff8800"
        elif score >= 40:
            color = "#ffcc00"
        else:
            color = "#44bb44"

        title = f"{node}\nScore: {score:.1f}\nSeverity: {sev}\nLabel: {label_text}"
        short = str(node)[:8] + "..."
        net.add_node(node, label=short, color=color, title=title, size=10 + score / 5)

    for u, v, data in g.edges(data=True):
        if u in top_addrs and v in top_addrs:
            val = data.get("value_sat", 0)
            net.add_edge(u, v, title=f"{val:,} sat", width=max(0.5, min(5, val / 1_000_000)))

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w") as f:
        net.save_graph(f.name)
        html = Path(f.name).read_text()
    st.components.v1.html(html, height=520, scrolling=True)


def _show_score_table(result):
    """Full searchable score table."""
    st.subheader("Full Score Table")
    df = result["scores_addr"].reset_index()
    search = st.text_input("Filter addresses", key="addr_filter")
    if search:
        df = df[df["address"].str.contains(search, case=False, na=False)]
    st.dataframe(
        df.sort_values("score", ascending=False),
        use_container_width=True,
        height=400,
    )


# ---------------------------------------------------------------------------
# Tab 2: Case Studies
# ---------------------------------------------------------------------------

def tab_case_studies():
    from pof.cases import CASES, get_case

    st.header("Forensic Case Studies")

    case_slug = st.selectbox(
        "Select a case",
        options=list(CASES.keys()),
        format_func=lambda s: CASES[s].name,
    )
    case = get_case(case_slug)

    st.markdown(f"**Date:** {case.date}")
    st.markdown(f"**Description:** {case.description}")
    st.markdown(f"**Category:** `{case.category}` / `{case.abuse}`")
    st.markdown("**Seed addresses:**")
    for addr in case.seed_addresses:
        st.code(addr)
    st.markdown("**Sources:**")
    for src in case.sources:
        st.markdown(f"- [{src}]({src})")

    parquet_path = RESULTS_DIR / f"case_{case_slug}_scores.parquet"
    entity_path = RESULTS_DIR / f"case_{case_slug}_entity_scores.parquet"

    if parquet_path.exists():
        df_addr = pd.read_parquet(parquet_path)
        st.subheader("Pre-computed Results")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Addresses", len(df_addr))
        col2.metric("Mean Score", f"{df_addr['score'].mean():.1f}")
        col3.metric("Median Score", f"{df_addr['score'].median():.1f}")
        col4.metric("Tainted", int((df_addr["severity"] > 0).sum()))

        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 3, figsize=(15, 4))
        axes[0].hist(df_addr["score"], bins=30, edgecolor="black", alpha=0.7)
        axes[0].set_xlabel("Aggregate Score")
        axes[0].set_title("Score Distribution")

        dist_clean = df_addr["distance"].replace(-1, np.nan).dropna()
        if not dist_clean.empty:
            axes[1].hist(dist_clean, bins=15, edgecolor="black", alpha=0.7)
        axes[1].set_xlabel("Distance (hops)")
        axes[1].set_title("Distance to Tainted")

        axes[2].hist(df_addr["haircut"], bins=30, edgecolor="black", alpha=0.7)
        axes[2].set_xlabel("Haircut Taint")
        axes[2].set_title("Haircut Distribution")

        plt.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

        if entity_path.exists():
            df_entity = pd.read_parquet(entity_path)
            st.subheader("Entity vs Address Comparison")
            col1, col2 = st.columns(2)
            col1.metric("Address nodes", len(df_addr))
            col2.metric("Entity nodes", len(df_entity))
            st.markdown(
                f"Clustering reduced graph by **{(1 - len(df_entity)/max(len(df_addr),1))*100:.1f}%**"
            )

        st.subheader("Top Risk Addresses")
        st.dataframe(df_addr.nlargest(20, "score"), use_container_width=True)

    else:
        st.warning(
            f"No pre-computed results found at `{parquet_path}`. "
            "Run the case study notebook first, or investigate directly from Tab 1."
        )

    if st.button("Run Live Investigation", key=f"live_{case_slug}"):
        with st.spinner("Running investigation..."):
            result = _run_investigation(case.seed_addresses, hops=1, max_tx=25, use_clustering=True)
        _show_score_summary(result)


# ---------------------------------------------------------------------------
# Tab 3: Score Distributions
# ---------------------------------------------------------------------------

def tab_distributions():
    st.header("Score Distributions")

    parquet_files = sorted(RESULTS_DIR.glob("case_*_scores.parquet")) if RESULTS_DIR.exists() else []

    if not parquet_files:
        st.warning("No pre-computed results found. Run the case study notebook or precompute first.")
        return

    selected = st.multiselect(
        "Select datasets to compare",
        options=[p.stem.replace("case_", "").replace("_scores", "") for p in parquet_files],
        default=[p.stem.replace("case_", "").replace("_scores", "") for p in parquet_files[:4]],
    )

    if not selected:
        return

    dfs = {}
    for slug in selected:
        path = RESULTS_DIR / f"case_{slug}_scores.parquet"
        if path.exists():
            dfs[slug] = pd.read_parquet(path)

    import matplotlib.pyplot as plt

    metric = st.selectbox("Metric", ["score", "distance", "direct_exposure", "haircut"])

    fig, ax = plt.subplots(figsize=(10, 5))
    for slug, df in dfs.items():
        vals = df[metric]
        if metric == "distance":
            vals = vals.replace(-1, np.nan).dropna()
        ax.hist(vals, bins=30, alpha=0.5, label=slug, edgecolor="black")
    ax.set_xlabel(metric.replace("_", " ").title())
    ax.set_ylabel("Count")
    ax.set_title(f"{metric.replace('_', ' ').title()} Distribution Across Cases")
    ax.legend()
    st.pyplot(fig)
    plt.close(fig)

    st.subheader("Summary Statistics")
    summary_rows = []
    for slug, df in dfs.items():
        summary_rows.append({
            "Case": slug,
            "N": len(df),
            "Mean Score": f"{df['score'].mean():.1f}",
            "Median Score": f"{df['score'].median():.1f}",
            "Std Score": f"{df['score'].std():.1f}",
            "Max Score": f"{df['score'].max():.1f}",
            "% High Risk (>75)": f"{(df['score'] > 75).mean()*100:.1f}%",
            "% Medium (40-75)": f"{((df['score'] >= 40) & (df['score'] <= 75)).mean()*100:.1f}%",
            "% Low (<40)": f"{(df['score'] < 40).mean()*100:.1f}%",
        })
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True)


# ---------------------------------------------------------------------------
# Tab 4: Validation
# ---------------------------------------------------------------------------

def tab_validation():
    st.header("Validation Against Ground Truth")
    st.markdown(
        "Evaluate how well the risk scores separate **known-bad** addresses "
        "(OFAC sanctions, ransomware) from **known-clean** addresses (exchanges, services)."
    )

    parquet_files = sorted(RESULTS_DIR.glob("case_*_scores.parquet")) if RESULTS_DIR.exists() else []
    if not parquet_files:
        st.warning("No pre-computed results found.")
        return

    selected = st.selectbox(
        "Dataset",
        options=[p.stem.replace("case_", "").replace("_scores", "") for p in parquet_files],
    )

    path = RESULTS_DIR / f"case_{selected}_scores.parquet"
    if not path.exists():
        st.error("File not found.")
        return

    df = pd.read_parquet(path)

    positive = set(df[df["severity"] > 0.5].index)
    negative = set(df[df["severity"] < 0.01].index)

    if not positive:
        st.warning("No high-severity addresses found in this dataset for validation.")
        return

    st.markdown(f"**Positives (severity > 0.5):** {len(positive)} addresses")
    st.markdown(f"**Negatives (severity = 0):** {len(negative)} addresses")

    from pof.validation import evaluate_scores, plot_roc, plot_threshold_analysis
    import matplotlib.pyplot as plt

    result = evaluate_scores(
        df, positive_addrs=positive, negative_addrs=negative,
        thresholds=[10, 25, 40, 50, 75, 90],
    )

    col1, col2 = st.columns(2)
    with col1:
        st.metric("AUC", f"{result['auc']:.3f}")
    with col2:
        best_f1 = max(
            (m["f1"] for m in result["threshold_metrics"].values()), default=0
        )
        st.metric("Best F1", f"{best_f1:.3f}")

    col1, col2 = st.columns(2)
    with col1:
        fig, ax = plt.subplots(figsize=(5, 5))
        plot_roc(result, ax=ax)
        st.pyplot(fig)
        plt.close(fig)

    with col2:
        fig, ax = plt.subplots(figsize=(6, 4))
        plot_threshold_analysis(result, ax=ax)
        st.pyplot(fig)
        plt.close(fig)

    st.subheader("Threshold Analysis")
    thresh_rows = []
    for t, m in sorted(result["threshold_metrics"].items()):
        thresh_rows.append({
            "Threshold": t,
            "TP": m["tp"], "FP": m["fp"], "TN": m["tn"], "FN": m["fn"],
            "Precision": f"{m['precision']:.3f}",
            "Recall": f"{m['recall']:.3f}",
            "F1": f"{m['f1']:.3f}",
        })
    st.dataframe(pd.DataFrame(thresh_rows), use_container_width=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    st.title("Proof of Funds — Bitcoin Risk Dashboard")
    st.markdown(
        "An investigation tool for quantifying risk exposure in Bitcoin transactions. "
        "Uses GraphSense TagPacks, mempool.space data, and entity clustering."
    )

    tab1, tab2, tab3, tab4 = st.tabs([
        "🔍 Investigation",
        "📋 Case Studies",
        "📊 Distributions",
        "✅ Validation",
    ])

    with tab1:
        tab_investigation()
    with tab2:
        tab_case_studies()
    with tab3:
        tab_distributions()
    with tab4:
        tab_validation()


if __name__ == "__main__":
    main()
