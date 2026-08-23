from io import BytesIO
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import (
    getSampleStyleSheet,
    ParagraphStyle,
)
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)


def create_payment_receipt_pdf(
    *,
    studio_name,
    client_name,
    job_id,
    amount,
    currency,
    network,
    token,
    tx_hash,
    block_number,
    confirmations,
    recipient,
    sender,
):
    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"Payment Receipt SB-{int(job_id):04d}",
        author=studio_name,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReceiptTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=24,
        leading=29,
        spaceAfter=6,
    )

    subtitle_style = ParagraphStyle(
        "ReceiptSubtitle",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor(
            "#666666"
        ),
        spaceAfter=16,
    )

    heading_style = ParagraphStyle(
        "ReceiptHeading",
        parent=styles["Heading2"],
        fontSize=13,
        leading=17,
        spaceBefore=10,
        spaceAfter=8,
    )

    body_style = ParagraphStyle(
        "ReceiptBody",
        parent=styles["BodyText"],
        fontSize=10,
        leading=15,
    )

    small_style = ParagraphStyle(
        "ReceiptSmall",
        parent=styles["BodyText"],
        fontSize=8,
        leading=11,
        textColor=colors.HexColor(
            "#666666"
        ),
    )

    amount_style = ParagraphStyle(
        "ReceiptAmount",
        parent=styles["Heading1"],
        alignment=TA_CENTER,
        fontSize=24,
        leading=30,
        spaceBefore=10,
        spaceAfter=10,
    )

    story = []

    # -----------------------------------------------------
    # HEADER
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "PAYMENT RECEIPT",
            title_style,
        )
    )

    story.append(
        Paragraph(
            f"{studio_name}",
            subtitle_style,
        )
    )

    story.append(
        HRFlowable(
            width="100%",
            thickness=1,
            color=colors.HexColor(
                "#222222"
            ),
            spaceBefore=2,
            spaceAfter=18,
        )
    )

    # -----------------------------------------------------
    # RECEIPT NUMBER
    # -----------------------------------------------------

    receipt_id = (
        f"RCPT-SB-{int(job_id):04d}"
    )

    paid_at = datetime.now(
        timezone.utc
    ).strftime(
        "%d %B %Y, %H:%M UTC"
    )

    metadata = [
        [
            Paragraph(
                "<b>Receipt ID</b>",
                body_style,
            ),
            Paragraph(
                receipt_id,
                body_style,
            ),
        ],
        [
            Paragraph(
                "<b>Project</b>",
                body_style,
            ),
            Paragraph(
                f"SB-{int(job_id):04d}",
                body_style,
            ),
        ],
        [
            Paragraph(
                "<b>Client</b>",
                body_style,
            ),
            Paragraph(
                str(client_name),
                body_style,
            ),
        ],
        [
            Paragraph(
                "<b>Payment Date</b>",
                body_style,
            ),
            Paragraph(
                paid_at,
                body_style,
            ),
        ],
    ]

    table = Table(
        metadata,
        colWidths=[
            42 * mm,
            120 * mm,
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "BOTTOMPADDING",
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
                    "LINEBELOW",
                    (0, 0),
                    (-1, -1),
                    0.3,
                    colors.HexColor(
                        "#dddddd"
                    ),
                ),
            ]
        )
    )

    story.append(table)

    story.append(
        Spacer(
            1,
            12,
        )
    )

    # -----------------------------------------------------
    # AMOUNT
    # -----------------------------------------------------

    story.append(
        Paragraph(
            f"{currency} {float(amount):,.2f}",
            amount_style,
        )
    )

    story.append(
        Paragraph(
            "PAYMENT VERIFIED",
            ParagraphStyle(
                "Verified",
                parent=body_style,
                alignment=TA_CENTER,
                fontSize=11,
                leading=15,
            ),
        )
    )

    story.append(
        Spacer(
            1,
            15,
        )
    )

    # -----------------------------------------------------
    # PAYMENT DETAILS
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "Payment Details",
            heading_style,
        )
    )

    payment_rows = [
        [
            Paragraph(
                "<b>Network</b>",
                body_style,
            ),
            Paragraph(
                str(network),
                body_style,
            ),
        ],
        [
            Paragraph(
                "<b>Token</b>",
                body_style,
            ),
            Paragraph(
                str(token),
                body_style,
            ),
        ],
        [
            Paragraph(
                "<b>Blockchain</b>",
                body_style,
            ),
            Paragraph(
                "Base",
                body_style,
            ),
        ],
        [
            Paragraph(
                "<b>Block</b>",
                body_style,
            ),
            Paragraph(
                str(block_number),
                body_style,
            ),
        ],
        [
            Paragraph(
                "<b>Confirmations</b>",
                body_style,
            ),
            Paragraph(
                str(confirmations),
                body_style,
            ),
        ],
    ]

    payment_table = Table(
        payment_rows,
        colWidths=[
            45 * mm,
            117 * mm,
        ],
    )

    payment_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    colors.HexColor(
                        "#f5f5f5"
                    ),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.HexColor(
                        "#dddddd"
                    ),
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
            ]
        )
    )

    story.append(
        payment_table
    )

    # -----------------------------------------------------
    # BLOCKCHAIN TRANSACTION
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "Blockchain Transaction",
            heading_style,
        )
    )

    tx_display = (
        str(tx_hash)
    )

    blockchain_rows = [
        [
            Paragraph(
                "<b>TX Hash</b>",
                body_style,
            ),
            Paragraph(
                tx_display,
                small_style,
            ),
        ],
        [
            Paragraph(
                "<b>Sender</b>",
                body_style,
            ),
            Paragraph(
                str(sender),
                small_style,
            ),
        ],
        [
            Paragraph(
                "<b>Recipient</b>",
                body_style,
            ),
            Paragraph(
                str(recipient),
                small_style,
            ),
        ],
    ]

    blockchain_table = Table(
        blockchain_rows,
        colWidths=[
            45 * mm,
            117 * mm,
        ],
    )

    blockchain_table.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.HexColor(
                        "#dddddd"
                    ),
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
            ]
        )
    )

    story.append(
        blockchain_table
    )

    story.append(
        Spacer(
            1,
            20,
        )
    )

    story.append(
        HRFlowable(
            width="100%",
            thickness=0.5,
            color=colors.HexColor(
                "#cccccc"
            ),
            spaceBefore=5,
            spaceAfter=10,
        )
    )

    story.append(
        Paragraph(
            "This receipt confirms that the payment "
            "listed above was verified on Base mainnet "
            "using the configured "
            "USDC contract and studio wallet.",
            small_style,
        )
    )

    story.append(
        Spacer(
            1,
            8,
        )
    )

    story.append(
        Paragraph(
            "This document is automatically generated "
            "by Sovereign Studio.",
            small_style,
        )
    )

    document.build(
        story
    )

    buffer.seek(0)

    return buffer