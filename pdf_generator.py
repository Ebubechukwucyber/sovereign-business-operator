from io import BytesIO
from datetime import datetime
from html import escape
import re

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
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


# =========================================================
# PREMIUM CORPORATE COLOUR PALETTE
# =========================================================

NAVY = HexColor("#12233F")
NAVY_2 = HexColor("#1D3557")

ACCENT = HexColor("#168AAD")
ACCENT_LIGHT = HexColor("#E8F5F8")

SLATE = HexColor("#53657D")
TEXT = HexColor("#263238")
MUTED = HexColor("#718096")

LIGHT_BG = HexColor("#F4F7FA")
BORDER = HexColor("#D9E2EC")

WHITE = colors.white

SUCCESS = HexColor("#2A9D8F")
SUCCESS_LIGHT = HexColor("#EAF7F4")


# =========================================================
# MAIN PDF GENERATOR
# =========================================================

def create_proposal_pdf(
    studio_name: str,
    client_name: str,
    proposal_text: str,
    price: float,
    timeline: str,
    proposal_id: str = "SB-0001",
    change_request: str = "",
    project_title: str = "",
    signature: str = "",
    owner_signature: str = "",
    currency: str = "USD",
) -> BytesIO:

    buffer = BytesIO()

    # =====================================================
    # SAFE VALUES
    # =====================================================

    studio_name = str(
        studio_name or "Business"
    ).strip()

    client_name = str(
        client_name or "Client"
    ).strip()

    proposal_text = str(
        proposal_text or ""
    ).strip()

    timeline = str(
        timeline or "To be confirmed"
    ).strip()

    proposal_id = str(
        proposal_id or "SB-0001"
    ).strip()

    change_request = str(
        change_request or ""
    ).strip()

    signature = str(
        owner_signature or signature or ""
    ).strip()

    currency = str(
        currency or "USD"
    ).strip().upper()

    try:

        numeric_price = float(price)

    except (
        TypeError,
        ValueError,
    ):

        numeric_price = 0.0

    # =====================================================
    # PROJECT TITLE
    # =====================================================

    if not project_title:

        project_title = _extract_project_title(
            proposal_text
        )

    if not project_title:

        project_title = "Project Proposal"

    # =====================================================
    # DOCUMENT
    # =====================================================

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=19 * mm,
        bottomMargin=20 * mm,
        title=(
            f"{studio_name} - "
            f"Business Proposal"
        ),
        author=studio_name,
        subject=(
            f"Proposal {proposal_id}"
        ),
    )

    styles = getSampleStyleSheet()

    # =====================================================
    # STYLES
    # =====================================================

    brand_style = ParagraphStyle(
        "Brand",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=17,
        leading=20,
        textColor=NAVY,
        spaceAfter=3,
    )

    brand_subtitle = ParagraphStyle(
        "BrandSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=ACCENT,
        spaceAfter=0,
    )

    cover_title = ParagraphStyle(
        "CoverTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=29,
        leading=34,
        textColor=NAVY,
        alignment=TA_LEFT,
        spaceAfter=8,
    )

    cover_subtitle = ParagraphStyle(
        "CoverSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=17,
        textColor=SLATE,
        spaceAfter=18,
    )

    eyebrow_style = ParagraphStyle(
        "Eyebrow",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=10,
        textColor=ACCENT,
        spaceAfter=5,
    )

    heading_style = ParagraphStyle(
        "Heading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=NAVY,
        spaceBefore=12,
        spaceAfter=8,
    )

    body_style = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.7,
        leading=15,
        textColor=TEXT,
        spaceAfter=7,
    )

    bullet_style = ParagraphStyle(
        "Bullet",
        parent=body_style,
        leftIndent=12,
        firstLineIndent=-7,
        spaceAfter=5,
    )

    small_style = ParagraphStyle(
        "Small",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.7,
        leading=10.5,
        textColor=MUTED,
    )

    table_label_style = ParagraphStyle(
        "TableLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.2,
        leading=9,
        textColor=MUTED,
    )

    table_value_style = ParagraphStyle(
        "TableValue",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=NAVY,
    )

    table_body_style = ParagraphStyle(
        "TableBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.4,
        leading=12,
        textColor=TEXT,
    )

    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=WHITE,
    )

    price_label_style = ParagraphStyle(
        "PriceLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=10,
        textColor=ACCENT,
        alignment=TA_CENTER,
    )

    price_style = ParagraphStyle(
        "Price",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=27,
        leading=32,
        textColor=NAVY,
        alignment=TA_CENTER,
    )

    price_note_style = ParagraphStyle(
        "PriceNote",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=SLATE,
        alignment=TA_CENTER,
    )

    revision_title_style = ParagraphStyle(
        "RevisionTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=10,
        textColor=ACCENT,
    )

    signature_style = ParagraphStyle(
        "Signature",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=12,
        leading=16,
        textColor=NAVY,
    )

    story = []

    # =====================================================
    # HELPERS
    # =====================================================

    def safe(value):

        if value is None:
            return ""

        return escape(
            str(value)
        ).replace(
            "\n",
            "<br/>",
        )

    def add_heading(text):

        story.append(
            Paragraph(
                safe(text),
                heading_style,
            )
        )

    def add_body(text):

        if text:

            story.append(
                Paragraph(
                    safe(text),
                    body_style,
                )
            )

    def add_bullet(text):

        if not text:
            return

        clean = str(
            text
        ).strip()

        clean = re.sub(
            r"^[-•*]\s*",
            "",
            clean,
        )

        if clean:

            story.append(
                Paragraph(
                    (
                        '<font color="#168AAD">'
                        "•"
                        "</font> "
                        f"{safe(clean)}"
                    ),
                    bullet_style,
                )
            )

    # =====================================================
    # PARSE PROPOSAL
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
        "scope of work": "scope",
        "project scope": "scope",

        "included": "included",
        "what's included": "included",
        "whats included": "included",
        "included services": "included",
        "included services & deliverables": "included",
        "deliverables": "included",

        "not included": "not_included",
        "what's not included": "not_included",
        "whats not included": "not_included",
        "exclusions": "not_included",

        "timeline": "timeline",
        "timeline & milestones": "timeline",
        "timeline and milestones": "timeline",

        "price": "price",
        "pricing": "price",
        "investment": "price",
    }

    for raw_line in proposal_text.splitlines():

        line = raw_line.strip()

        if not line:
            continue

        clean = (
            line
            .replace("**", "")
            .replace("__", "")
            .strip()
        )

        normalized = (
            clean
            .lower()
            .rstrip(":")
            .strip()
        )

        if clean.startswith("#"):

            candidate = (
                clean
                .lstrip("#")
                .strip()
                .lower()
                .rstrip(":")
            )

            if candidate in heading_map:

                current_section = (
                    heading_map[
                        candidate
                    ]
                )

                continue

        if normalized in heading_map:

            current_section = (
                heading_map[
                    normalized
                ]
            )

            continue

        if current_section:

            parsed_sections[
                current_section
            ].append(clean)

    # =====================================================
    # HEADER / FOOTER
    # =====================================================

    def draw_header_footer(
        canvas,
        doc,
    ):

        canvas.saveState()

        width, height = A4

        # Top accent line
        canvas.setStrokeColor(
            ACCENT
        )

        canvas.setLineWidth(
            2.2
        )

        canvas.line(
            doc.leftMargin,
            height - 10 * mm,
            width - doc.rightMargin,
            height - 10 * mm,
        )

        # Footer separator
        canvas.setStrokeColor(
            BORDER
        )

        canvas.setLineWidth(
            0.5
        )

        canvas.line(
            doc.leftMargin,
            12 * mm,
            width - doc.rightMargin,
            12 * mm,
        )

        canvas.setFont(
            "Helvetica",
            7,
        )

        canvas.setFillColor(
            MUTED
        )

        canvas.drawString(
            doc.leftMargin,
            7.5 * mm,
            (
                f"{studio_name} • "
                f"Proposal {proposal_id}"
            ),
        )

        canvas.drawRightString(
            width - doc.rightMargin,
            7.5 * mm,
            f"Page {doc.page}",
        )

        canvas.restoreState()

    # =====================================================
    # COVER HEADER
    # =====================================================

    header_table = Table(
        [
            [
                Paragraph(
                    safe(
                        studio_name
                    ).upper(),
                    brand_style,
                ),

                Paragraph(
                    "PROFESSIONAL BUSINESS PROPOSAL",
                    brand_subtitle,
                ),
            ]
        ],
        colWidths=[
            100 * mm,
            65 * mm,
        ],
    )

    header_table.setStyle(
        TableStyle(
            [

                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),

                (
                    "ALIGN",
                    (1, 0),
                    (1, 0),
                    "RIGHT",
                ),

                (
                    "LINEBELOW",
                    (0, 0),
                    (-1, 0),
                    1,
                    BORDER,
                ),

                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    12,
                ),

            ]
        )
    )

    story.append(
        header_table
    )

    story.append(
        Spacer(1, 25)
    )

    # =====================================================
    # COVER TITLE
    # =====================================================

    story.append(
        Paragraph(
            "PROJECT PROPOSAL",
            eyebrow_style,
        )
    )

    story.append(
        Paragraph(
            safe(project_title),
            cover_title,
        )
    )

    story.append(
        Paragraph(
            (
                "A clear proposal outlining the agreed "
                "scope, timeline and project investment."
            ),
            cover_subtitle,
        )
    )

    # =====================================================
    # METADATA
    # =====================================================

    metadata = [

        [
            Paragraph(
                "PREPARED FOR",
                table_label_style,
            ),

            Paragraph(
                "PROPOSAL ID",
                table_label_style,
            ),

            Paragraph(
                "DATE",
                table_label_style,
            ),
        ],

        [
            Paragraph(
                safe(client_name),
                table_value_style,
            ),

            Paragraph(
                safe(proposal_id),
                table_value_style,
            ),

            Paragraph(
                datetime.now().strftime(
                    "%B %d, %Y"
                ),
                table_value_style,
            ),
        ],

        [
            Paragraph(
                "DELIVERY TIMELINE",
                table_label_style,
            ),

            Paragraph(
                "PROJECT INVESTMENT",
                table_label_style,
            ),

            Paragraph(
                "STATUS",
                table_label_style,
            ),
        ],

        [
            Paragraph(
                safe(timeline),
                table_value_style,
            ),

            Paragraph(
                (
                    f"{currency} "
                    f"{numeric_price:,.2f}"
                ),
                table_value_style,
            ),

            Paragraph(
                "PROPOSAL",
                table_value_style,
            ),
        ],
    ]

    metadata_table = Table(
        metadata,
        colWidths=[
            55 * mm,
            55 * mm,
            55 * mm,
        ],
        rowHeights=[
            8 * mm,
            11 * mm,
            8 * mm,
            11 * mm,
        ],
    )

    metadata_table.setStyle(
        TableStyle(
            [

                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    LIGHT_BG,
                ),

                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.7,
                    BORDER,
                ),

                (
                    "INNERGRID",
                    (0, 0),
                    (-1, -1),
                    0.45,
                    BORDER,
                ),

                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),

                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    9,
                ),

                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    9,
                ),

                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),

                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),

            ]
        )
    )

    story.append(
        metadata_table
    )

    # =====================================================
    # REVISION NOTICE
    # =====================================================

    if change_request:

        story.append(
            Spacer(1, 17)
        )

        revision_table = Table(
            [

                [
                    Paragraph(
                        "CLIENT REQUESTED CHANGES",
                        revision_title_style,
                    )
                ],

                [
                    Paragraph(
                        safe(change_request),
                        body_style,
                    )
                ],

            ],
            colWidths=[
                165 * mm
            ],
        )

        revision_table.setStyle(
            TableStyle(
                [

                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, -1),
                        ACCENT_LIGHT,
                    ),

                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.8,
                        ACCENT,
                    ),

                    (
                        "LINEBEFORE",
                        (0, 0),
                        (0, -1),
                        4,
                        ACCENT,
                    ),

                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        10,
                    ),

                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        10,
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

        story.append(
            revision_table
        )

    # =====================================================
    # PREPARED BY
    # =====================================================

    story.append(
        Spacer(1, 24)
    )

    prepared_card = Table(
        [

            [
                Paragraph(
                    "PREPARED BY",
                    table_label_style,
                )
            ],

            [
                Paragraph(
                    (
                        f"<b>"
                        f"{safe(studio_name)}"
                        f"</b>"
                    ),
                    table_value_style,
                )
            ],

        ],
        colWidths=[
            70 * mm
        ],
    )

    prepared_card.setStyle(
        TableStyle(
            [

                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    LIGHT_BG,
                ),

                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.7,
                    BORDER,
                ),

                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),

                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
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

    story.append(
        prepared_card
    )

    story.append(
        PageBreak()
    )

    # =====================================================
    # 1. EXECUTIVE SUMMARY
    # =====================================================

    add_heading(
        "1. Executive Summary"
    )

    summary = _first_content(
        parsed_sections[
            "scope"
        ]
    )

    if not summary:

        summary = (
            "This proposal outlines the agreed project "
            "scope, deliverables, timeline and investment "
            "for the client."
        )

    add_body(
        summary
    )

    # =====================================================
    # 2. PROJECT SCOPE
    # =====================================================

    add_heading(
        "2. Project Scope"
    )

    scope = parsed_sections[
        "scope"
    ]

    if scope:

        for item in scope:

            add_body(
                item
            )

    else:

        add_body(
            "The project will be delivered according "
            "to the requirements discussed and "
            "approved by the client."
        )

    # =====================================================
    # 3. INCLUDED SERVICES
    # =====================================================

    add_heading(
        "3. Included Services & Deliverables"
    )

    included = parsed_sections[
        "included"
    ]

    if included:

        for item in included:

            add_bullet(
                item
            )

    else:

        add_bullet(
            "Custom work tailored to the client's requirements."
        )

        add_bullet(
            "Professional execution of the agreed project scope."
        )

        add_bullet(
            "Reasonable revisions based on the approved scope."
        )

    # =====================================================
    # 4. TIMELINE
    # =====================================================

    add_heading(
        "4. Timeline"
    )

    add_body(
        (
            f"Delivery within "
            f"{safe(timeline)} "
            "from project kickoff."
        )
    )

    timeline_data = [

        [
            Paragraph(
                "ITEM",
                table_header_style,
            ),

            Paragraph(
                "DETAIL",
                table_header_style,
            ),
        ],

        [
            Paragraph(
                "Project kickoff",
                table_body_style,
            ),

            Paragraph(
                (
                    "Following confirmation and "
                    "required payment verification."
                ),
                table_body_style,
            ),
        ],

        [
            Paragraph(
                "Delivery",
                table_body_style,
            ),

            Paragraph(
                safe(timeline),
                table_body_style,
            ),
        ],
    ]

    timeline_table = Table(
        timeline_data,
        colWidths=[
            48 * mm,
            117 * mm,
        ],
    )

    timeline_table.setStyle(
        TableStyle(
            [

                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    NAVY,
                ),

                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        WHITE,
                        LIGHT_BG,
                    ],
                ),

                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.6,
                    BORDER,
                ),

                (
                    "INNERGRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    BORDER,
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

    story.append(
        timeline_table
    )

    # =====================================================
    # 5. INVESTMENT
    # =====================================================

    add_heading(
        "5. Investment"
    )

    price_table = Table(
        [

            [
                Paragraph(
                    "TOTAL PROJECT INVESTMENT",
                    price_label_style,
                )
            ],

            [
                Paragraph(
                    (
                        f"{currency} "
                        f"{numeric_price:,.2f}"
                    ),
                    price_style,
                )
            ],

            [
                Paragraph(
                    (
                        "Fixed project fee based "
                        "on the approved scope."
                    ),
                    price_note_style,
                )
            ],

        ],
        colWidths=[
            165 * mm
        ],
    )

    price_table.setStyle(
        TableStyle(
            [

                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    ACCENT_LIGHT,
                ),

                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    1,
                    ACCENT,
                ),

                (
                    "LINEABOVE",
                    (0, 0),
                    (-1, 0),
                    5,
                    ACCENT,
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
                    9,
                ),

                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    9,
                ),

            ]
        )
    )

    story.append(
        price_table
    )

    # =====================================================
    # 6. EXCLUSIONS
    # =====================================================

    add_heading(
        "6. Exclusions"
    )

    exclusions = parsed_sections[
        "not_included"
    ]

    if exclusions:

        for item in exclusions:

            add_bullet(
                item
            )

    else:

        add_bullet(
            "Work outside the agreed project scope."
        )

        add_bullet(
            "Ongoing maintenance unless specifically agreed."
        )

        add_bullet(
            "Third-party costs unless specifically agreed."
        )

    # =====================================================
    # 7. CLIENT RESPONSIBILITIES
    # =====================================================

    add_heading(
        "7. Client Responsibilities"
    )

    responsibilities = [

        "Provide accurate project information and required materials.",

        "Provide timely feedback and approvals.",

        "Communicate material changes to the agreed scope.",
    ]

    for item in responsibilities:

        add_bullet(
            item
        )

    # =====================================================
    # 8. PAYMENT TERMS
    # =====================================================

    add_heading(
        "8. Payment Terms"
    )

    add_body(
        (
            f"The total project fee is "
            f"{currency} "
            f"{numeric_price:,.2f}. "
            "Payment instructions will be provided "
            "through the business's approved payment "
            "process. Work begins after payment has "
            "been verified by the business."
        )
    )

    # =====================================================
    # 9. NEXT STEPS
    # =====================================================

    add_heading(
        "9. Next Steps"
    )

    add_body(
        (
            "Review this proposal and confirm that "
            "the scope, timeline and investment "
            "accurately reflect your requirements. "
            "Once the proposal is accepted and payment "
            "is verified, the project can proceed "
            "according to the stated timeline."
        )
    )

    # =====================================================
    # ACCEPTANCE
    # =====================================================

    acceptance_table = Table(
        [

            [
                Paragraph(
                    "PROPOSAL ACCEPTANCE",
                    revision_title_style,
                )
            ],

            [
                Paragraph(
                    (
                        "By proceeding with payment, the "
                        "client confirms acceptance of the "
                        "approved scope, timeline and "
                        "project investment outlined in "
                        "this proposal."
                    ),
                    body_style,
                )
            ],

        ],
        colWidths=[
            165 * mm
        ],
    )

    acceptance_table.setStyle(
        TableStyle(
            [

                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    SUCCESS_LIGHT,
                ),

                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.8,
                    SUCCESS,
                ),

                (
                    "LINEBEFORE",
                    (0, 0),
                    (0, -1),
                    4,
                    SUCCESS,
                ),

                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),

                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
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

    story.append(
        Spacer(1, 10)
    )

    story.append(
        acceptance_table
    )

    # =====================================================
    # SIGNATURES
    # =====================================================

    story.append(
        Spacer(1, 22)
    )

    owner_signature_display = (
        signature
        if signature
        else studio_name
    )

    signature_data = [

        [
            Paragraph(
                "PREPARED BY",
                table_label_style,
            ),

            Paragraph(
                "CLIENT",
                table_label_style,
            ),
        ],

        [
            Paragraph(
                safe(
                    owner_signature_display
                ),
                signature_style,
            ),

            Paragraph(
                "",
                signature_style,
            ),
        ],

        [
            Paragraph(
                "____________________________",
                small_style,
            ),

            Paragraph(
                "____________________________",
                small_style,
            ),
        ],

        [
            Paragraph(
                safe(
                    studio_name
                ),
                table_body_style,
            ),

            Paragraph(
                safe(
                    client_name
                ),
                table_body_style,
            ),
        ],

        [
            Paragraph(
                "Authorized representative",
                small_style,
            ),

            Paragraph(
                "Client approval",
                small_style,
            ),
        ],
    ]

    signature_table = Table(
        signature_data,
        colWidths=[
            82 * mm,
            82 * mm,
        ],
    )

    signature_table.setStyle(
        TableStyle(
            [

                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    LIGHT_BG,
                ),

                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.6,
                    BORDER,
                ),

                (
                    "INNERGRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    BORDER,
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
                    9,
                ),

                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    9,
                ),

                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),

                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),

            ]
        )
    )

    story.append(
        signature_table
    )

    # =====================================================
    # BUILD PDF
    # =====================================================

    document.build(
        story,
        onFirstPage=draw_header_footer,
        onLaterPages=draw_header_footer,
    )

    buffer.seek(0)

    return buffer


# =========================================================
# HELPER: FIRST CONTENT
# =========================================================

def _first_content(items):

    if not items:
        return ""

    for item in items:

        clean = str(
            item
        ).strip()

        if clean:
            return clean

    return ""


# =========================================================
# HELPER: PROJECT TITLE
# =========================================================

def _extract_project_title(
    proposal_text,
):

    if not proposal_text:
        return ""

    lines = [
        line.strip()
        for line in proposal_text.splitlines()
        if line.strip()
    ]

    ignored_prefixes = (
        "scope",
        "included",
        "not included",
        "timeline",
        "price",
        "pricing",
        "investment",
        "deliverables",
        "exclusions",
    )

    for line in lines[:10]:

        clean = (
            line
            .replace("**", "")
            .replace("__", "")
            .strip()
        )

        lower = clean.lower()

        if lower.startswith(
            ignored_prefixes
        ):
            continue

        if clean.startswith("#"):

            clean = (
                clean
                .lstrip("#")
                .strip()
            )

        if (
            3
            <= len(clean)
            <= 90
        ):

            return clean

    return ""

# =========================================================
# PROFESSIONAL INVOICE PDF
# =========================================================

def create_invoice_pdf(
    studio_name: str,
    client_name: str,
    job_id,
    amount,
    currency: str = "USDC",
    network: str = "Base",
    token: str = "USDC",
    tx_hash: str = "",
    block_number: str = "",
    confirmations: str = "",
    recipient: str = "",
    sender: str = "",
    project_title: str = "",
    signature_name: str = "",
    signature_title: str = "",
) -> BytesIO:
    """
    Premium corporate invoice matching the proposal design.
    """

    buffer = BytesIO()

    studio_name = str(studio_name or "Sovereign Studio").strip()
    client_name = str(client_name or "Client").strip()
    currency = str(currency or "USDC").strip().upper()
    network = str(network or "Base").strip()
    token = str(token or "USDC").strip()
    tx_hash = str(tx_hash or "").strip()
    recipient = str(recipient or "").strip()
    sender = str(sender or "").strip()
    project_title = str(project_title or "Professional Services").strip()
    signature_name = str(signature_name or studio_name).strip()
    signature_title = str(signature_title or "Authorized representative").strip()

    try:
        job_num = int(job_id)
    except (TypeError, ValueError):
        job_num = 0

    invoice_id = f"INV-SB-{job_num:04d}"
    project_id = f"SB-{job_num:04d}"

    try:
        numeric_amount = float(amount)
        amount_display = f"{numeric_amount:,.2f}"
    except (TypeError, ValueError):
        amount_display = str(amount or "0")

    issued_at = datetime.utcnow().strftime("%d %B %Y")

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=19 * mm,
        bottomMargin=20 * mm,
        title=f"{studio_name} - Invoice {invoice_id}",
        author=studio_name,
        subject=f"Invoice {invoice_id}",
    )

    styles = getSampleStyleSheet()

    brand_style = ParagraphStyle(
        "InvBrand",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=17,
        leading=20,
        textColor=NAVY,
        spaceAfter=3,
    )

    brand_subtitle = ParagraphStyle(
        "InvBrandSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=ACCENT,
        spaceAfter=0,
        alignment=TA_RIGHT,
    )

    eyebrow_style = ParagraphStyle(
        "InvEyebrow",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=10,
        textColor=ACCENT,
        spaceAfter=5,
    )

    cover_title = ParagraphStyle(
        "InvCoverTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=28,
        leading=33,
        textColor=NAVY,
        alignment=TA_LEFT,
        spaceAfter=6,
    )

    cover_subtitle = ParagraphStyle(
        "InvCoverSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=15,
        textColor=SLATE,
        spaceAfter=16,
    )

    table_label_style = ParagraphStyle(
        "InvTableLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.2,
        leading=9,
        textColor=MUTED,
    )

    table_value_style = ParagraphStyle(
        "InvTableValue",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=NAVY,
    )

    table_body_style = ParagraphStyle(
        "InvTableBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.4,
        leading=12,
        textColor=TEXT,
    )

    table_header_style = ParagraphStyle(
        "InvTableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=WHITE,
    )

    amount_label_style = ParagraphStyle(
        "InvAmountLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=10,
        textColor=ACCENT,
        alignment=TA_CENTER,
    )

    amount_style = ParagraphStyle(
        "InvAmount",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=26,
        leading=31,
        textColor=NAVY,
        alignment=TA_CENTER,
    )

    amount_note_style = ParagraphStyle(
        "InvAmountNote",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=SLATE,
        alignment=TA_CENTER,
    )

    heading_style = ParagraphStyle(
        "InvHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=NAVY,
        spaceBefore=10,
        spaceAfter=8,
    )

    body_style = ParagraphStyle(
        "InvBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=TEXT,
        spaceAfter=6,
    )

    small_style = ParagraphStyle(
        "InvSmall",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.7,
        leading=10.5,
        textColor=MUTED,
    )

    signature_style = ParagraphStyle(
        "InvSignature",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=12,
        leading=16,
        textColor=NAVY,
    )

    paid_badge_style = ParagraphStyle(
        "InvPaidBadge",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=SUCCESS,
        alignment=TA_CENTER,
    )

    def safe(value):
        if value is None:
            return ""
        return escape(str(value)).replace("\n", "<br/>")

    def draw_header_footer(canvas, doc):
        canvas.saveState()
        width, height = A4

        canvas.setStrokeColor(ACCENT)
        canvas.setLineWidth(2.2)
        canvas.line(
            doc.leftMargin,
            height - 10 * mm,
            width - doc.rightMargin,
            height - 10 * mm,
        )

        canvas.setStrokeColor(BORDER)
        canvas.setLineWidth(0.5)
        canvas.line(
            doc.leftMargin,
            12 * mm,
            width - doc.rightMargin,
            12 * mm,
        )

        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(
            doc.leftMargin,
            7.5 * mm,
            f"{studio_name} • Invoice {invoice_id}",
        )
        canvas.drawRightString(
            width - doc.rightMargin,
            7.5 * mm,
            f"Page {doc.page}",
        )
        canvas.restoreState()

    story = []

    # Header
    header_table = Table(
        [
            [
                Paragraph(safe(studio_name).upper(), brand_style),
                Paragraph("PROFESSIONAL INVOICE", brand_subtitle),
            ]
        ],
        colWidths=[100 * mm, 65 * mm],
    )
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("LINEBELOW", (0, 0), (-1, 0), 1, BORDER),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    story.append(header_table)
    story.append(Spacer(1, 22))

    # Title
    story.append(Paragraph("TAX / PAYMENT INVOICE", eyebrow_style))
    story.append(Paragraph(safe(project_title), cover_title))
    story.append(
        Paragraph(
            "This invoice confirms payment received for the "
            "professional services detailed below.",
            cover_subtitle,
        )
    )

    # Metadata
    metadata = [
        [
            Paragraph("BILLED TO", table_label_style),
            Paragraph("INVOICE ID", table_label_style),
            Paragraph("ISSUE DATE", table_label_style),
            Paragraph("STATUS", table_label_style),
        ],
        [
            Paragraph(safe(client_name), table_value_style),
            Paragraph(invoice_id, table_value_style),
            Paragraph(issued_at, table_value_style),
            Paragraph("PAID", paid_badge_style),
        ],
    ]

    metadata_table = Table(
        metadata,
        colWidths=[45 * mm, 40 * mm, 40 * mm, 40 * mm],
    )
    metadata_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BG),
                ("BACKGROUND", (0, 1), (-1, 1), WHITE),
                ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.append(metadata_table)
    story.append(Spacer(1, 18))

    # Amount highlight
    amount_block = Table(
        [
            [Paragraph("AMOUNT PAID", amount_label_style)],
            [Paragraph(f"{amount_display} {currency}", amount_style)],
            [
                Paragraph(
                    f"Settled on {network} • {token}",
                    amount_note_style,
                )
            ],
        ],
        colWidths=[165 * mm],
    )
    amount_block.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), SUCCESS_LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.8, SUCCESS),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 10),
                ("TOPPADDING", (0, 1), (-1, 1), 4),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 4),
            ]
        )
    )
    story.append(amount_block)
    story.append(Spacer(1, 18))

    # Line items
    story.append(Paragraph("Invoice Details", heading_style))

    line_items = [
        [
            Paragraph("DESCRIPTION", table_header_style),
            Paragraph("PROJECT", table_header_style),
            Paragraph("AMOUNT", table_header_style),
        ],
        [
            Paragraph(
                safe(f"Professional services — {project_title}"),
                table_body_style,
            ),
            Paragraph(project_id, table_body_style),
            Paragraph(
                f"{amount_display} {currency}",
                table_value_style,
            ),
        ],
        [
            Paragraph("<b>TOTAL PAID</b>", table_value_style),
            Paragraph("", table_body_style),
            Paragraph(
                f"<b>{amount_display} {currency}</b>",
                table_value_style,
            ),
        ],
    ]

    items_table = Table(
        line_items,
        colWidths=[95 * mm, 30 * mm, 40 * mm],
    )
    items_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("BACKGROUND", (0, -1), (-1, -1), LIGHT_BG),
                ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (2, 0), (2, -1), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(items_table)
    story.append(Spacer(1, 18))

    # Blockchain settlement
    story.append(Paragraph("Blockchain Settlement", heading_style))

    chain_rows = [
        [
            Paragraph("NETWORK", table_label_style),
            Paragraph(safe(network), table_body_style),
        ],
        [
            Paragraph("TOKEN", table_label_style),
            Paragraph(safe(token), table_body_style),
        ],
        [
            Paragraph("RECIPIENT WALLET", table_label_style),
            Paragraph(safe(recipient) or "—", table_body_style),
        ],
        [
            Paragraph("SENDER WALLET", table_label_style),
            Paragraph(safe(sender) or "—", table_body_style),
        ],
        [
            Paragraph("TRANSACTION HASH", table_label_style),
            Paragraph(safe(tx_hash) or "—", table_body_style),
        ],
        [
            Paragraph("BLOCK", table_label_style),
            Paragraph(str(block_number or "—"), table_body_style),
        ],
        [
            Paragraph("CONFIRMATIONS", table_label_style),
            Paragraph(str(confirmations or "—"), table_body_style),
        ],
    ]

    chain_table = Table(chain_rows, colWidths=[45 * mm, 120 * mm])
    chain_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), LIGHT_BG),
                ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(chain_table)
    story.append(Spacer(1, 20))

    # Notes
    story.append(
        Paragraph(
            "Payment has been independently verified on-chain. "
            "This invoice is issued only after a successful "
            "USDC transfer to the configured studio wallet.",
            body_style,
        )
    )
    story.append(Spacer(1, 16))

    # Signature
    signature_data = [
        [
            Paragraph("ISSUED BY", table_label_style),
            Paragraph("RECEIVED BY", table_label_style),
        ],
        [
            Paragraph(safe(signature_name), signature_style),
            Paragraph(safe(client_name), signature_style),
        ],
        [
            Paragraph("____________________________", small_style),
            Paragraph("____________________________", small_style),
        ],
        [
            Paragraph(safe(studio_name), table_body_style),
            Paragraph(safe(client_name), table_body_style),
        ],
        [
            Paragraph(safe(signature_title), small_style),
            Paragraph("Client", small_style),
        ],
    ]

    signature_table = Table(signature_data, colWidths=[82 * mm, 82 * mm])
    signature_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BG),
                ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(signature_table)

    document.build(
        story,
        onFirstPage=draw_header_footer,
        onLaterPages=draw_header_footer,
    )

    buffer.seek(0)
    return buffer


# =========================================================
# OWNER ORDER SUMMARY PDF
# =========================================================

def create_order_summary_pdf(job, answers=None, business_name="Studio"):
    """
    One-page operational summary for the owner to download.
    """
    import json
    from io import BytesIO
    from datetime import datetime
    from html import escape

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )
    from reportlab.lib.colors import HexColor
    from reportlab.lib.enums import TA_LEFT

    NAVY = HexColor("#12233F")
    ACCENT = HexColor("#168AAD")
    BORDER = HexColor("#D9E2EC")
    LIGHT = HexColor("#F4F7FA")

    def safe(value):
        return escape(str(value or "").strip()) or "—"

    if answers is None:
        raw = job["answers"] if hasattr(job, "keys") else (job.get("answers") if isinstance(job, dict) else "{}")
        if isinstance(raw, str):
            try:
                answers = json.loads(raw or "{}")
            except Exception:
                answers = {}
        elif isinstance(raw, dict):
            answers = raw
        else:
            answers = {}

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "os_title",
        parent=styles["Heading1"],
        fontSize=16,
        textColor=NAVY,
        spaceAfter=8,
    )
    h = ParagraphStyle(
        "os_h",
        parent=styles["Heading2"],
        fontSize=11,
        textColor=ACCENT,
        spaceBefore=10,
        spaceAfter=4,
    )
    body = ParagraphStyle(
        "os_body",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=13,
        textColor=NAVY,
    )

    job_id = job["id"] if hasattr(job, "keys") else job.get("id")
    client_name = job["client_name"] if hasattr(job, "keys") else job.get("client_name")
    client_username = ""
    try:
        client_username = job["client_username"] if hasattr(job, "keys") else job.get("client_username", "")
    except Exception:
        client_username = ""
    client_tid = job["client_telegram_id"] if hasattr(job, "keys") else job.get("client_telegram_id")
    status = job["status"] if hasattr(job, "keys") else job.get("status")
    payment_status = job["payment_status"] if hasattr(job, "keys") else job.get("payment_status")
    price = float((job["quoted_price"] if hasattr(job, "keys") else job.get("quoted_price")) or 0)
    currency = (job["currency"] if hasattr(job, "keys") else job.get("currency")) or "USD"
    tx = job["payment_tx_hash"] if hasattr(job, "keys") else job.get("payment_tx_hash")
    deadline = job["deadline"] if hasattr(job, "keys") else job.get("deadline")
    created = job["created_at"] if hasattr(job, "keys") else job.get("created_at")
    username_line = f"@{client_username}" if client_username else "—"

    story = [
        Paragraph(safe(business_name), title),
        Paragraph(f"Order summary · #{int(job_id):04d}", body),
        Spacer(1, 6),
        Paragraph("Client", h),
        Paragraph(f"<b>Name:</b> {safe(client_name)}", body),
        Paragraph(f"<b>Telegram username:</b> {safe(username_line)}", body),
        Paragraph(f"<b>Telegram ID:</b> {safe(client_tid)}", body),
        Paragraph("Status", h),
        Paragraph(f"<b>Job:</b> {safe(status)} · <b>Payment:</b> {safe(payment_status)}", body),
        Paragraph(f"<b>Quote:</b> ${price:.2f} {safe(currency)}", body),
        Paragraph(f"<b>Deadline:</b> {safe(deadline)}", body),
        Paragraph(f"<b>TX:</b> {safe(tx)}", body),
        Paragraph(f"<b>Created:</b> {safe(created)}", body),
        Paragraph("Intake answers", h),
    ]
    if answers:
        for key, value in answers.items():
            story.append(
                Paragraph(
                    f"<b>{safe(key)}:</b> {safe(value)}",
                    body,
                )
            )
    else:
        story.append(Paragraph("No answers stored.", body))

    proposal = job["proposal_text"] if hasattr(job, "keys") else job.get("proposal_text")
    if proposal:
        story.append(Paragraph("Proposal excerpt", h))
        excerpt = str(proposal)[:1200]
        story.append(Paragraph(safe(excerpt), body))

    story.append(Spacer(1, 12))
    story.append(
        Paragraph(
            f"Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC",
            body,
        )
    )

    doc.build(story)
    buffer.seek(0)
    return buffer


def create_orders_batch_pdf(jobs, business_name="Studio"):
    """
    Multi-order summary PDF for the owner.
    """
    import json
    from io import BytesIO
    from datetime import datetime
    from html import escape

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
    from reportlab.lib.colors import HexColor
    from reportlab.lib.enums import TA_LEFT

    NAVY = HexColor("#12233F")
    BORDER = HexColor("#D9E2EC")
    LIGHT = HexColor("#F4F7FA")

    def safe(value):
        return escape(str(value or "").strip()) or "—"

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "t", parent=styles["Heading1"], textColor=NAVY, fontSize=16, spaceAfter=8
    )
    body = ParagraphStyle(
        "b", parent=styles["Normal"], fontSize=9, leading=12, textColor=NAVY
    )
    h = ParagraphStyle(
        "h", parent=styles["Heading2"], textColor=NAVY, fontSize=11, spaceBefore=8, spaceAfter=4
    )

    story = [
        Paragraph(safe(business_name) + " — Orders export", title),
        Paragraph(
            f"Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC · {len(jobs or [])} order(s)",
            body,
        ),
        Spacer(1, 8),
    ]

    for i, job in enumerate(jobs or []):
        if hasattr(job, "keys") and not isinstance(job, dict):
            job = dict(job)
        jid = job.get("id", "?")
        uname = job.get("client_username") or ""
        uname_disp = f"@{uname}" if uname else "—"
        price = float(job.get("quoted_price") or 0)
        story.append(Paragraph(f"Order #{int(jid):04d}", h))
        data = [
            ["Client", safe(job.get("client_name"))],
            ["Telegram", uname_disp],
            ["Telegram ID", safe(job.get("client_telegram_id"))],
            ["Status", safe(job.get("status"))],
            ["Payment", safe(job.get("payment_status"))],
            ["Price", f"${price:.2f} {job.get('currency') or 'USD'}"],
            ["TX", safe(job.get("payment_tx_hash"))[:42]],
            ["Created", safe(job.get("created_at"))],
        ]
        table = Table(data, colWidths=[35 * mm, 130 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), LIGHT),
                    ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(table)
        raw = job.get("answers") or "{}"
        if isinstance(raw, str):
            try:
                answers = json.loads(raw or "{}")
            except Exception:
                answers = {}
        else:
            answers = raw if isinstance(raw, dict) else {}
        if answers:
            bits = "; ".join(
                f"{k}: {str(v)[:80]}" for k, v in list(answers.items())[:6]
            )
            story.append(Paragraph(safe(bits), body))
        story.append(Spacer(1, 10))
        if i < len(jobs) - 1 and (i + 1) % 4 == 0:
            story.append(PageBreak())

    doc.build(story)
    buffer.seek(0)
    return buffer
