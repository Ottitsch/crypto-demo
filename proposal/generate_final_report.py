"""
Generate the full Proof of Funds final report as a multi-page A4 PDF.

Mirrors the visual style of generate_presentation_pdf.py (monochrome palette,
grey cards, black table headers, TU Wien Informatics logo, thin rules).

Run:
    python proposal/generate_final_report.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

PAGE_W, PAGE_H = A4
LEFT_MARGIN = 14 * mm
RIGHT_MARGIN = 14 * mm
CONTENT_W = PAGE_W - LEFT_MARGIN - RIGHT_MARGIN

ACCENT = colors.HexColor("#3A3F47")
INK = colors.HexColor("#11151A")
MUTED = colors.HexColor("#586471")
LINE = colors.HexColor("#D8DDE3")
PANEL = colors.HexColor("#F3F5F7")
PANEL_ALT = colors.HexColor("#FAFAFA")
WHITE = colors.white

FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
FONT_ITALIC = "Helvetica-Oblique"

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
LOGO_PATH = SCRIPT_DIR / "assets" / "tu_wien_informatics_logo.png"
RESULTS_DIR = PROJECT_ROOT / "data" / "results"

styles = getSampleStyleSheet()


def _style(name, parent="Normal", **kw):
    return ParagraphStyle(name, parent=styles[parent], **kw)


TITLE_STYLE = _style("RTitle", fontName=FONT_BOLD, fontSize=20, leading=24, textColor=INK)
SUBTITLE = _style("RSub", fontName=FONT_ITALIC, fontSize=10, leading=13, textColor=MUTED)
BODY = _style("RBody", fontName=FONT, fontSize=8.85, leading=11.4, textColor=INK, alignment=TA_LEFT)
SMALL = _style("RSmall", fontName=FONT, fontSize=8.25, leading=10.4, textColor=INK)
MUTED_SMALL = _style("RMuted", fontName=FONT, fontSize=7.45, leading=9.4, textColor=MUTED)
SECTION = _style("RSec", fontName=FONT_BOLD, fontSize=10, leading=12, textColor=INK, spaceBefore=4*mm, spaceAfter=2*mm)
SUBSECTION = _style("RSubsec", fontName=FONT_BOLD, fontSize=8.9, leading=10.8, textColor=INK, spaceBefore=3*mm, spaceAfter=1.6*mm)
CARD_TITLE = _style("RCard", fontName=FONT_BOLD, fontSize=9.1, leading=11, textColor=INK, spaceAfter=0.8*mm)
TABLE_HEAD = _style("RTHead", fontName=FONT_BOLD, fontSize=7.75, leading=9.3, textColor=WHITE)
TABLE_CELL = _style("RTCell", fontName=FONT, fontSize=7.75, leading=9.45, textColor=INK)
TABLE_CELL_BOLD = _style("RTCellB", fontName=FONT_BOLD, fontSize=7.75, leading=9.45, textColor=INK)
CAPTION = _style("RCaption", fontName=FONT_ITALIC, fontSize=7.5, leading=9, textColor=MUTED, alignment=TA_CENTER, spaceBefore=1*mm, spaceAfter=2*mm)


def p(text, ps=BODY):
    return Paragraph(text, ps)


def spacer(h):
    return Spacer(1, h * mm)


def section(title):
    return p(title.upper(), SECTION)


def subsection(title):
    return p(title, SUBSECTION)


def rule(after=3.0):
    return HRFlowable(width="100%", thickness=0.45*mm, color=INK, spaceBefore=0, spaceAfter=after*mm)


def panel(title, body):
    tbl = Table([[""], [[p(title, CARD_TITLE), p(body, BODY)]]], colWidths=[CONTENT_W], rowHeights=[1.0*mm, None])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,0), ACCENT),
        ("BACKGROUND", (0,1), (0,1), PANEL),
        ("BOX", (0,1), (0,1), 0.25*mm, LINE),
        ("LEFTPADDING", (0,0), (0,0), 0), ("RIGHTPADDING", (0,0), (0,0), 0),
        ("TOPPADDING", (0,0), (0,0), 0), ("BOTTOMPADDING", (0,0), (0,0), 0),
        ("LEFTPADDING", (0,1), (0,1), 3*mm), ("RIGHTPADDING", (0,1), (0,1), 3*mm),
        ("TOPPADDING", (0,1), (0,1), 2.2*mm), ("BOTTOMPADDING", (0,1), (0,1), 2.2*mm),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))
    return tbl


def make_table(rows, widths, first_col_bold=True):
    data = []
    for ri, row in enumerate(rows):
        rendered = []
        for ci, cell in enumerate(row):
            if ri == 0:
                rendered.append(p(cell, TABLE_HEAD))
            elif first_col_bold and ci == 0:
                rendered.append(p(cell, TABLE_CELL_BOLD))
            else:
                rendered.append(p(cell, TABLE_CELL))
        data.append(rendered)
    tbl = Table(data, colWidths=widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), INK),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [WHITE, PANEL_ALT]),
        ("GRID", (0,0), (-1,-1), 0.25*mm, LINE),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 1.35*mm),
        ("RIGHTPADDING", (0,0), (-1,-1), 1.35*mm),
        ("TOPPADDING", (0,0), (-1,-1), 1.0*mm),
        ("BOTTOMPADDING", (0,0), (-1,-1), 1.0*mm),
    ]))
    return tbl


def figure(path: Path, caption: str, max_width_mm: float = 170):
    """Embed a figure preserving its native aspect ratio."""
    elems = []
    if path.exists():
        with PILImage.open(path) as img:
            pw, ph = img.size
        aspect = ph / pw
        w = max_width_mm * mm
        h = w * aspect
        max_h = 130 * mm
        if h > max_h:
            h = max_h
            w = h / aspect
        im = Image(str(path), width=w, height=h)
        im.hAlign = "CENTER"
        elems.append(im)
    else:
        elems.append(p(f"[Figure not found: {path.name}]", MUTED_SMALL))
    elems.append(p(caption, CAPTION))
    return elems


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.25*mm)
    canvas.line(LEFT_MARGIN, 10*mm, PAGE_W - RIGHT_MARGIN, 10*mm)
    canvas.setFillColor(MUTED)
    canvas.setFont(FONT, 7)
    canvas.drawString(LEFT_MARGIN, 6.2*mm, "Crypto Asset Analytics — Proof of Funds — Final Report")
    canvas.drawRightString(PAGE_W - RIGHT_MARGIN, 6.2*mm, f"{doc.page}")
    canvas.restoreState()


# ═══════════════════════════════════════════════════════════════════════

def build_story():
    s = []

    # ── Title ─────────────────────────────────────────────────────────
    title_parts = [
        p("Proof of Funds: Final Report", TITLE_STYLE),
        p("Bitcoin Risk Quantification for KYT / AML Compliance<br/>"
          "<font size=8>Crypto Asset Analytics — TU Wien Informatics — 2026S</font>", SUBTITLE),
    ]
    if LOGO_PATH.exists():
        logo = Image(str(LOGO_PATH), width=56*mm, height=8.4*mm)
        hdr = Table([[title_parts, logo]], colWidths=[CONTENT_W - 62*mm, 56*mm])
        hdr.setStyle(TableStyle([
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("ALIGN", (1,0), (1,0), "RIGHT"),
            ("LEFTPADDING", (0,0), (-1,-1), 0), ("RIGHTPADDING", (0,0), (-1,-1), 0),
            ("TOPPADDING", (0,0), (-1,-1), 0), ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ]))
        s += [hdr, rule()]
    else:
        s += title_parts + [rule()]

    # ══════════════════════════════════════════════════════════════════
    # 1. EXECUTIVE SUMMARY
    # ══════════════════════════════════════════════════════════════════
    s += [
        section("1. Executive Summary"),
        panel("Project Goal",
              "We built a fully functional Bitcoin <b>Proof of Funds</b> prototype for "
              "Know-Your-Transaction (KYT) / Anti-Money-Laundering (AML) screening. "
              "Starting from known high-risk seed addresses, the system crawls their "
              "transaction neighbourhood via the public mempool.space API, clusters "
              "addresses into real-world entities, and assigns each node an explainable "
              "0–100 risk score. The pipeline is validated against real-world ground truth "
              "(OFAC sanctions, DOJ court filings) and tested on four high-profile criminal cases."),
        spacer(2),
        make_table([
            ["Metric", "Value"],
            ["Tagged seed addresses", "46,000+ from GraphSense TagPacks + custom DOJ-sourced tags"],
            ["Case studies", "4 real criminal cases (WannaCry, Twitter Hack, Colonial Pipeline, Bitfinex)"],
            ["Addresses scored", "441,668 across all cases"],
            ["Entity clustering", "11–71% node reduction via co-spend + change heuristics"],
            ["Validation", "AUC up to 1.0 against OFAC/TagPack ground truth"],
            ["Code", "Python package with 41 unit tests, 3 notebooks, interactive dashboard"],
        ], [48*mm, CONTENT_W - 48*mm]),
    ]

    # ══════════════════════════════════════════════════════════════════
    # 2. RELATED WORK & CONTRIBUTIONS
    # ══════════════════════════════════════════════════════════════════
    s += [
        section("2. Related Work & Contributions"),
        subsection("2.1 Commercial and Academic Landscape"),
        p("Bitcoin transaction tracing is a well-studied problem with both commercial and academic solutions:", BODY),
        spacer(1),
        make_table([
            ["System", "Type", "Approach", "Limitation for Our Context"],
            ["Chainalysis Reactor",
             "Commercial",
             "Full-chain heuristic clustering + proprietary labels. Industry standard for law enforcement.",
             "Closed-source, expensive, not reproducible for academic work."],
            ["Elliptic",
             "Commercial",
             "GNN-based classification on transaction subgraphs. Published Elliptic dataset (200K nodes).",
             "Model is proprietary; dataset has no real addresses."],
            ["Crystal Blockchain",
             "Commercial",
             "Risk scoring with compliance dashboards. Used by exchanges.",
             "Closed-source, SaaS only."],
            ["Meiklejohn et al. (2013)",
             "Academic",
             "Pioneered common-input-ownership clustering. Manual ground truth via purchasing.",
             "No automated risk scoring; small scale."],
            ["Ron & Shamir (2013)",
             "Academic",
             "First large-scale Bitcoin graph analysis. Entity-level statistics.",
             "Descriptive only; no taint propagation or risk quantification."],
            ["Moeser et al. (2013)",
             "Academic",
             "Taint analysis for Bitcoin mixing services.",
             "Focused on CoinJoin; no general AML scoring pipeline."],
        ], [32*mm, 20*mm, 62*mm, CONTENT_W - 114*mm]),
        spacer(2),
        subsection("2.2 Our Contributions"),
        panel("What This Project Adds",
              "<b>Contribution 1 — Open-source end-to-end pipeline:</b> From raw TagPack YAML to a scored, "
              "clustered entity graph — fully reproducible, no API keys, no paid services.<br/><br/>"
              "<b>Contribution 2 — Entity clustering with quantified impact:</b> We implement and <i>measure</i> "
              "how co-spend and change-address heuristics affect risk scores (11–71% node reduction, risk "
              "concentration in 3/4 cases).<br/><br/>"
              "<b>Contribution 3 — Validation on real criminal cases:</b> We test against 4 DOJ-documented cases "
              "with known addresses and validate against the OFAC sanctions list — not synthetic data, but "
              "actual law-enforcement outcomes."),
    ]

    # ══════════════════════════════════════════════════════════════════
    # 3. DATA SOURCES
    # ══════════════════════════════════════════════════════════════════
    s += [
        section("3. Data Sources"),
        p("All data sources are <b>free and publicly accessible</b> — no API keys required.", BODY),
        spacer(1),
        make_table([
            ["Source", "Description", "Format"],
            ["GraphSense TagPacks", "Open address labels: ransomware, darknet markets, scams, hacks, exchanges. ~46K BTC.", "YAML"],
            ["Custom TagPacks (DOJ)", "Hand-curated from DOJ complaints for Twitter Hack 2020 and Colonial Pipeline 2021.", "YAML"],
            ["mempool.space API", "Public blockchain explorer REST API. Responses cached in SQLite.", "JSON"],
            ["OFAC SDN List", "US Treasury sanctioned crypto addresses. 81 BTC addresses from 0xB10C pre-extraction.", "TXT"],
            ["Ransomwhere", "Crowdsourced ransomware payment addresses and family labels.", "JSON"],
        ], [38*mm, CONTENT_W - 38*mm - 18*mm, 18*mm]),
    ]

    # ══════════════════════════════════════════════════════════════════
    # 4. METHODOLOGY — with pipeline diagram
    # ══════════════════════════════════════════════════════════════════
    s += [
        section("4. Methodology"),
        subsection("4.1 Data Pipeline"),
        p("The system follows a six-stage pipeline from raw data to validated risk scores:", BODY),
        spacer(1),
    ]
    s += figure(RESULTS_DIR / "fig_pipeline.png",
                "Figure 1 — End-to-end data pipeline. Grey dashed boxes are external inputs; "
                "blue boxes are processing stages; orange is scoring; green is validation.")

    s += [
        spacer(2),
        subsection("4.2 Risk Metrics"),
        make_table([
            ["Metric", "Approach", "Interpretation"],
            ["BFS Distance",
             "Shortest-path hops to nearest tainted predecessor (multi-source BFS).",
             "Proximity: fewer hops = higher risk."],
            ["Direct Exposure",
             "Fraction of 1-hop incoming value from tainted predecessors.",
             "How much money comes directly from bad actors."],
            ["Haircut Taint",
             "Multi-hop proportional propagation via sparse-matrix Jacobi iteration.",
             "How taint dilutes across the graph."],
            ["Aggregate Score",
             "Weighted blend: 0.3×Distance + 0.3×Exposure + 0.4×Haircut, scaled to 0–100.",
             "Single actionable score for compliance screening."],
        ], [30*mm, 68*mm, CONTENT_W - 98*mm]),
        spacer(2),
        subsection("4.3 Entity Clustering"),
        p("We implement two standard Bitcoin forensics heuristics (Meiklejohn et al., 2013) "
          "using a Union-Find data structure:", BODY),
        spacer(1),
        make_table([
            ["Heuristic", "Rule", "Rationale"],
            ["Common-input-ownership\n(Heuristic 1)",
             "All input addresses in the same transaction belong to the same entity.",
             "Spending from multiple addresses requires holding all private keys."],
            ["Change-address detection\n(Heuristic 2)",
             "A single-use output appearing for the first time is likely a change address.",
             "Standard wallet behaviour returns leftover value to a fresh address."],
        ], [38*mm, 64*mm, CONTENT_W - 102*mm]),
    ]

    s.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════
    # 5. TRANSACTION GRAPH VISUALIZATION
    # ══════════════════════════════════════════════════════════════════
    s += [
        section("5. Transaction Graph Visualization"),
        p("The core output of our system is a <b>directed, value-weighted transaction graph</b> "
          "where each node is a Bitcoin address and edges represent proportional value flow. "
          "Below we visualize the Bitfinex case — the 2016 hack that resulted in the largest "
          "DOJ cryptocurrency seizure ($3.6 billion).", BODY),
        spacer(2),
    ]
    s += figure(RESULTS_DIR / "fig_graph_viz.png",
                "Figure 2 — Bitfinex Hack transaction graph (300 highest-risk nodes). "
                "Color intensity = aggregate risk score (yellow→red). Red borders = tagged tainted sources. "
                "The graph shows how risk radiates outward from the hack addresses through the transaction network.")

    s.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════
    # 6. CASE STUDIES
    # ══════════════════════════════════════════════════════════════════
    s += [
        section("6. Forensic Case Studies"),
        p("We applied the full pipeline to <b>four real criminal cases</b> with publicly "
          "known Bitcoin addresses from DOJ filings and blockchain analytics reports.", BODY),
        spacer(1),
    ]

    cases = [
        ("WannaCry Ransomware (2017)",
         "Global ransomware attack infecting 200K+ computers across 150 countries. "
         "3 hardcoded BTC addresses collected ~$140K. Attributed to North Korea's Lazarus Group.",
         "426,535 addrs → 336,715 entities (21%)", "4", "88.66", "1.0000",
         "The WannaCry addresses are <b>perfectly separated</b> from all other nodes (AUC = 1.0). "
         "This is consistent with ransomware wallets that only receive victim payments and quickly "
         "consolidate — they form isolated high-risk clusters with no legitimate transaction history."),
        ("Twitter Hack (2020)",
         "Social engineering attack on Twitter employees. 130 VIP accounts compromised to post "
         "BTC doubling scam netting ~$117K. Three arrested within two weeks.",
         "7,941 addrs → 2,311 entities (71%)", "3", "84.37", "0.6666",
         "The Twitter hack shows the <b>highest clustering reduction</b> (71%) — the scammer "
         "consolidated funds aggressively, creating many co-spent address groups. The moderate AUC "
         "reflects that our custom DOJ TagPacks only tag 3 addresses; with fuller labeling from "
         "chain analysis firms, separation would improve."),
        ("Colonial Pipeline / DarkSide (2021)",
         "DarkSide ransomware shut down the largest US fuel pipeline for 6 days. Colonial paid "
         "75 BTC (~$4.4M). FBI seized 63.7 BTC from the affiliate's wallet.",
         "6,585 addrs → 4,229 entities (36%)", "1", "88.66", "0.4999",
         "The low AUC (0.50) reflects a <b>single tagged address</b> — the FBI seizure wallet. "
         "DarkSide used a sophisticated affiliate model that distributes ransom across many wallets, "
         "making single-address tagging insufficient. This demonstrates the importance of comprehensive "
         "labeling for ransomware-as-a-service operations."),
        ("Bitfinex Hack (2016)",
         "119,756 BTC stolen from Bitfinex exchange. Largest DOJ cryptocurrency seizure. "
         "Ilya Lichtenstein and Heather Morgan arrested in Feb 2022.",
         "607 addrs → 539 entities (11%)", "8", "88.00", "0.9381",
         "Strong AUC (0.94) despite a small graph — the hack addresses are well-tagged in GraphSense "
         "and the laundering chain within 1 hop is relatively short. The low clustering reduction (11%) "
         "suggests the laundering used <b>many separate wallets</b> rather than consolidating into "
         "co-spent clusters, consistent with known tumbling/peel-chain behavior."),
    ]

    for name, desc, graph_size, tainted, max_score, auc, insight in cases:
        s.append(KeepTogether([
            subsection(name),
            p(f"<i>{desc}</i>", BODY),
            spacer(1),
            make_table([
                ["Property", "Value"],
                ["Graph size", graph_size],
                ["Tainted nodes", tainted],
                ["Max score", max_score],
                ["Validation AUC", auc],
            ], [35*mm, CONTENT_W - 35*mm]),
            spacer(1),
            p(f"<b>Interpretation:</b> {insight}", BODY),
            spacer(2),
        ]))

    # ══════════════════════════════════════════════════════════════════
    # 7. TAINT PROPAGATION ANALYSIS
    # ══════════════════════════════════════════════════════════════════
    s += [
        section("7. Taint Propagation Analysis"),
        p("A key question is: <i>how quickly does risk decay as we move away from tainted sources?</i> "
          "Below we plot the mean and max risk score at each BFS hop distance, overlaid with the "
          "number of nodes at that distance.", BODY),
        spacer(2),
    ]
    s += figure(RESULTS_DIR / "fig_taint_decay.png",
                "Figure 3 — Risk score decay vs hop distance from tainted sources. "
                "Blue line = mean score; red dashes = max score; grey bars = node count. "
                "Risk drops sharply after 1–2 hops in most cases.")
    s += [
        spacer(2),
        panel("Key Finding",
              "Risk decays <b>rapidly with distance</b> — mean scores drop to near-zero within "
              "2–3 hops in all cases. However, <b>max scores remain elevated</b> at greater distances "
              "in the Bitfinex case, indicating that some laundering chains preserve risk further. "
              "This validates our multi-metric approach: distance alone would miss these extended "
              "taint paths, but the haircut propagation captures them."),
    ]

    s.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════
    # 8. VALIDATION RESULTS
    # ══════════════════════════════════════════════════════════════════
    s += [
        section("8. Validation Results"),
        p("We evaluate our aggregate risk score as a <b>binary classifier</b>: positives are "
          "addresses tagged as malicious (severity > 0) or found in the OFAC sanctions list; "
          "negatives are untagged addresses.", BODY),
        spacer(2),
    ]
    s += figure(RESULTS_DIR / "fig_roc.png",
                "Figure 4 — ROC curves for each case study. Shaded area = AUC. "
                "WannaCry achieves perfect separation (AUC = 1.0); Bitfinex is strong (0.94).")
    s += [
        spacer(2),
        subsection("Threshold Analysis"),
        make_table([
            ["Case", "Threshold", "Precision", "Recall", "F1"],
            ["WannaCry", "10", "0.444", "1.000", "0.615"],
            ["WannaCry", "50", "0.444", "1.000", "0.615"],
            ["Twitter Hack", "10", "0.600", "1.000", "0.750"],
            ["Twitter Hack", "50", "0.600", "1.000", "0.750"],
            ["Colonial Pipeline", "10", "0.333", "0.500", "0.400"],
            ["Colonial Pipeline", "50", "0.333", "0.500", "0.400"],
            ["Bitfinex", "10", "0.098", "1.000", "0.178"],
            ["Bitfinex", "50", "0.286", "1.000", "0.444"],
        ], [38*mm, 22*mm, 22*mm, 22*mm, 22*mm], first_col_bold=True),
        spacer(2),
        panel("Interpretation",
              "At threshold 50, the system achieves <b>perfect recall</b> (1.0) for WannaCry, "
              "Twitter Hack, and Bitfinex — every known-bad address is flagged. The precision/recall "
              "trade-off is typical for AML: in a graph of hundreds of thousands of addresses, even a "
              "small false-positive rate produces many false positives. A compliance team would use "
              "these scores for <b>prioritized manual review</b>, not automated blocking."),
    ]

    s.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════
    # 9. ENTITY CLUSTERING IMPACT
    # ══════════════════════════════════════════════════════════════════
    s += [
        section("9. Address-Level vs Entity-Level Analysis"),
        p("A key contribution is <b>entity clustering</b> — grouping addresses controlled "
          "by the same real-world actor. We quantify how this changes the risk landscape.", BODY),
        spacer(2),
    ]
    s += figure(RESULTS_DIR / "fig_clustering.png",
                "Figure 5 — Impact of entity clustering. Left: node count reduction (log scale). "
                "Center: percentage reduction. Right: mean risk score shift (green = risk concentrates).")
    s += [
        spacer(2),
        make_table([
            ["Case", "Addresses", "Entities", "Reduction", "Mean (addr)", "Mean (entity)", "Shift"],
            ["WannaCry", "426,535", "336,715", "21.1%", "0.0015", "0.0016", "+0.0001"],
            ["Twitter Hack", "7,941", "2,311", "70.9%", "0.0458", "0.1251", "+0.0793"],
            ["Colonial Pipeline", "6,585", "4,229", "35.8%", "0.0379", "0.0585", "+0.0206"],
            ["Bitfinex", "607", "539", "11.2%", "5.8988", "5.8754", "−0.0234"],
        ], [36*mm, 22*mm, 22*mm, 20*mm, 22*mm, 22*mm, CONTENT_W - 144*mm], first_col_bold=True),
        spacer(2),
    ]
    s += figure(RESULTS_DIR / "fig_distributions.png",
                "Figure 6 — Risk score distributions (histograms, log-scaled Y-axis) comparing address-level "
                "and entity-level analysis across all scores. The tall first bar represents zero-score nodes.")
    s += [
        spacer(2),
        panel("Finding",
              "In 3 of 4 cases, entity clustering <b>increases</b> mean risk — tainted funds "
              "are concentrated into fewer entity nodes. The Twitter Hack shows the strongest effect "
              "(71% reduction, +0.08 score shift) because the scammer consolidated aggressively. "
              "Bitfinex is the exception: its peel-chain laundering creates many separate wallets "
              "that don't co-spend, so clustering has minimal effect. This demonstrates that "
              "<b>clustering effectiveness depends on the laundering strategy</b>."),
    ]

    # ══════════════════════════════════════════════════════════════════
    # 10. DEEP DIVE: BITFINEX
    # ══════════════════════════════════════════════════════════════════
    s += [
        section("10. Deep Dive: Bitfinex Hack"),
        p("We examine the Bitfinex case in detail — the 2016 hack that led to the largest "
          "cryptocurrency seizure in DOJ history ($3.6 billion recovered in Feb 2022).", BODY),
        spacer(2),
    ]
    s += figure(RESULTS_DIR / "fig_deepdive.png",
                "Figure 7 — Bitfinex deep dive. Left: risk score distribution. Center: key statistics. "
                "Right: severity class breakdown.")
    s += [
        spacer(2),
        p("<b>What the scores reveal:</b> The Bitfinex graph has the highest mean score (5.90) across "
          "all cases — nearly 4x higher than the next (Twitter Hack at 0.05). This reflects the "
          "concentration of the graph: with only 607 addresses in the 1-hop neighbourhood, a large "
          "fraction (28 addresses, 4.6%) scores above 50. The 8 tagged tainted sources achieve near-maximum "
          "scores (88.0), and the risk propagates to ~46% of all addresses (non-zero scores). "
          "This is consistent with the known laundering pattern: Lichtenstein used a chain of small "
          "transactions to slowly move stolen funds, keeping the taint signal concentrated.", BODY),
    ]

    s.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════
    # 11. DELIVERABLES
    # ══════════════════════════════════════════════════════════════════
    s += [
        section("11. Deliverables"),
        make_table([
            ["Deliverable", "Description"],
            ["Python package (pof/)", "Modular library: tagpack loading, graph construction, entity clustering, 4 risk metrics, validation, and Streamlit dashboard. 41 unit tests."],
            ["Notebook 01: Methodology", "Narrative explanation of the pipeline, metric design, and score distributions."],
            ["Notebook 02: Case Studies", "Walk-through of 4 real forensic cases with crawling, clustering, scoring, and analysis."],
            ["Notebook 03: Validation", "OFAC SDN validation with ROC curves and address-vs-entity comparison."],
            ["Interactive Dashboard", "Streamlit app with 4 tabs: investigation, case studies, distributions, validation."],
            ["Precomputed Results", "Parquet files with scores for all cases + 7 publication-quality figures."],
        ], [42*mm, CONTENT_W - 42*mm]),
    ]

    # ══════════════════════════════════════════════════════════════════
    # 12. ARCHITECTURE
    # ══════════════════════════════════════════════════════════════════
    s += [
        section("12. Technical Architecture"),
        make_table([
            ["Module", "Purpose", "Key Implementation"],
            ["pof/tagpacks.py", "Load TagPack YAML files", "YAML parser with category mapping"],
            ["pof/explorer.py", "mempool.space API client", "SQLite response cache, rate limiting"],
            ["pof/clustering.py", "Entity clustering", "Union-Find with co-spend + change heuristics"],
            ["pof/graph.py", "Build transaction graph", "Proportional attribution, entity collapse"],
            ["pof/metrics/distance.py", "BFS distance metric", "Multi-source BFS on DiGraph"],
            ["pof/metrics/direct_exposure.py", "1-hop exposure", "Tainted-value fraction per node"],
            ["pof/metrics/haircut.py", "Multi-hop taint", "Sparse matrix Jacobi iteration"],
            ["pof/metrics/aggregate.py", "Final 0–100 score", "Weighted blend with severity modulation"],
            ["pof/validation.py", "Ground-truth evaluation", "OFAC/Ransomwhere loaders, ROC/AUC"],
            ["pof/cases.py", "Forensic case registry", "4 cases with DOJ-sourced addresses"],
            ["pof/dashboard.py", "Interactive UI", "Streamlit 4-tab investigation tool"],
            ["pof/precompute.py", "CLI pipeline", "End-to-end: load → crawl → cluster → score → save"],
        ], [38*mm, 38*mm, CONTENT_W - 76*mm]),
    ]

    # ══════════════════════════════════════════════════════════════════
    # 13. LIMITATIONS & FUTURE WORK
    # ══════════════════════════════════════════════════════════════════
    s += [
        section("13. Limitations & Future Work"),
        make_table([
            ["Limitation", "Impact", "Possible Extension"],
            ["Bounded BFS crawl", "May miss distant taint paths.", "Full-chain analysis with a local Bitcoin node."],
            ["Basic clustering heuristics", "CoinJoin and sophisticated mixing defeats detection.", "Advanced heuristics, CoinJoin detection."],
            ["Illustrative weights", "Not calibrated to a regulatory regime.", "Threshold calibration with expert labels."],
            ["Bitcoin only", "No Ethereum, Monero, or cross-chain.", "Multi-chain extension with bridge tracking."],
            ["Static snapshot", "Scores reflect crawl time, not real-time.", "Temporal risk decay model."],
        ], [36*mm, 52*mm, CONTENT_W - 88*mm]),
    ]

    # ══════════════════════════════════════════════════════════════════
    # 14. REFERENCES
    # ══════════════════════════════════════════════════════════════════
    s += [
        section("14. References"),
        p("[1] Meiklejohn, S. et al. (2013). <i>A Fistful of Bitcoins: Characterizing Payments Among Men with No Names.</i> IMC '13.", SMALL),
        spacer(0.5),
        p("[2] Ron, D. & Shamir, A. (2013). <i>Quantitative Analysis of the Full Bitcoin Transaction Graph.</i> Financial Cryptography.", SMALL),
        spacer(0.5),
        p("[3] Moeser, M. et al. (2013). <i>An Inquiry into Money Laundering Tools in the Bitcoin Ecosystem.</i> eCrime.", SMALL),
        spacer(0.5),
        p("[4] GraphSense TagPacks — https://github.com/graphsense/graphsense-tagpacks", SMALL),
        spacer(0.5),
        p("[5] US Treasury OFAC SDN List — https://home.treasury.gov/policy-issues/financial-sanctions/", SMALL),
        spacer(0.5),
        p("[6] 0xB10C/ofac-sanctioned-digital-currency-addresses — https://github.com/0xB10C/ofac-sanctioned-digital-currency-addresses", SMALL),
        spacer(0.5),
        p("[7] DOJ: Twitter Hack Charges — https://www.justice.gov/opa/pr/three-individuals-charged-alleged-roles-twitter-hack", SMALL),
        spacer(0.5),
        p("[8] DOJ: Colonial Pipeline Seizure — https://www.justice.gov/opa/pr/department-justice-seizes-23-million-cryptocurrency-paid-ransomware-extortionists-darkside", SMALL),
        spacer(0.5),
        p("[9] Elliptic: DarkSide Ransom Analysis — https://www.elliptic.co/blog/us-authorities-seize-darkside", SMALL),
        spacer(0.5),
        p("[10] DOJ: Bitfinex Seizure — https://www.justice.gov/opa/pr/two-arrested-alleged-conspiracy-launder-45-billion-stolen-cryptocurrency", SMALL),
        spacer(0.5),
        p("[11] Ransomwhere — https://ransomwhe.re/", SMALL),
        spacer(0.5),
        p("[12] mempool.space API — https://mempool.space/docs/api", SMALL),
    ]

    return s


def generate(out_path=None):
    if out_path is None:
        out_path = str(SCRIPT_DIR / "final_report.pdf")
    doc = SimpleDocTemplate(out_path, pagesize=A4,
                            leftMargin=LEFT_MARGIN, rightMargin=RIGHT_MARGIN,
                            topMargin=10*mm, bottomMargin=13*mm,
                            title="Proof of Funds — Final Report",
                            author="Crypto Asset Analytics — TU Wien 2026S")
    doc.build(build_story(), onFirstPage=_footer, onLaterPages=_footer)
    print(f"PDF written -> {out_path}")


if __name__ == "__main__":
    generate()
