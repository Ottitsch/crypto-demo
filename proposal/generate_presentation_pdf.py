"""
Generate a two-page actionable PDF implementation brief.

Style target: final_report.html
- compact A4 report, not slides
- TU Wien Informatics logo in the top-right header
- monochrome palette, grey cards, black table headers, thin rules
- one consistent content column to avoid random indentation

Run:
    python generate_presentation_pdf.py
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


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
SCRIPT_DIR = Path(__file__).resolve().parent
LOGO_PATH = SCRIPT_DIR / "assets" / "tu_wien_informatics_logo.png"

styles = getSampleStyleSheet()


def style(name: str, parent: str = "Normal", **kwargs) -> ParagraphStyle:
    return ParagraphStyle(name, parent=styles[parent], **kwargs)


TITLE = style(
    "Title",
    "Normal",
    fontName=FONT_BOLD,
    fontSize=18.5,
    leading=21,
    textColor=INK,
)
BODY = style(
    "Body",
    "Normal",
    fontName=FONT,
    fontSize=8.85,
    leading=11.4,
    textColor=INK,
    alignment=TA_LEFT,
)
SMALL = style(
    "Small",
    "Normal",
    fontName=FONT,
    fontSize=8.25,
    leading=10.4,
    textColor=INK,
)
MUTED_SMALL = style(
    "MutedSmall",
    "Normal",
    fontName=FONT,
    fontSize=7.45,
    leading=9.4,
    textColor=MUTED,
)
SECTION = style(
    "Section",
    "Normal",
    fontName=FONT_BOLD,
    fontSize=8.9,
    leading=10.8,
    textColor=INK,
    spaceBefore=3.4 * mm,
    spaceAfter=1.6 * mm,
)
CARD_TITLE = style(
    "CardTitle",
    "Normal",
    fontName=FONT_BOLD,
    fontSize=9.1,
    leading=11,
    textColor=INK,
    spaceAfter=0.8 * mm,
)
TABLE_HEAD = style(
    "TableHead",
    "Normal",
    fontName=FONT_BOLD,
    fontSize=7.75,
    leading=9.3,
    textColor=WHITE,
)
TABLE_CELL = style(
    "TableCell",
    "Normal",
    fontName=FONT,
    fontSize=7.75,
    leading=9.45,
    textColor=INK,
)
TABLE_CELL_BOLD = style(
    "TableCellBold",
    "Normal",
    fontName=FONT_BOLD,
    fontSize=7.75,
    leading=9.45,
    textColor=INK,
)
CODE = style(
    "Code",
    "Normal",
    fontName="Courier",
    fontSize=7.6,
    leading=9.4,
    textColor=INK,
)


def p(text: str, paragraph_style: ParagraphStyle = BODY) -> Paragraph:
    return Paragraph(text, paragraph_style)


def spacer(height_mm: float) -> Spacer:
    return Spacer(1, height_mm * mm)


def section(title: str) -> Paragraph:
    return p(title.upper(), SECTION)


def rule(space_after_mm: float = 3.0) -> HRFlowable:
    return HRFlowable(
        width="100%",
        thickness=0.45 * mm,
        color=INK,
        spaceBefore=0,
        spaceAfter=space_after_mm * mm,
    )


def header(title: str, subtitle: str | None = None) -> list:
    left_flowables = [p(title, TITLE)]
    if subtitle:
        left_flowables.append(p(subtitle, MUTED_SMALL))

    if LOGO_PATH.exists():
        logo = Image(str(LOGO_PATH), width=56 * mm, height=8.4 * mm)
        table = Table([[left_flowables, logo]], colWidths=[CONTENT_W - 62 * mm, 56 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        return [table, rule()]

    return left_flowables + [rule()]


def panel(title: str, body: str) -> Table:
    table = Table(
        [
            [""],
            [[p(title, CARD_TITLE), p(body, BODY)]],
        ],
        colWidths=[CONTENT_W],
        rowHeights=[1.0 * mm, None],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), ACCENT),
                ("BACKGROUND", (0, 1), (0, 1), PANEL),
                ("BOX", (0, 1), (0, 1), 0.25 * mm, LINE),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
                ("RIGHTPADDING", (0, 0), (0, 0), 0),
                ("TOPPADDING", (0, 0), (0, 0), 0),
                ("BOTTOMPADDING", (0, 0), (0, 0), 0),
                ("LEFTPADDING", (0, 1), (0, 1), 3.0 * mm),
                ("RIGHTPADDING", (0, 1), (0, 1), 3.0 * mm),
                ("TOPPADDING", (0, 1), (0, 1), 2.2 * mm),
                ("BOTTOMPADDING", (0, 1), (0, 1), 2.2 * mm),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def simple_card(title: str, body: str) -> Table:
    table = Table([[[p(title, CARD_TITLE), p(body, SMALL)]]], colWidths=[CONTENT_W])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PANEL),
                ("BOX", (0, 0), (-1, -1), 0.25 * mm, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 2.2 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2.2 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 1.6 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6 * mm),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def make_table(rows: list[list[str]], widths: list[float], first_col_bold: bool = True) -> Table:
    data = []
    for row_idx, row in enumerate(rows):
        rendered_row = []
        for col_idx, cell in enumerate(row):
            if row_idx == 0:
                rendered_row.append(p(cell, TABLE_HEAD))
            elif first_col_bold and col_idx == 0:
                rendered_row.append(p(cell, TABLE_CELL_BOLD))
            else:
                rendered_row.append(p(cell, TABLE_CELL))
        data.append(rendered_row)

    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), INK),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PANEL_ALT]),
                ("GRID", (0, 0), (-1, -1), 0.25 * mm, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 1.35 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 1.35 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 1.0 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.0 * mm),
            ]
        )
    )
    return table


def footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.25 * mm)
    canvas.line(LEFT_MARGIN, 10 * mm, PAGE_W - RIGHT_MARGIN, 10 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont(FONT, 7)
    canvas.drawString(LEFT_MARGIN, 6.2 * mm, "Crypto Asset Analytics - Project 1")
    canvas.drawRightString(PAGE_W - RIGHT_MARGIN, 6.2 * mm, "1 / 1")
    canvas.restoreState()


def build_story() -> list:
    story = []

    story += header(
        "Proof of Funds: Implementation Brief",
        "Planned KYT / AML graph scoring prototype for incoming Bitcoin transactions.",
    )
    story += [
        section("Project brief"),
        make_table(
            [
                ["Item", "Description"],
                [
                    "Context",
                    "Cryptoasset service providers must quantify risk for incoming transactions as part of AML / KYT procedures.",
                ],
                [
                    "Questions",
                    "How can we quantify risk, for example by distance from darknet markets? How can scores be precomputed for large graphs?",
                ],
                [
                    "Tasks",
                    "Define risk metrics, compute exposure per entity, and analyze the resulting risk distribution.",
                ],
            ],
            [34 * mm, CONTENT_W - 34 * mm],
        ),
        spacer(1.0),
        panel(
            "Objective",
            "We will build a Bitcoin Proof of Funds prototype for KYT / AML screening. "
            "The system will start from known high-risk addresses, crawl their transaction "
            "neighbourhood, and assign each address an explainable risk score.",
        ),
        section("Data we found"),
        make_table(
            [
                ["Data", "Use in the prototype"],
                [
                    "GraphSense TagPacks",
                    "Open address labels for ransomware, darknet markets, scams, hacks, exchanges, miners, and services.",
                ],
                [
                    "Seed addresses",
                    "6 tagged Bitcoin addresses: Locky ransomware, investment / gift-BTC scams, and the 2016 Bitfinex hack.",
                ],
                [
                    "mempool.space API",
                    "Public transaction data for crawling the local neighbourhood around the seeds.",
                ],
            ],
            [43 * mm, CONTENT_W - 43 * mm],
        ),
        section("Core approach"),
        make_table(
            [
                ["Step", "What we will do", "Output"],
                [
                    "1. Label risk sources",
                    "Use GraphSense TagPacks to identify addresses linked to ransomware, darknet markets, hacks, scams, and services.",
                    "Tagged seed addresses",
                ],
                [
                    "2. Build local graph",
                    "Fetch transactions around the seeds and convert value flow into a weighted directed graph.",
                    "Address graph",
                ],
                [
                    "3. Score exposure",
                    "Combine graph distance, direct tainted value, and multi-hop taint propagation.",
                    "0-100 risk score",
                ],
                [
                    "4. Analyze results",
                    "Export the score table and inspect the distribution in a notebook.",
                    "Case study + plots",
                ],
            ],
            [36 * mm, 96 * mm, CONTENT_W - 132 * mm],
        ),
        section("Risk metrics"),
        make_table(
            [
                ["Metric", "Meaning"],
                [
                    "Distance",
                    "How many hops separate an address from known high-risk funds.",
                ],
                [
                    "Direct exposure",
                    "How much incoming value comes directly from risky predecessors.",
                ],
                [
                    "Haircut taint",
                    "How taint propagates through the graph over multiple hops.",
                ],
                [
                    "Aggregate score",
                    "A weighted 0-100 score used to prioritize manual review.",
                ],
            ],
            [42 * mm, CONTENT_W - 42 * mm],
        ),
        spacer(1.5),
        simple_card(
            "Design principle",
            "The score should be explainable. A compliance analyst should be able to see whether risk comes from proximity, direct value exposure, or indirect taint.",
        ),
        section("What we will deliver"),
        make_table(
            [
                ["Deliverable", "Purpose"],
                ["Python package", "Reusable implementation for loading labels, building graphs, and computing risk metrics."],
                ["Notebook", "Readable explanation of the pipeline and score distribution."],
                ["Risk table", "One row per address with metric columns and final score."],
            ],
            [44 * mm, CONTENT_W - 44 * mm],
        ),
        section("Scope boundaries"),
        make_table(
            [
                ["Boundary", "Reason"],
                ["Bitcoin only", "Keeps the first prototype focused on one transaction model and one data source."],
                ["Bounded crawl", "Makes the demo reproducible, but may miss distant taint paths."],
                ["No full clustering", "Change-address and entity clustering heuristics are future work."],
                ["Prototype weights", "Severity weights are illustrative and not production policy."],
            ],
            [43 * mm, CONTENT_W - 43 * mm],
        ),
    ]
    return story


def generate(out_path: str | None = None) -> None:
    if out_path is None:
        out_path = str(SCRIPT_DIR / "presentation_template.pdf")

    doc = SimpleDocTemplate(
        out_path,
        pagesize=A4,
        leftMargin=LEFT_MARGIN,
        rightMargin=RIGHT_MARGIN,
        topMargin=10 * mm,
        bottomMargin=13 * mm,
        title="Proof of Funds - Implementation Brief",
        author="Crypto Asset Analytics",
    )
    doc.build(build_story(), onFirstPage=footer, onLaterPages=footer)
    print(f"PDF written -> {out_path}")


if __name__ == "__main__":
    generate()
