"""Generate all publication-quality figures for the final report.

Produces 300 DPI PNGs with a consistent professional style.

Run:
    python proposal/generate_figures.py
"""

from __future__ import annotations

import logging
import sys
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patheffects as pe
import numpy as np
import pandas as pd
import networkx as nx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logging.basicConfig(level=logging.INFO)
logging.getLogger("pof.tagpacks").setLevel(logging.WARNING)
warnings.filterwarnings("ignore")

from pof.cases import CASES
from pof.validation import evaluate_scores

PROJECT = Path(__file__).resolve().parent.parent
RESULTS = PROJECT / "data" / "results"
OUT = PROJECT / "data" / "results"
OUT.mkdir(parents=True, exist_ok=True)

DPI = 300

# Consistent color palette
PAL = {
    "primary": "#1565C0",
    "secondary": "#E65100",
    "accent": "#2E7D32",
    "danger": "#C62828",
    "neutral": "#546E7A",
    "light": "#B0BEC5",
    "bg": "#FAFAFA",
}

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.labelsize": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.facecolor": "white",
    "figure.dpi": DPI,
    "savefig.dpi": DPI,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.15,
})


def load_case_data() -> dict:
    data = {}
    for slug, case in CASES.items():
        af = RESULTS / f"case_{slug}_scores.parquet"
        ef = RESULTS / f"case_{slug}_entity_scores.parquet"
        if af.exists() and ef.exists():
            data[slug] = {
                "name": case.name,
                "case": case,
                "addr": pd.read_parquet(af),
                "entity": pd.read_parquet(ef),
            }
    return data


def load_ofac() -> set[str]:
    p = PROJECT / "data" / "ofac" / "sanctioned_addresses_XBT.txt"
    if not p.exists():
        return set()
    return {line.strip() for line in p.read_text().splitlines()
            if line.strip() and not line.startswith("#")}


# ═══════════════════════════════════════════════════════════════════════
# FIG 1: Pipeline Architecture Diagram
# ═══════════════════════════════════════════════════════════════════════

def fig_pipeline():
    fig, ax = plt.subplots(figsize=(16, 8))
    ax.set_xlim(0, 16)
    ax.set_ylim(-1, 9)
    ax.axis("off")

    def draw_box(x, y, label, color, w=2.4, h=1.1, fontsize=10):
        box = FancyBboxPatch((x - w/2, y - h/2), w, h,
                             boxstyle="round,pad=0.2",
                             facecolor=color, edgecolor="#1B2631",
                             linewidth=2, alpha=0.95, zorder=3)
        ax.add_patch(box)
        ax.text(x, y, label, ha="center", va="center",
                fontsize=fontsize, fontweight="bold", color="white", zorder=4,
                path_effects=[pe.withStroke(linewidth=1, foreground="#00000066")])

    def draw_input(x, y, label, fontsize=9):
        box = FancyBboxPatch((x - 1.3, y - 0.55), 2.6, 1.1,
                             boxstyle="round,pad=0.15",
                             facecolor="#E8EAF6", edgecolor="#7986CB",
                             linewidth=1.5, linestyle="--", zorder=3)
        ax.add_patch(box)
        ax.text(x, y, label, ha="center", va="center",
                fontsize=fontsize, color="#283593", style="italic", zorder=4)

    def arrow_down(x1, y1, x2, y2, color="#455A64"):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color=color,
                                    lw=2.2, connectionstyle="arc3,rad=0.0"),
                    zorder=2)

    def arrow_right(x1, y1, x2, y2, color="#455A64"):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color=color,
                                    lw=2.2, connectionstyle="arc3,rad=0.0"),
                    zorder=2)

    # ── Layout: single column, top to bottom ──
    # All processing boxes centered at x=8, flowing downward
    cx = 8.0

    # ROW 0 (y=8): Title
    ax.text(cx, 8.5, "Data Pipeline Architecture", fontsize=17, fontweight="bold",
            ha="center", color="#11151A")

    # ROW 1 (y=7): Data Sources — spread horizontally
    draw_input(3.0, 7.0, "GraphSense\nTagPacks")
    draw_input(8.0, 7.0, "Custom DOJ\nTagPacks")
    draw_input(13.0, 7.0, "mempool.space\nAPI")

    # ROW 2 (y=5.2): Step 1 - Load & Label + Step 2 - BFS Crawl side by side
    draw_box(5.5, 5.2, "1. Load & Label\naddresses", "#1565C0")
    draw_box(10.5, 5.2, "2. BFS Crawl\ntransactions", "#1565C0")

    # ROW 3 (y=3.4): Step 3 - Build Graph
    draw_box(cx, 3.4, "3. Build Transaction\nGraph", "#0D47A1")

    # ROW 4 (y=1.6): Step 4 - Entity Clustering
    draw_box(cx, 1.6, "4. Entity Clustering\n(co-spend + change)", "#0D47A1")

    # ROW 5 (y=-0.2): Step 5 - Risk Scoring + OFAC side by side
    draw_box(5.5, -0.2, "5. Risk Scoring\n(BFS + Haircut + Exposure)", "#E65100", w=3.6)
    draw_input(12.5, -0.2, "OFAC SDN\nList")

    # OUTPUTS at bottom corners
    draw_box(3.0, -0.2, "Validation\n(ROC/AUC)", "#2E7D32", w=2.2, h=0.9, fontsize=9)
    draw_box(12.5, -0.2, "OFAC SDN\nList", "#ECEFF1", w=2.2, h=0.9, fontsize=9)

    # Actually, let me redo this more cleanly. I'll erase and redo.
    # Clear and start fresh with ax
    ax.clear()
    ax.set_xlim(0, 16)
    ax.set_ylim(-2.5, 10)
    ax.axis("off")

    # Y positions for each row (top to bottom)
    y_title = 9.5
    y_src = 8.2
    y_s1 = 6.3
    y_s2 = 4.6
    y_s3 = 2.9
    y_out = 0.8
    y_bot = -1.0

    # Title
    ax.text(8, y_title, "Data Pipeline Architecture", fontsize=17, fontweight="bold",
            ha="center", color="#11151A")

    # ── Row: Data Sources ──
    draw_input(2.5, y_src, "GraphSense\nTagPacks")
    draw_input(8.0, y_src, "Custom DOJ\nTagPacks")
    draw_input(13.5, y_src, "mempool.space\nAPI")

    # ── Row: Step 1 ──
    draw_box(5.25, y_s1, "1. Load & Label", "#1565C0", w=3.0)
    ax.text(5.25, y_s1 - 0.75, "Parse YAML TagPacks → address labels", fontsize=8,
            ha="center", color="#546E7A")

    # ── Row: Step 2 ──
    draw_box(11.0, y_s1, "2. BFS Crawl", "#1565C0", w=3.0)
    ax.text(11.0, y_s1 - 0.75, "Fetch tx neighbourhood from mempool.space", fontsize=8,
            ha="center", color="#546E7A")

    # ── Row: Step 3 ──
    draw_box(8.0, y_s2, "3. Build Transaction Graph", "#0D47A1", w=4.5)
    ax.text(8.0, y_s2 - 0.75, "Directed edges with proportional value attribution", fontsize=8,
            ha="center", color="#546E7A")

    # ── Row: Step 4 ──
    draw_box(8.0, y_s3, "4. Entity Clustering", "#0D47A1", w=4.5)
    ax.text(8.0, y_s3 - 0.75, "Union-Find: co-spend heuristic + change-address detection", fontsize=8,
            ha="center", color="#546E7A")

    # ── Row: Step 5 ──
    draw_box(8.0, y_out, "5. Risk Scoring", "#E65100", w=4.5)
    ax.text(8.0, y_out - 0.75, "BFS Distance + Direct Exposure + Haircut Taint → Aggregate 0–100",
            fontsize=8, ha="center", color="#546E7A")

    # ── Bottom Row: Outputs side by side ──
    draw_input(3.5, y_bot, "OFAC SDN List\n(ground truth)")
    draw_box(8.0, y_bot, "Validation\n(ROC / AUC)", "#2E7D32", w=2.8)
    draw_box(13.0, y_bot, "Dashboard\n& Report", "#6A1B9A", w=2.8)

    # ═══ ARROWS ═══
    # Sources → Step 1
    arrow_down(2.5, y_src - 0.55, 4.2, y_s1 + 0.55)
    arrow_down(8.0, y_src - 0.55, 6.0, y_s1 + 0.55)
    # Source → Step 2
    arrow_down(13.5, y_src - 0.55, 11.5, y_s1 + 0.55)

    # Step 1 → Step 3
    arrow_down(5.25, y_s1 - 0.55, 6.8, y_s2 + 0.55)
    # Step 2 → Step 3
    arrow_down(11.0, y_s1 - 0.55, 9.2, y_s2 + 0.55)

    # Step 3 → Step 4
    arrow_down(8.0, y_s2 - 0.55, 8.0, y_s3 + 0.55)

    # Step 4 → Step 5
    arrow_down(8.0, y_s3 - 0.55, 8.0, y_out + 0.55)

    # Step 5 → Validation
    arrow_down(6.8, y_out - 0.55, 7.5, y_bot + 0.55)
    # Step 5 → Dashboard
    arrow_down(9.2, y_out - 0.55, 12.0, y_bot + 0.55)
    # OFAC → Validation
    arrow_right(4.8, y_bot, 6.6, y_bot, color="#2E7D32")

    # ── Legend ──
    ax.text(8, 9.0,
            "Dashed = external data  |  Blue = processing  |  "
            "Orange = scoring  |  Green = validation  |  Purple = output",
            fontsize=8.5, ha="center", color="#78909C")

    fig.tight_layout()
    fig.savefig(OUT / "fig_pipeline.png")
    plt.close(fig)
    print("  Saved fig_pipeline.png")


# ═══════════════════════════════════════════════════════════════════════
# FIG 2: Transaction Graph Visualization (Bitfinex — hero figure)
# ═══════════════════════════════════════════════════════════════════════

def fig_graph_viz(case_data: dict):
    slug = "bitfinex_hack"
    if slug not in case_data:
        print("  SKIP fig_graph_viz (no bitfinex data)")
        return

    cd = case_data[slug]
    df = cd["addr"]

    from pof.cases import get_case
    from pof.clustering import cluster_addresses
    from pof.explorer import Explorer, crawl_neighborhood
    from pof.tagpacks import discover_tagpack_files, load_tagpacks
    from pof.graph import build_graph

    tagpack_dirs = [
        PROJECT / "data" / "tagpacks" / "graphsense-tagpacks" / "packs",
        PROJECT / "data" / "tagpacks" / "custom",
    ]
    all_files = []
    for d in tagpack_dirs:
        if d.exists():
            all_files += discover_tagpack_files(d)
    tags = load_tagpacks(all_files)

    case = get_case(slug)
    explorer = Explorer(cache_path=PROJECT / "data" / "cache" / "explorer.sqlite")
    txs = crawl_neighborhood(explorer, case.seed_addresses, hops=1, max_tx_per_addr=15)
    g = build_graph(txs, tags=tags)

    scores = df["score"].to_dict()
    severities = {n: d.get("severity", 0.0) for n, d in g.nodes(data=True)}

    if g.number_of_nodes() > 500:
        top_nodes = sorted(scores.keys(), key=lambda x: scores.get(x, 0), reverse=True)[:300]
        seed_set = set(case.seed_addresses)
        keep = set(top_nodes) | seed_set
        for n in seed_set:
            if n in g:
                keep |= set(g.predecessors(n)) | set(g.successors(n))
        g = g.subgraph(keep).copy()

    node_scores = np.array([scores.get(n, 0) for n in g.nodes()])
    node_sev = np.array([severities.get(n, 0) for n in g.nodes()])

    fig, ax = plt.subplots(figsize=(12, 10))
    ax.set_facecolor("#1a1a2e")
    fig.patch.set_facecolor("#1a1a2e")

    pos = nx.spring_layout(g, k=0.8, iterations=80, seed=42)

    nx.draw_networkx_edges(g, pos, ax=ax, alpha=0.15, edge_color="#4a4a6a",
                           width=0.3, arrows=True, arrowsize=4)

    cmap = plt.cm.YlOrRd
    node_colors = cmap(node_scores / max(node_scores.max(), 1))
    sizes = 8 + node_scores * 3

    tainted_mask = node_sev > 0
    normal_mask = ~tainted_mask

    nodes_list = list(g.nodes())
    normal_nodes = [n for n, m in zip(nodes_list, normal_mask) if m]
    tainted_nodes = [n for n, m in zip(nodes_list, tainted_mask) if m]

    if normal_nodes:
        normal_idx = [nodes_list.index(n) for n in normal_nodes]
        nx.draw_networkx_nodes(g, pos, nodelist=normal_nodes, ax=ax,
                               node_color=[node_colors[i] for i in normal_idx],
                               node_size=[sizes[i] for i in normal_idx],
                               linewidths=0, alpha=0.8)

    if tainted_nodes:
        tainted_idx = [nodes_list.index(n) for n in tainted_nodes]
        nx.draw_networkx_nodes(g, pos, nodelist=tainted_nodes, ax=ax,
                               node_color=[node_colors[i] for i in tainted_idx],
                               node_size=[max(sizes[i] * 2, 60) for i in tainted_idx],
                               linewidths=2.0, edgecolors="#ff4444", alpha=0.95)

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, max(node_scores.max(), 1)))
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, shrink=0.6, aspect=20, pad=0.02)
    cbar.set_label("Risk Score (0-100)", color="white", fontsize=10)
    cbar.ax.yaxis.set_tick_params(color="white")
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color="white")

    legend_elements = [
        plt.scatter([], [], c="#ff4444", s=80, edgecolors="#ff4444",
                    linewidths=2, label="Tainted (tagged source)"),
        plt.scatter([], [], c="#fee08b", s=30, edgecolors="none",
                    label="Low risk"),
        plt.scatter([], [], c="#d73027", s=50, edgecolors="none",
                    label="High risk"),
    ]
    legend = ax.legend(handles=legend_elements, loc="lower left",
                       facecolor="#2a2a4e", edgecolor="#4a4a6a",
                       labelcolor="white", fontsize=9)

    ax.set_title(f"Bitfinex Hack — Transaction Graph ({g.number_of_nodes()} nodes)\n"
                 f"Node color = risk score, red borders = tagged tainted sources",
                 color="white", fontsize=13, fontweight="bold", pad=15)
    ax.axis("off")

    fig.savefig(OUT / "fig_graph_viz.png", facecolor="#1a1a2e")
    plt.close(fig)
    print(f"  Saved fig_graph_viz.png ({g.number_of_nodes()} nodes)")


# ═══════════════════════════════════════════════════════════════════════
# FIG 3: Taint Propagation Decay
# ═══════════════════════════════════════════════════════════════════════

def fig_taint_decay(case_data: dict):
    from pof.cases import get_case
    from pof.clustering import cluster_addresses
    from pof.explorer import Explorer, crawl_neighborhood
    from pof.tagpacks import discover_tagpack_files, load_tagpacks
    from pof.graph import build_graph
    from pof.metrics.distance import distance_to_tainted

    tagpack_dirs = [
        PROJECT / "data" / "tagpacks" / "graphsense-tagpacks" / "packs",
        PROJECT / "data" / "tagpacks" / "custom",
    ]
    all_files = []
    for d in tagpack_dirs:
        if d.exists():
            all_files += discover_tagpack_files(d)
    tags = load_tagpacks(all_files)

    fig, axes = plt.subplots(2, 2, figsize=(13, 10))
    axes = axes.flatten()

    for idx, (slug, cd) in enumerate(case_data.items()):
        case = get_case(slug)
        explorer = Explorer(cache_path=PROJECT / "data" / "cache" / "explorer.sqlite")
        txs = crawl_neighborhood(explorer, case.seed_addresses, hops=1, max_tx_per_addr=15)
        g = build_graph(txs, tags=tags)

        dist = distance_to_tainted(g)
        scores = cd["addr"]["score"].to_dict()

        hop_data: dict[int, list[float]] = {}
        for node, d in dist.items():
            if d >= 0 and node in scores:
                hop_data.setdefault(d, []).append(scores[node])

        hops_sorted = sorted(h for h in hop_data if h <= 8)
        if not hops_sorted:
            continue

        means = [np.mean(hop_data[h]) for h in hops_sorted]
        medians = [np.median(hop_data[h]) for h in hops_sorted]
        counts = [len(hop_data[h]) for h in hops_sorted]
        maxes = [np.max(hop_data[h]) for h in hops_sorted]

        ax = axes[idx]
        ax2 = ax.twinx()

        bars = ax2.bar(hops_sorted, counts, alpha=0.2, color=PAL["light"],
                       label="Node count", zorder=1)
        ax.plot(hops_sorted, means, "o-", color=PAL["primary"], linewidth=2.5,
                markersize=7, label="Mean score", zorder=3)
        ax.plot(hops_sorted, maxes, "s--", color=PAL["danger"], linewidth=1.5,
                markersize=5, alpha=0.7, label="Max score", zorder=3)
        ax.fill_between(hops_sorted, 0, means, alpha=0.1, color=PAL["primary"])

        ax.set_xlabel("Hops from Tainted Source")
        ax.set_ylabel("Risk Score")
        ax2.set_ylabel("Node Count", color=PAL["neutral"])
        ax.set_title(cd["name"], fontweight="bold")
        ax.set_xlim(-0.3, max(hops_sorted) + 0.3)
        ax.set_ylim(bottom=0)

        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=8)

    fig.suptitle("Taint Propagation: How Risk Decays with Distance",
                 fontsize=14, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(OUT / "fig_taint_decay.png")
    plt.close(fig)
    print("  Saved fig_taint_decay.png")


# ═══════════════════════════════════════════════════════════════════════
# FIG 4: Fixed ROC Curves
# ═══════════════════════════════════════════════════════════════════════

def fig_roc(case_data: dict, ofac_addrs: set[str]):
    fig, axes = plt.subplots(2, 2, figsize=(13, 12))
    axes = axes.flatten()

    annotations = {
        "wannacry": "Perfect separation:\nall 4 tainted addresses\nscore higher than all\n426K clean addresses.",
        "twitter_hack": "Near-perfect: 3 tagged\nscam addresses cleanly\nseparated from 7,938\nnon-tagged addresses.",
        "colonial_pipeline": "Only 2 positives (1 DOJ\n+ 1 OFAC). Diagonal shape\nshows limited tag coverage\nfor RaaS affiliate model.",
        "bitfinex_hack": "Strong separation: 8\ntagged hack addresses\nscore well above most\nof the 599 clean nodes.",
    }

    for idx, (slug, cd) in enumerate(case_data.items()):
        df = cd["addr"]
        addrs_in_graph = set(df.index)
        ofac_in = ofac_addrs & addrs_in_graph

        positive = set(df[df["severity"] > 0].index) | ofac_in
        negative = set(df[df["severity"] < 0.01].index) - positive

        result = evaluate_scores(
            df, positive_addrs=positive, negative_addrs=negative,
            thresholds=[10, 25, 50, 75],
        )

        ax = axes[idx]
        roc = result["roc_points"]
        if roc:
            fprs = [p[0] for p in roc]
            tprs = [p[1] for p in roc]
            ax.fill_between(fprs, 0, tprs, alpha=0.12, color=PAL["primary"], step="post")
            ax.plot(fprs, tprs, color=PAL["primary"], linewidth=2.5, drawstyle="steps-post",
                    label=f"AUC = {result['auc']:.3f}")
        ax.plot([0, 1], [0, 1], "k--", alpha=0.25, linewidth=1, label="Random (AUC = 0.5)")

        ax.set_xlabel("False Positive Rate")
        ax.set_ylabel("True Positive Rate")
        n_p = result["n_positive"]
        n_n = result["n_negative"]
        ax.set_title(f"{cd['name']}\n{n_p} known-bad vs {n_n:,} unlabeled addresses")

        if slug in annotations:
            ax.text(0.62, 0.15, annotations[slug],
                    transform=ax.transAxes, fontsize=7.5, color="#455A64",
                    bbox=dict(boxstyle="round,pad=0.4", facecolor="#F5F5F5",
                              edgecolor="#BDBDBD", alpha=0.9),
                    verticalalignment="bottom")

        ax.set_xlim(-0.02, 1.02)
        ax.set_ylim(-0.02, 1.02)
        ax.legend(loc="lower right", fontsize=9, framealpha=0.9)
        ax.set_aspect("equal")

    fig.suptitle("ROC Curves: Aggregate Risk Score as Binary Classifier\n"
                 "Sharp corners are expected with very few positives (3–8) vs thousands of negatives",
                 fontsize=13, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(OUT / "fig_roc.png")
    plt.close(fig)
    print("  Saved fig_roc.png")


# ═══════════════════════════════════════════════════════════════════════
# FIG 5: Clustering Impact — bar charts
# ═══════════════════════════════════════════════════════════════════════

def fig_clustering(case_data: dict):
    names = [cd["name"] for cd in case_data.values()]
    n_addr = [len(cd["addr"]) for cd in case_data.values()]
    n_entity = [len(cd["entity"]) for cd in case_data.values()]
    reduction = [(1 - e / max(a, 1)) * 100 for a, e in zip(n_addr, n_entity)]
    mean_a = [cd["addr"]["score"].mean() for cd in case_data.values()]
    mean_e = [cd["entity"]["score"].mean() for cd in case_data.values()]
    shift = [e - a for a, e in zip(mean_a, mean_e)]

    short_names = ["WannaCry", "Twitter\nHack", "Colonial\nPipeline", "Bitfinex\nHack"]

    fig, axes = plt.subplots(1, 3, figsize=(17, 6))

    # Panel 1: Node counts (before vs after clustering)
    ax = axes[0]
    x = np.arange(len(short_names))
    w = 0.35
    bars1 = ax.bar(x - w/2, n_addr, w, label="Before (Addresses)", color=PAL["primary"], alpha=0.85)
    bars2 = ax.bar(x + w/2, n_entity, w, label="After (Entities)", color=PAL["secondary"], alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(short_names, fontsize=9)
    ax.set_ylabel("Node Count (log scale)")
    ax.set_title("Graph Size Before vs After Clustering")
    ax.set_yscale("log")
    ax.legend(fontsize=9, loc="upper right")
    for bar, val in zip(bars1, n_addr):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                f"{val:,}", ha="center", va="bottom", fontsize=7, color=PAL["primary"])
    for bar, val in zip(bars2, n_entity):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                f"{val:,}", ha="center", va="bottom", fontsize=7, color=PAL["secondary"])

    # Panel 2: Reduction %
    ax = axes[1]
    colors = [PAL["accent"], PAL["secondary"], PAL["primary"], "#6A1B9A"]
    bars = ax.bar(short_names, reduction, color=colors, alpha=0.85)
    for bar, val in zip(bars, reduction):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.2,
                f"{val:.1f}%", ha="center", va="bottom", fontweight="bold", fontsize=10)
    ax.set_ylabel("Reduction (%)")
    ax.set_title("Node Count Reduction\n(higher = more addresses merged)")
    ax.set_ylim(0, max(reduction) * 1.2)

    # Panel 3: Score shift
    ax = axes[2]
    bar_colors = [PAL["accent"] if s > 0 else PAL["danger"] for s in shift]
    bars = ax.bar(short_names, shift, color=bar_colors, alpha=0.85)
    ax.axhline(y=0, color="black", linewidth=0.8)
    for bar, val in zip(bars, shift):
        y = bar.get_height()
        label = f"+{val:.2f}" if val > 0 else f"{val:.2f}"
        offset = abs(max(shift) - min(shift)) * 0.05
        ax.text(bar.get_x() + bar.get_width()/2,
                y + offset * (1 if y >= 0 else -1),
                label, ha="center", va="bottom" if y >= 0 else "top",
                fontweight="bold", fontsize=10)
    ax.set_ylabel("Mean Score Change (entity − address)")
    ax.set_title("Risk Concentration Effect\n(positive = risk concentrates)")
    y_pad = max(abs(max(shift)), abs(min(shift))) * 0.3
    ax.set_ylim(min(shift) - y_pad, max(shift) + y_pad)

    fig.suptitle("Impact of Entity Clustering on Risk Analysis",
                 fontsize=14, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    fig.savefig(OUT / "fig_clustering.png")
    plt.close(fig)
    print("  Saved fig_clustering.png")


# ═══════════════════════════════════════════════════════════════════════
# FIG 6: Score Distributions — histograms of ALL scores (including zero)
# ═══════════════════════════════════════════════════════════════════════

def fig_distributions(case_data: dict):
    fig, axes = plt.subplots(2, 2, figsize=(14, 11))
    axes = axes.flatten()

    bins = np.concatenate([[-0.5, 0.5], np.arange(5, 101, 5)])

    for idx, (slug, cd) in enumerate(case_data.items()):
        ax = axes[idx]

        addr_s = cd["addr"]["score"].values
        entity_s = cd["entity"]["score"].values

        ax.hist(addr_s, bins=bins, alpha=0.7, color=PAL["primary"],
                label=f"Addresses (n={len(addr_s):,})", edgecolor="white", linewidth=0.5)
        ax.hist(entity_s, bins=bins, alpha=0.55, color=PAL["secondary"],
                label=f"Entities (n={len(entity_s):,})", edgecolor="white", linewidth=0.5)

        ax.set_yscale("log")
        ax.set_xlabel("Aggregate Risk Score (0–100)")
        ax.set_ylabel("Count (log scale)")
        ax.set_title(cd["name"], fontweight="bold")
        ax.set_xlim(-2, 102)
        ax.legend(fontsize=9, loc="upper right")

        n_addr_nz = int((addr_s > 0.1).sum())
        n_ent_nz = int((entity_s > 0.1).sum())
        pct_addr = n_addr_nz / max(len(addr_s), 1) * 100
        pct_ent = n_ent_nz / max(len(entity_s), 1) * 100
        mean_nz_addr = addr_s[addr_s > 0.1].mean() if n_addr_nz > 0 else 0
        mean_nz_ent = entity_s[entity_s > 0.1].mean() if n_ent_nz > 0 else 0

        ax.text(0.98, 0.55,
                f"Non-zero scores:\n"
                f"  Addr: {n_addr_nz:,} ({pct_addr:.2f}%)\n"
                f"  Entity: {n_ent_nz:,} ({pct_ent:.2f}%)\n"
                f"Mean (non-zero):\n"
                f"  Addr: {mean_nz_addr:.1f}\n"
                f"  Entity: {mean_nz_ent:.1f}",
                transform=ax.transAxes, fontsize=8, color="#37474F",
                ha="right", va="top", family="monospace",
                bbox=dict(boxstyle="round,pad=0.4", facecolor="#FAFAFA",
                          edgecolor="#BDBDBD", alpha=0.92))

    fig.suptitle(
        "Risk Score Distributions: Address-Level vs Entity-Level\n"
        "All scores shown (including zero). Y-axis is log-scaled. "
        "First bar is the zero-score bin.",
        fontsize=12, fontweight="bold",
    )
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    fig.savefig(OUT / "fig_distributions.png")
    plt.close(fig)
    print("  Saved fig_distributions.png")


# ═══════════════════════════════════════════════════════════════════════
# FIG 7: Deep-dive — Bitfinex fund flow
# ═══════════════════════════════════════════════════════════════════════

def fig_deepdive(case_data: dict):
    slug = "bitfinex_hack"
    if slug not in case_data:
        print("  SKIP fig_deepdive")
        return

    cd = case_data[slug]
    df = cd["addr"]

    score_bins = [0, 1, 10, 25, 50, 75, 100.01]
    bin_labels = ["0", "1-10", "10-25", "25-50", "50-75", "75-100"]
    df_copy = df.copy()
    df_copy["risk_bin"] = pd.cut(df_copy["score"], bins=score_bins, labels=bin_labels, right=False)
    bin_counts = df_copy["risk_bin"].value_counts().reindex(bin_labels).fillna(0)

    total = len(df)
    high_risk = (df["score"] >= 50).sum()
    tainted = (df["severity"] > 0).sum()

    fig, axes = plt.subplots(1, 3, figsize=(16, 5.5))

    # Panel 1: Risk score histogram
    ax = axes[0]
    colors_bars = ["#4CAF50", "#8BC34A", "#FFC107", "#FF9800", "#FF5722", "#D32F2F"]
    ax.bar(bin_labels, bin_counts.values, color=colors_bars, edgecolor="#37474F",
           linewidth=0.5, alpha=0.85)
    for i, (lbl, cnt) in enumerate(zip(bin_labels, bin_counts.values)):
        if cnt > 0:
            ax.text(i, cnt + total * 0.01, f"{int(cnt)}", ha="center",
                    fontsize=8, fontweight="bold")
    ax.set_xlabel("Risk Score Range")
    ax.set_ylabel("Number of Addresses")
    ax.set_title("Bitfinex: Score Distribution")

    # Panel 2: Key stats card
    ax = axes[1]
    ax.axis("off")
    stats = [
        ("Total Addresses", f"{total:,}"),
        ("Tainted Sources", f"{tainted}"),
        ("High Risk (>50)", f"{high_risk}"),
        ("Mean Score", f"{df['score'].mean():.2f}"),
        ("Median Score", f"{df['score'].median():.2f}"),
        ("Max Score", f"{df['score'].max():.1f}"),
        ("% Non-zero", f"{(df['score'] > 0).mean() * 100:.1f}%"),
    ]
    y_pos = 0.92
    ax.text(0.5, 0.98, "Bitfinex Hack — Key Statistics",
            ha="center", va="top", fontsize=12, fontweight="bold",
            transform=ax.transAxes)
    for label, value in stats:
        ax.text(0.15, y_pos - 0.03, label, fontsize=10,
                transform=ax.transAxes, va="top", color="#546E7A")
        ax.text(0.85, y_pos - 0.03, value, fontsize=10, fontweight="bold",
                transform=ax.transAxes, va="top", ha="right", color="#11151A")
        y_pos -= 0.115
    ax.add_patch(FancyBboxPatch((0.05, 0.05), 0.9, 0.93,
                                boxstyle="round,pad=0.02",
                                facecolor="#F5F5F5", edgecolor="#BDBDBD",
                                transform=ax.transAxes, linewidth=1.2))

    # Panel 3: Severity category breakdown
    ax = axes[2]
    sev_data = df["severity"].value_counts().sort_index()
    if len(sev_data) > 1:
        sev_labels = [f"Severity {s:.1f}" if s > 0 else "Clean (0.0)" for s in sev_data.index]
        sev_colors = ["#4CAF50" if s == 0 else "#FF5722" if s >= 0.8 else "#FFC107"
                      for s in sev_data.index]
        wedges, texts, autotexts = ax.pie(
            sev_data.values, labels=sev_labels, colors=sev_colors,
            autopct=lambda p: f"{p:.1f}%" if p > 2 else "",
            startangle=90, textprops={"fontsize": 8})
        ax.set_title("Severity Breakdown")
    else:
        ax.text(0.5, 0.5, f"All nodes: severity={sev_data.index[0]:.1f}",
                ha="center", va="center", transform=ax.transAxes)
        ax.set_title("Severity Breakdown")

    fig.suptitle("Deep Dive: Bitfinex Hack (2016) — Largest DOJ Crypto Seizure",
                 fontsize=14, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(OUT / "fig_deepdive.png")
    plt.close(fig)
    print("  Saved fig_deepdive.png")


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    print("Loading case data...")
    case_data = load_case_data()
    ofac_addrs = load_ofac()
    print(f"  {len(case_data)} cases, {len(ofac_addrs)} OFAC addresses\n")

    print("Generating figures...")
    fig_pipeline()
    fig_roc(case_data, ofac_addrs)
    fig_clustering(case_data)
    fig_distributions(case_data)
    fig_taint_decay(case_data)
    fig_graph_viz(case_data)
    fig_deepdive(case_data)

    print(f"\nAll figures saved to {OUT}")


if __name__ == "__main__":
    main()
