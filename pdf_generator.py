from io import BytesIO
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)


def create_proposal_pdf(
    studio_name: str,
    client_name: str,
    proposal_text: str,
    price: float,
    timeline: str,
    proposal_id: str = "SB-0001",
) -> BytesIO:

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"{studio_name} - Business Proposal",
        author=studio_name,
    )

    styles = getSampleStyleSheet()

    brand_style = ParagraphStyle(
        "Brand",
        parent=styles["Normal"],
        fontSize=18,
        leading=22,
        fontName="Helvetica-Bold",
        spaceAfter=4,
    )

    title_style = ParagraphStyle(
        "Title",
        parent=styles["Title"],
        fontSize=27,
        leading=33,
        fontName="Helvetica-Bold",
        spaceAfter=10,
    )

    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=12,
        leading=18,
        spaceAfter=25,
    )

    heading_style = ParagraphStyle(
        "Heading",
        parent=styles["Heading2"],
        fontSize=14,
        leading=18,
        fontName="Helvetica-Bold",
        spaceBefore=14,
        spaceAfter=8,
    )

    body_style = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontSize=10.5,
        leading=16,
        spaceAfter=8,
    )

    bullet_style = ParagraphStyle(
        "Bullet",
        parent=body_style,
        leftIndent=10,
        firstLineIndent=-6,
        spaceAfter=5,
    )

    small_style = ParagraphStyle(
        "Small",
        parent=styles["Normal"],
        fontSize=8.5,
        leading=12,
    )

    table_style = ParagraphStyle(
        "TableText",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
    )

    price_style = ParagraphStyle(
        "Price",
        parent=styles["Normal"],
        fontSize=24,
        leading=30,
        fontName="Helvetica-Bold",
        alignment=1,
    )

    story = []

    def heading(text):
        story.append(
            Paragraph(
                text,
                heading_style,
            )
        )

    def body(text):
        story.append(
            Paragraph(
                text,
                body_style,
            )
        )

    def bullet(text):
        story.append(
            Paragraph(
                f"• {text}",
                bullet_style,
            )
        )

    # =====================================================
    # HEADER
    # =====================================================

    story.append(
        Paragraph(
            studio_name.upper(),
            brand_style,
        )
    )

    story.append(
        Paragraph(
            "BUSINESS PROPOSAL",
            small_style,
        )
    )

    story.append(
        Spacer(1, 20)
    )

    # =====================================================
    # COVER
    # =====================================================

    story.append(
        Paragraph(
            "Landing Page<br/>"
            "Design & Development",
            title_style,
        )
    )

    story.append(
        Paragraph(
            "A tailored proposal for your project",
            subtitle_style,
        )
    )

    cover_data = [
        [
            Paragraph("<b>Prepared for</b>", table_style),
            Paragraph(client_name, table_style),
        ],
        [
            Paragraph("<b>Proposal</b>", table_style),
            Paragraph(proposal_id, table_style),
        ],
        [
            Paragraph("<b>Date</b>", table_style),
            Paragraph(
                datetime.now().strftime("%B %d, %Y"),
                table_style,
            ),
        ],
        [
            Paragraph("<b>Timeline</b>", table_style),
            Paragraph(timeline, table_style),
        ],
    ]

    cover_table = Table(
        cover_data,
        colWidths=[
            45 * mm,
            120 * mm,
        ],
    )

    cover_table.setStyle(
        TableStyle(
            [
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.lightgrey,
                ),
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    colors.whitesmoke,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
            ]
        )
    )

    story.append(cover_table)

    story.append(
        Spacer(1, 25)
    )

    story.append(
        Paragraph(
            "Prepared by",
            small_style,
        )
    )

    story.append(
        Paragraph(
            f"<b>{studio_name}</b>",
            body_style,
        )
    )

    story.append(PageBreak())

    # =====================================================
    # EXECUTIVE SUMMARY
    # =====================================================

    heading("1. Executive Summary")

    body(
        f"{studio_name} proposes to design and develop a "
        f"professional landing page tailored to "
        f"{client_name}'s requirements. The objective is to "
        f"create a clear, responsive and conversion-focused "
        f"web experience that communicates the client's "
        f"offering effectively and gives visitors a clear "
        f"path to take action."
    )

    # =====================================================
    # PROJECT UNDERSTANDING
    # =====================================================

    heading("2. Project Understanding")

    body(
        "Based on the information provided during the "
        "initial consultation, the project will focus on "
        "creating a landing-page experience aligned with "
        "the client's business goals, audience and requested "
        "content structure."
    )

    # =====================================================
    # PARSE LLM PROPOSAL
    # =====================================================

    parsed_sections = {
        "scope": [],
        "included": [],
        "not_included": [],
        "timeline": [],
        "price": [],
    }

    current_section = None

    heading_map = {
        "scope": "scope",
        "included": "included",
        "what's included": "included",
        "not included": "not_included",
        "what's not included": "not_included",
        "timeline": "timeline",
        "price": "price",
    }

    for raw_line in proposal_text.splitlines():

        line = raw_line.strip()

        if not line:
            continue

        clean = line.replace("**", "").strip()

        normalized = clean.lower().rstrip(":")

        if normalized in heading_map:

            current_section = heading_map[normalized]

            continue

        if current_section:

            parsed_sections[current_section].append(
                clean
            )

    # =====================================================
    # PROPOSED SOLUTION
    # =====================================================

    heading("3. Proposed Solution")

    scope = parsed_sections["scope"]

    if scope:

        for item in scope:

            body(item)

    else:

        body(
            "A professionally structured landing page "
            "designed around the client's requirements, "
            "with a clear content hierarchy and responsive "
            "presentation across modern devices."
        )

    # =====================================================
    # SCOPE OF WORK
    # =====================================================

    heading("4. Scope of Work")

    included = parsed_sections["included"]

    if included:

        for item in included:

            item = item.lstrip("-• ").strip()

            if item:
                bullet(item)

    else:

        bullet("Landing page structure and layout")
        bullet("Responsive desktop and mobile presentation")
        bullet("Content and section structure")
        bullet("Two reasonable revision rounds")

    # =====================================================
    # DELIVERABLES
    # =====================================================

    heading("5. Deliverables")

    deliverables = [
        "Completed landing-page design and agreed structure",
        "Responsive presentation for desktop and mobile devices",
        "Final agreed content and section arrangement",
        "Two rounds of reasonable revisions",
    ]

    for item in deliverables:
        bullet(item)

    # =====================================================
    # TIMELINE
    # =====================================================

    heading("6. Timeline & Milestones")

    timeline_days = "7"

    timeline_parts = timeline.split()

    if timeline_parts:
        timeline_days = timeline_parts[0]

    timeline_data = [
        [
            Paragraph("<b>Phase</b>", table_style),
            Paragraph("<b>Activity</b>", table_style),
            Paragraph("<b>Timing</b>", table_style),
        ],
        [
            Paragraph("01", table_style),
            Paragraph(
                "Project brief & structure",
                table_style,
            ),
            Paragraph("Day 1", table_style),
        ],
        [
            Paragraph("02", table_style),
            Paragraph(
                "Initial design / draft",
                table_style,
            ),
            Paragraph("Days 2–4", table_style),
        ],
        [
            Paragraph("03", table_style),
            Paragraph(
                "Review & revisions",
                table_style,
            ),
            Paragraph("Days 5–6", table_style),
        ],
        [
            Paragraph("04", table_style),
            Paragraph(
                "Final delivery",
                table_style,
            ),
            Paragraph(
                f"Day {timeline_days}",
                table_style,
            ),
        ],
    ]

    timeline_table = Table(
        timeline_data,
        colWidths=[
            20 * mm,
            105 * mm,
            40 * mm,
        ],
    )

    timeline_table.setStyle(
        TableStyle(
            [
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.lightgrey,
                ),
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.whitesmoke,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
            ]
        )
    )

    story.append(timeline_table)

    # =====================================================
    # INVESTMENT
    # =====================================================

    heading("7. Investment")

    price_table = Table(
        [
            [
                Paragraph(
                    "PROJECT INVESTMENT",
                    table_style,
                )
            ],
            [
                Paragraph(
                    f"${price:.0f} USD",
                    price_style,
                )
            ],
            [
                Paragraph(
                    "Fixed project fee based on the agreed scope.",
                    table_style,
                )
            ],
        ],
        colWidths=[
            165 * mm,
        ],
    )

    price_table.setStyle(
        TableStyle(
            [
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.8,
                    colors.grey,
                ),
                (
                    "LINEBELOW",
                    (0, 0),
                    (-1, 0),
                    0.4,
                    colors.lightgrey,
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER",
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
            ]
        )
    )

    story.append(price_table)

    # =====================================================
    # EXCLUSIONS
    # =====================================================

    heading("8. Exclusions")

    exclusions = parsed_sections["not_included"]

    if exclusions:

        for item in exclusions:

            item = item.lstrip("-• ").strip()

            if item:
                bullet(item)

    else:

        bullet("Domain registration and hosting fees")
        bullet("Logo or full brand identity development")
        bullet("Paid advertising or third-party software fees")

    # =====================================================
    # CLIENT RESPONSIBILITIES
    # =====================================================

    heading("9. Client Responsibilities")

    responsibilities = [
        "Provide accurate business and project information",
        "Provide existing brand assets and content where applicable",
        "Review submitted work within a reasonable timeframe",
        "Provide consolidated feedback for revisions",
    ]

    for item in responsibilities:
        bullet(item)

    # =====================================================
    # PAYMENT TERMS
    # =====================================================

    heading("10. Payment Terms")

    body(
        f"The total project fee is ${price:.0f} USD. "
        "Payment instructions will be provided directly "
        "through the Telegram conversation. Project "
        "production begins after payment confirmation."
    )

    # =====================================================
    # NEXT STEPS
    # =====================================================

    heading("11. Next Steps")

    body(
        "To proceed with the project, complete the payment "
        "using the instructions provided in Telegram and "
        "reply PAID in the conversation. Once payment is "
        "confirmed, the project will move into the production queue."
    )

    story.append(
        Spacer(1, 20)
    )

    story.append(
        Paragraph(
            f"{studio_name} • Proposal {proposal_id}",
            small_style,
        )
    )

    document.build(story)

    buffer.seek(0)

    return buffer