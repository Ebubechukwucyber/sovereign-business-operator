import json
import os
import re
import asyncio

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from telegram.ext import (
    ContextTypes,
    ConversationHandler,
)

from datetime import datetime, timezone

from db import (
    get_owner_by_slug,
    ensure_owner_slug,
    get_owner,
    create_job,
    get_job,
    get_client_job,
    get_client_orders,
    get_latest_order,
    get_job_answers,
    save_job_answers,
    save_proposal,
    set_job_status,
    client_owns_job,
    save_job_analysis,
    set_payment_details,
    set_payment_tx_hash,
    mark_payment_pending,
    get_payment_details,
    confirm_payment,
    reject_payment,
    find_other_job_using_tx_hash,
    save_receipt_file,
    save_invoice_file,
    get_owner_signature,
)

from ai import (
    generate_proposal,
    template_proposal,
    estimate_price_with_ai,
    normalize_client_answers,
    next_intake_question,
)

from payment_verifier import verify_usdc_payment
from payment_receipt import create_payment_receipt_pdf

from pricing import calculate_price
from pdf_generator import create_proposal_pdf, create_invoice_pdf


# =========================================================
# STATES
# =========================================================

NAME = 1
QUESTION_1 = 2
QUESTION_2 = 3
QUESTION_3 = 4
QUESTION_4 = 5
QUESTION_5 = 6
EDIT_REQUEST = 7

QUESTION_STATES = [
    QUESTION_1,
    QUESTION_2,
    QUESTION_3,
    QUESTION_4,
    QUESTION_5,
]


# =========================================================
# QUESTIONS
# =========================================================

GENERIC_QUESTIONS = [
    (
        "project",
        "Thanks — let's get a clear picture of the work.\n\n"
        "In your own words, what do you need done?",
    ),
    (
        "requirements",
        "Got it.\n\n"
        "What matters most for a good result? "
        "Any must-haves we should include?",
    ),
    (
        "quantity",
        "Helpful.\n\n"
        "About how large is this? "
        "(items, people, hours, pages, locations, "
        "or whatever measures size for this job)",
    ),
    (
        "deadline",
        "When would you like this completed?",
    ),
    (
        "additional",
        "Almost done.\n\n"
        "Anything else we should know before we prepare "
        "your quote and proposal?",
    ),
]


# =========================================================
# HELPERS
# =========================================================

def clean_text(value):
    if value is None:
        return ""

    return str(value).strip()


def safe_float(value, fallback=0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def row_get(row, key, default=None):
    """
    Safely read a value from sqlite3.Row, dict or similar object.
    """

    if row is None:
        return default

    try:
        return row[key]
    except (KeyError, IndexError, TypeError):
        pass

    try:
        return row.get(key, default)
    except AttributeError:
        return default


def get_rules(owner):
    if not owner:
        return {}

    raw = row_get(
        owner,
        "business_rules",
        "",
    )

    if not raw:
        return {}

    if isinstance(raw, dict):
        return raw

    try:
        rules = json.loads(raw)

        if isinstance(rules, dict):
            return rules

    except (
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ):
        pass

    return {}


def rule_number(
    rules,
    key,
    default=0,
):
    try:
        return float(
            rules.get(
                key,
                default,
            )
        )
    except (
        TypeError,
        ValueError,
    ):
        return float(default)




def owner_for_job(job, context=None):
    """Resolve the business owner for a job (multi-tenant safe)."""
    from config import OWNER_TELEGRAM_ID
    biz = 0
    if job is not None:
        try:
            biz = int(job["business_id"] or 0)
        except Exception:
            biz = 0
    if not biz and context is not None:
        try:
            biz = int(context.user_data.get("owner_id") or 0)
        except Exception:
            biz = 0
    if not biz:
        biz = OWNER_TELEGRAM_ID or 0
    if not biz:
        return None
    return get_owner(biz)


def payment_network_label(value=None) -> str:
    """Always show Base mainnet to clients — never Sepolia testnet labels."""
    text = str(value or "Base").strip()
    low = text.lower()
    if "sepolia" in low or "testnet" in low:
        return "Base"
    if not text or text.lower() == "base":
        return "Base"
    return text


def _email_owner_paid_order(job_id, client_name, client_username, tx_hash, amount, owner_telegram_id=None):
    """
    Email owner after payment.
    Prefer Resend API; fall back to SMTP if configured.
    Recipient: owner.notify_email, else OWNER_NOTIFY_EMAIL env.
    """
    try:
        from config import (
            EMAIL_ENABLED,
            RESEND_API_KEY,
            EMAIL_FROM,
            OWNER_NOTIFY_EMAIL,
            OWNER_TELEGRAM_ID,
            SMTP_HOST,
            SMTP_PORT,
            SMTP_USER,
            SMTP_PASSWORD,
            SMTP_FROM,
        )
        from db import get_owner
    except Exception as error:
        print("Email config import failed:", error)
        return

    if not EMAIL_ENABLED:
        return

    to_email = ""
    try:
        owner = get_owner(OWNER_TELEGRAM_ID)
        if owner is not None:
            to_email = (owner["notify_email"] if "notify_email" in owner.keys() else "") or ""
            to_email = str(to_email).strip()
    except Exception:
        to_email = ""

    if not to_email:
        to_email = OWNER_NOTIFY_EMAIL

    if not to_email or "@" not in to_email:
        print("Owner email notify skipped: no notify email configured")
        return

    uname = f"@{client_username}" if client_username else "—"
    subject = f"[Sovereign] Payment confirmed — Project #{job_id}"
    text_body = (
        f"Payment confirmed for Project #{job_id}\n\n"
        f"Client: {client_name}\n"
        f"Telegram: {uname}\n"
        f"Amount: {amount} USDC\n"
        f"Network: Base\n"
        f"TX: {tx_hash}\n"
    )
    html_body = (
        f"<h2>Payment confirmed</h2>"
        f"<p><strong>Project</strong> #{job_id}</p>"
        f"<p><strong>Client</strong> {client_name}<br/>"
        f"<strong>Telegram</strong> {uname}</p>"
        f"<p><strong>Amount</strong> {amount} USDC on Base</p>"
        f"<p><strong>TX</strong> <code>{tx_hash}</code></p>"
    )
    from_addr = EMAIL_FROM or SMTP_FROM or "onboarding@resend.dev"

    # Prefer Resend
    if RESEND_API_KEY:
        try:
            import httpx
            resp = httpx.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": from_addr,
                    "to": [to_email],
                    "subject": subject,
                    "html": html_body,
                    "text": text_body,
                },
                timeout=20.0,
            )
            if resp.status_code >= 400:
                print("Resend error:", resp.status_code, resp.text[:300])
            else:
                print("Resend ok:", resp.status_code)
            return
        except Exception as error:
            print("Resend notify failed:", error)

    # SMTP fallback
    if not (SMTP_HOST and from_addr):
        return
    try:
        import smtplib
        from email.mime.text import MIMEText
        msg = MIMEText(html_body, "html")
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = to_email
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
            server.starttls()
            if SMTP_USER and SMTP_PASSWORD:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(from_addr, [to_email], msg.as_string())
    except Exception as error:
        print("Owner email notify failed:", error)



async def notify_owner_payment_confirmed(
    context,
    job_id,
    client_name,
    tx_hash,
    amount,
    confirmations,
    receipt_pdf=None,
    invoice_pdf=None,
    client_username="",
):
    from config import OWNER_TELEGRAM_ID
    from db import get_job

    owner_chat_id = OWNER_TELEGRAM_ID
    try:
        job = get_job(job_id)
        if job is not None:
            biz = int(job["business_id"] or 0)
            if biz:
                owner_chat_id = biz
    except Exception as error:
        print("notify: resolve business_id failed:", error)

    if not owner_chat_id:
        print("notify: no owner chat id")
        return

    uname = f"@{client_username}" if client_username else "—"
    text = (
        "💰 Payment confirmed\n\n"
        f"Project #{job_id}\n"
        f"Client: {client_name}\n"
        f"Telegram: {uname}\n"
        f"Amount: {amount} USDC\n"
        f"Network: Base\n"
        f"Confirmations: {confirmations}\n\n"
        f"TX hash:\n{tx_hash}\n\n"
        "The job has been marked PAID."
    )
    try:
        _email_owner_paid_order(
            job_id,
            client_name,
            client_username,
            tx_hash,
            amount,
            owner_telegram_id=owner_chat_id,
        )
    except Exception as error:
        print("Email notify wrapper:", error)

    try:
        await context.bot.send_message(
            chat_id=owner_chat_id,
            text=text,
        )
    except Exception as error:
        print("Telegram owner notify failed:", error)
        return

    if receipt_pdf is not None:
        try:
            receipt_pdf.seek(0)
            await context.bot.send_document(
                chat_id=owner_chat_id,
                document=receipt_pdf,
                filename=f"Receipt_SB-{int(job_id):04d}.pdf",
                caption=f"📄 Receipt for Project #{job_id}",
            )
        except Exception:
            pass

    if invoice_pdf is not None:
        try:
            invoice_pdf.seek(0)
            await context.bot.send_document(
                chat_id=owner_chat_id,
                document=invoice_pdf,
                filename=f"Invoice_SB-{int(job_id):04d}.pdf",
                caption=f"🧾 Invoice for Project #{job_id}",
            )
        except Exception:
            pass



def parse_iso_timestamp(value):
    text = clean_text(value)

    if not text:
        return 0

    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"

        parsed = datetime.fromisoformat(text)

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return int(parsed.timestamp())
    except (TypeError, ValueError):
        return 0


def extract_number(text):
    if not text:
        return None

    match = re.search(
        r"\b(\d+(?:\.\d+)?)\b",
        str(text),
    )

    if not match:
        return None

    try:
        number = float(match.group(1))

        if number <= 0:
            return None

        return number

    except ValueError:
        return None


# =========================================================
# TIMELINE
# =========================================================

def extract_timeline_from_text(text):
    text = clean_text(text).lower()

    if not text:
        return None

    patterns = [
        (
            r"(?:timeline|deadline|delivery|deliver|complete|completion)"
            r".{0,80}?"
            r"(\d+(?:\.\d+)?)\s*"
            r"(day|days|week|weeks)"
        ),
        (
            r"(?:change|make|move|reduce|increase|set)"
            r".{0,80}?"
            r"(\d+(?:\.\d+)?)\s*"
            r"(day|days|week|weeks)"
        ),
        (
            r"\bwithin\s+"
            r"(\d+(?:\.\d+)?)\s*"
            r"(day|days|week|weeks)\b"
        ),
        (
            r"\bin\s+"
            r"(\d+(?:\.\d+)?)\s*"
            r"(day|days|week|weeks)\b"
        ),
        (
            r"\b(\d+(?:\.\d+)?)\s*"
            r"(day|days|week|weeks)\b"
        ),
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if not match:
            continue

        try:
            value = float(match.group(1))
        except ValueError:
            continue

        if value <= 0:
            continue

        unit = match.group(2).lower()

        if unit.startswith("week"):
            unit = "week" if value == 1 else "weeks"
        else:
            unit = "day" if value == 1 else "days"

        return f"{value:g} {unit}"

    return None


def normalize_timeline(value):
    value = clean_text(value)

    if not value:
        return "7 days"

    extracted = extract_timeline_from_text(value)

    if extracted:
        return extracted

    return value


# =========================================================
# QUANTITY
# =========================================================

def extract_quantity_from_text(text):
    text = clean_text(text).lower()

    if not text:
        return None

    patterns = [
        r"\b(?:for|of|with)\s+"
        r"(\d+(?:\.\d+)?)\s+"
        r"(?:people|person|persons|guests|guest|clients|"
        r"items|item|units|unit|customers|customer)\b",

        r"\b(\d+(?:\.\d+)?)\s+"
        r"(?:people|person|persons|guests|guest|clients|"
        r"items|item|units|unit|customers|customer)\b",

        r"\b(?:quantity|qty|amount)\s*"
        r"(?:to|of|=)?\s*"
        r"(\d+(?:\.\d+)?)\b",

        r"\b(?:make|change|set)\s+"
        r"(?:it|quantity)\s+"
        r"(?:to\s+)?"
        r"(\d+(?:\.\d+)?)\b",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if not match:
            continue

        try:
            value = float(match.group(1))
        except ValueError:
            continue

        if value <= 0:
            continue

        return f"{value:g}"

    return None


# =========================================================
# PROJECT ANALYSIS
# =========================================================

def analyze_project(
    owner,
    answers,
):
    rules = get_rules(owner)

    combined = " ".join(
        clean_text(value)
        for value in answers.values()
    ).lower()

    complexity_score = 0
    reasons = []

    quantity = extract_number(
        answers.get(
            "quantity",
            "",
        )
    )

    large_quantity_threshold = rule_number(
        rules,
        "large_quantity_threshold",
        20,
    )

    if (
        quantity is not None
        and quantity >= large_quantity_threshold
    ):
        complexity_score += 2

        reasons.append(
            f"quantity of {quantity:g} exceeds "
            f"the normal threshold of "
            f"{large_quantity_threshold:g}"
        )

    high_complexity_terms = [
        "urgent",
        "complex",
        "complicated",
        "large",
        "massive",
        "custom",
        "multiple locations",
        "multiple teams",
        "multiple people",
        "many items",
        "bulk",
        "full package",
        "end to end",
        "everything",
        "complete",
        "advanced",
        "high volume",
    ]

    found_terms = [
        term
        for term in high_complexity_terms
        if term in combined
    ]

    if found_terms:
        complexity_score += min(
            len(found_terms),
            3,
        )

        reasons.append(
            "complexity indicators: "
            + ", ".join(found_terms[:5])
        )

    rush_terms = [
        "today",
        "tonight",
        "tomorrow",
        "within 24 hours",
        "24 hours",
        "48 hours",
        "as soon as possible",
        "asap",
        "urgent",
        "immediately",
    ]

    if any(
        term in combined
        for term in rush_terms
    ):
        complexity_score += 1
        reasons.append(
            "rush delivery requested"
        )

    if complexity_score >= 4:
        complexity = "HIGH"
    elif complexity_score >= 2:
        complexity = "MEDIUM"
    else:
        complexity = "NORMAL"

    normal_buffer = rule_number(
        rules,
        "buffer_percent",
        0,
    )

    complexity_buffer = rule_number(
        rules,
        "complexity_buffer_percent",
        0,
    )

    days_buffer = rule_number(
        rules,
        "complexity_days_buffer",
        0,
    )

    buffer_percent = normal_buffer

    if complexity == "HIGH":
        buffer_percent += complexity_buffer
    elif complexity == "MEDIUM":
        buffer_percent += complexity_buffer / 2

    cushion_parts = []

    if buffer_percent > 0:
        cushion_parts.append(
            f"{buffer_percent:g}% scope buffer"
        )

    if (
        days_buffer > 0
        and complexity in (
            "MEDIUM",
            "HIGH",
        )
    ):
        cushion_parts.append(
            f"{days_buffer:g} additional days"
        )

    if cushion_parts:
        cushion_applied = " + ".join(
            cushion_parts
        )
    else:
        cushion_applied = "No additional cushion"

    internal_analysis = (
        f"Project complexity: {complexity}. "
    )

    if reasons:
        internal_analysis += (
            "Reasons: "
            + "; ".join(reasons)
            + "."
        )
    else:
        internal_analysis += (
            "No unusual complexity indicators "
            "were detected."
        )

    return {
        "complexity": complexity,
        "complexity_score": complexity_score,
        "buffer_percent": buffer_percent,
        "days_buffer": days_buffer,
        "cushion_applied": cushion_applied,
        "internal_analysis": internal_analysis,
    }


# =========================================================
# PRICE
# =========================================================

def calculate_business_price(
    owner,
    answers,
):
    """
    Price from rules engine when possible.
    Always fall back to owner min/max so a quote can still
    be issued if detailed business_rules are empty or AI fails.
    """
    rules = get_rules(owner)

    # Seed rules from owner min/max so the engine has bounds
    # even when business_rules JSON was never configured.
    min_price = safe_float(
        row_get(owner, "min_price", 150),
        150,
    )
    max_price = safe_float(
        row_get(owner, "max_price", 400),
        400,
    )
    if min_price <= 0:
        min_price = 150.0
    if max_price < min_price:
        max_price = min_price

    if not isinstance(rules, dict):
        rules = {}
    else:
        rules = dict(rules)

    rules.setdefault("enabled", True)
    rules.setdefault("currency", "USD")
    rules.setdefault("model", "fixed")
    rules.setdefault("minimum", min_price)
    rules.setdefault("maximum", max_price)
    # Fixed model needs a base_fee — near minimum, not midpoint
    if safe_float(rules.get("base_fee"), 0) <= 0:
        # Seed near minimum so simple jobs stay cheap
        rules["base_fee"] = round(min_price, 2)

    analysis = analyze_project(
        owner,
        answers,
    )

    quantity = extract_number(
        answers.get(
            "quantity",
            "",
        )
    )

    deadline_text = normalize_timeline(
        answers.get(
            "deadline",
            "7 days",
        )
    )

    deadline_days = 0

    timeline_match = re.search(
        r"(\d+(?:\.\d+)?)\s*"
        r"(day|days|week|weeks)",
        deadline_text.lower(),
    )

    if timeline_match:
        deadline_days = float(
            timeline_match.group(1)
        )

        if timeline_match.group(2).startswith("week"):
            deadline_days *= 7

    complexity = str(
        analysis.get(
            "complexity",
            "NORMAL",
        )
    ).lower()

    if complexity == "normal":
        complexity = "low"

    result = calculate_price(
        pricing_rules=rules,
        quantity=quantity,
        unit=None,
        hours=None,
        deadline_days=deadline_days,
        complexity=complexity,
    )

    if result.get("success") and result.get("price") is not None:
        price = round(float(result["price"]), 2)
        # Keep inside owner band
        price = max(min_price, min(max_price, price))
        return (
            price,
            {
                **analysis,
                "pricing_result": result,
                "pricing_source": "rules",
            },
        )

    # Last resort: never block the client with price 0.
    # Stay near the low end of the band for typical jobs.
    complexity = str(
        analysis.get("complexity", "NORMAL")
    ).upper()
    span = max(max_price - min_price, 0)
    if complexity == "HIGH":
        frac = 0.55
    elif complexity in ("MEDIUM", "MED"):
        frac = 0.22
    else:
        frac = 0.0  # simple → owner minimum
    fallback = round(min_price + span * frac, 2)
    return (
        fallback,
        {
            **analysis,
            "pricing_error": result.get(
                "reason",
                "Used owner band with job-size heuristic.",
            ),
            "pricing_result": result,
            "pricing_source": "min_max_fallback",
            "cushion_applied": analysis.get(
                "cushion_applied",
                "band_heuristic",
            ),
        },
    )


# =========================================================
# PROGRESS
# =========================================================

async def proposal_progress(message):
    steps = [
        (10, "Reviewing project details..."),
        (25, "Analyzing project scope..."),
        (45, "Calculating project investment..."),
        (65, "Preparing your business proposal..."),
        (80, "Formatting professional proposal..."),
        (95, "Generating PDF document..."),
        (100, "Proposal ready."),
    ]

    for percent, status in steps:

        bar_length = 20

        filled = int(
            bar_length * percent / 100
        )

        bar = (
            "█" * filled
            + "░" * (bar_length - filled)
        )

        try:
            await message.edit_text(
                "Preparing your proposal...\n\n"
                f"{bar} {percent}%\n\n"
                f"{status}"
            )
        except Exception:
            pass

        if percent != 100:
            await asyncio.sleep(0.45)


# =========================================================
# PDF
# =========================================================

def build_proposal_pdf(
    owner,
    job_id,
    client_name,
    answers,
    proposal,
    price,
    change_request="",
):
    studio_name = clean_text(
        row_get(
            owner,
            "name",
            "Sovereign Studio",
        )
    )

    timeline = normalize_timeline(
        answers.get(
            "deadline",
            "7 days",
        )
    )

    project_title = clean_text(
        answers.get(
            "project",
            "Project Proposal",
        )
    )

    if len(project_title) > 80:
        project_title = (
            project_title[:77]
            + "..."
        )

    proposal_id = f"SB-{int(job_id):04d}"

    return create_proposal_pdf(
        studio_name=studio_name,
        client_name=client_name,
        proposal_text=proposal,
        price=price,
        timeline=timeline,
        proposal_id=proposal_id,
        change_request=change_request,
        project_title=project_title,
    )


# =========================================================
# CLIENT HOME
# =========================================================

async def start_client(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data.clear()

    from config import OWNER_TELEGRAM_ID

    # Multi-tenant: /start <slug> or /start biz_<slug>
    owner = None
    args = []
    if context.args:
        args = list(context.args)
    elif update.message and update.message.text:
        parts = update.message.text.split(maxsplit=1)
        if len(parts) > 1:
            args = parts[1].split()

    if args:
        raw = (args[0] or "").strip()
        if raw.lower().startswith("biz_"):
            raw = raw[4:]
        owner = get_owner_by_slug(raw)
        if owner is None and raw.isdigit():
            owner = get_owner(int(raw))

    started_with_slug = bool(args)
    if owner is None:
        owner = get_owner(OWNER_TELEGRAM_ID)

    if owner is not None:
        context.user_data["owner_id"] = row_get(
            owner, "telegram_id", OWNER_TELEGRAM_ID
        )
    else:
        context.user_data["owner_id"] = OWNER_TELEGRAM_ID

    if owner is None or not int(row_get(owner, "setup_complete", 0) or 0):
        if started_with_slug:
            msg = (
                "No business found for that invite code.\n\n"
                "Ask the studio for their correct invite link, for example:\n"
                "/start their-business-slug\n\n"
                "Owners: send /setup to create your business."
            )
        else:
            msg = (
                "Welcome to Sovereign Business Operator.\n\n"
                "This bot runs many studios. To see a company, you need "
                "their invite link.\n\n"
                "• Clients: ask the business for their link "
                "(/start their-slug)\n"
                "• Owners: create your studio with /setup\n\n"
                "Tap a button below to continue."
            )
        guide_kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "How it works",
                        callback_data="client_guide",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "I am an owner",
                        callback_data="owner_hint_setup",
                    )
                ],
            ]
        )
        target = update.effective_message
        if target:
            await target.reply_text(msg, reply_markup=guide_kb)
        return

    business_name = "our studio"
    niche = ""
    services = ""

    if owner:
        business_name = clean_text(
            row_get(owner, "name", "")
        ) or "our studio"
        niche = clean_text(row_get(owner, "niche", ""))
        services = clean_text(
            row_get(owner, "services_text", "")
        )

    keyboard = [
        [
            InlineKeyboardButton(
                "➕ New order",
                callback_data="new_order",
            )
        ],
        [
            InlineKeyboardButton(
                "📦 My orders",
                callback_data="my_orders",
            )
        ],
        [
            InlineKeyboardButton(
                "🛠 Our services",
                callback_data="services",
            )
        ],
        [
            InlineKeyboardButton(
                "💬 Contact us",
                callback_data="contact_studio",
            )
        ],
        [
            InlineKeyboardButton(
                "📖 How to order",
                callback_data="client_guide",
            )
        ],
    ]

    # Organic welcome that reflects the configured business
    lines = [f"Welcome to {business_name}."]

    if niche:
        lines.append(
            f"We specialize in {niche}."
        )
    else:
        lines.append(
            "Glad you're here — we're ready to help."
        )

    if services:
        lines.append("")
        lines.append(f"What we offer: {services}")

    lines.append("")
    lines.append(
        "Tell us what you need and we'll scope it, "
        "send a clear proposal, and get you a quote."
    )
    lines.append("")
    lines.append(
        "Tap New order when you're ready to begin."
    )

    text = "\n".join(lines)

    markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        query = update.callback_query

        await query.answer()

        try:
            await query.edit_message_text(
                text,
                reply_markup=markup,
            )
        except Exception:
            if query.message:
                await query.message.reply_text(
                    text,
                    reply_markup=markup,
                )

    elif update.message:
        await update.message.reply_text(
            text,
            reply_markup=markup,
        )


async def client_home(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await start_client(
        update,
        context,
    )


# =========================================================
# NEW ORDER
# =========================================================

async def new_order_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    await query.answer()

    from config import OWNER_TELEGRAM_ID

    # Keep the business from /start slug — do not reset to env owner
    bound_id = context.user_data.get("owner_id") or OWNER_TELEGRAM_ID
    owner = get_owner(bound_id)

    if owner is None and OWNER_TELEGRAM_ID:
        owner = get_owner(OWNER_TELEGRAM_ID)
        bound_id = OWNER_TELEGRAM_ID

    if owner is None:
        await query.edit_message_text(
            "The business is not fully configured yet.\n\n"
            "Open the studio invite link first (/start their-slug)."
        )
        return ConversationHandler.END

    # Preserve owner binding across clear
    context.user_data.clear()
    context.user_data["owner_id"] = int(
        row_get(owner, "telegram_id", bound_id) or bound_id
    )
    context.user_data["answers"] = {}
    context.user_data["question_index"] = 0

    await query.edit_message_text(
        "Great. Let's get a few details so we can "
        "understand exactly what you need.\n\n"
        "What is your name?"
    )

    return NAME


# =========================================================
# CLIENT NAME
# =========================================================

async def handle_client_name(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    name = clean_text(
        update.message.text
    )

    if not name:
        await update.message.reply_text(
            "Please enter your name."
        )

        return NAME

    context.user_data["client_name"] = name

    # First question tailored to the business when LLM is available
    first_q = GENERIC_QUESTIONS[0][1]
    try:
        from config import OWNER_TELEGRAM_ID

        owner = get_owner(
            context.user_data.get(
                "owner_id",
                OWNER_TELEGRAM_ID,
            )
        )
        if owner is not None:
            niche = clean_text(row_get(owner, "niche", ""))
            services = clean_text(
                row_get(owner, "services_text", "")
            )
            business = clean_text(
                row_get(owner, "name", "us")
            )
            dynamic = await next_intake_question(
                owner,
                {
                    "client_name": name,
                    "note": (
                        f"Opening question for {business}. "
                        f"Niche: {niche}. Services: {services}."
                    ),
                },
                question_index=0,
                total_questions=len(GENERIC_QUESTIONS),
            )
            if dynamic:
                first_q = dynamic
    except Exception as error:
        print("First intake question failed:", error)

    await update.message.reply_text(first_q)

    return QUESTION_1


# =========================================================
# INTAKE
# =========================================================

async def handle_intake_answer(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    answer = clean_text(
        update.message.text
    )

    question_index = context.user_data.get(
        "question_index",
        0,
    )

    if not answer:
        await update.message.reply_text(
            "Please provide an answer so we can "
            "understand the project."
        )

        return QUESTION_STATES[
            min(
                question_index,
                len(QUESTION_STATES) - 1,
            )
        ]

    answers = context.user_data.setdefault(
        "answers",
        {},
    )
    # Keep originals for debugging; proposals use refined copy later
    raw_answers = context.user_data.setdefault(
        "answers_raw",
        {},
    )

    if question_index >= len(GENERIC_QUESTIONS):
        return ConversationHandler.END

    key = GENERIC_QUESTIONS[
        question_index
    ][0]

    answers[key] = answer
    raw_answers[key] = answer

    question_index += 1

    context.user_data["question_index"] = question_index

    if question_index < len(GENERIC_QUESTIONS):
        # Dynamic follow-up from AI; generic text as fallback
        next_text = ""
        try:
            from config import OWNER_TELEGRAM_ID

            owner = get_owner(
                context.user_data.get(
                    "owner_id",
                    OWNER_TELEGRAM_ID,
                )
            )
            if owner is not None:
                next_text = await next_intake_question(
                    owner,
                    answers,
                    question_index,
                    total_questions=len(GENERIC_QUESTIONS),
                )
        except Exception as error:
            print("Dynamic intake question failed:", error)

        if not next_text:
            next_text = GENERIC_QUESTIONS[question_index][1]

        await update.message.reply_text(next_text)

        return QUESTION_STATES[question_index]

    await finish_intake(
        update,
        context,
    )

    return ConversationHandler.END


# =========================================================
# FINISH INTAKE
# =========================================================

async def finish_intake(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user_id = update.effective_user.id

    owner_id = context.user_data.get(
        "owner_id"
    )

    if not owner_id:
        from config import OWNER_TELEGRAM_ID

        owner_id = OWNER_TELEGRAM_ID

    owner = get_owner(owner_id)

    if owner is None:
        await update.message.reply_text(
            "The business is currently unavailable."
        )

        return

    client_name = context.user_data.get(
        "client_name",
        update.effective_user.first_name or "Client",
    )

    answers = context.user_data.get(
        "answers",
        {},
    )

    job_id = create_job(
        client_telegram_id=user_id,
        client_name=client_name,
        client_username=(
            update.effective_user.username or ""
        ),
        business_id=int(owner_id or 0),
    )

    await update.message.reply_text(
        "Thanks — reviewing your requirements and "
        "preparing a tailored quote and proposal."
    )

    # Clean / structure messy client text for professional docs
    try:
        answers = await normalize_client_answers(
            answers,
            owner=owner,
        )
    except Exception as error:
        print("Answer normalization failed:", error)

    context.user_data["answers"] = answers
    save_job_answers(
        job_id,
        answers,
    )

    # Prefer AI estimate (clamped to owner min/max).
    # Fall back to the existing rule engine so jobs never break.
    ai_estimate = None
    try:
        ai_estimate = await estimate_price_with_ai(
            owner,
            answers,
        )
    except Exception as error:
        print("AI pricing failed:", error)

    if ai_estimate and ai_estimate.get("price", 0) > 0:
        price = float(ai_estimate["price"])
        analysis = {
            "complexity": ai_estimate.get(
                "complexity",
                "MEDIUM",
            ),
            "cushion_applied": "ai_estimate",
            "internal_analysis": ai_estimate.get(
                "reasoning",
                "AI-assisted price within owner bounds.",
            ),
            "in_scope": ai_estimate.get("in_scope", []),
            "out_of_scope": ai_estimate.get(
                "out_of_scope",
                [],
            ),
            "pricing_source": "ai",
        }
    else:
        price, analysis = calculate_business_price(
            owner,
            answers,
        )
        analysis["pricing_source"] = "rules"

    save_job_analysis(
        job_id,
        complexity=analysis.get("complexity", "MEDIUM"),
        cushion_applied=analysis.get(
            "cushion_applied",
            "",
        ),
        internal_analysis=analysis.get(
            "internal_analysis",
            "",
        ),
    )

    if price <= 0:
        min_price = safe_float(row_get(owner, "min_price", 150), 150)
        max_price = safe_float(row_get(owner, "max_price", 400), 400)
        if min_price <= 0:
            min_price = 150.0
        if max_price < min_price:
            max_price = min_price
        span = max(max_price - min_price, 0)
        price = round(min_price, 2)
        analysis = analysis or {}
        analysis["pricing_source"] = "min_max_fallback"
        analysis["internal_analysis"] = (
            analysis.get("internal_analysis")
            or "Quoted near the low end of the studio price range."
        )
        analysis.setdefault("complexity", "LOW")
        analysis.setdefault("cushion_applied", "band_low")

    # -----------------------------------------------------
    # GENERATE PROPOSAL
    # -----------------------------------------------------

    try:
        proposal = await generate_proposal(
            owner,
            answers,
            price,
            analysis=analysis,
        )
    except Exception:
        proposal = template_proposal(
            owner,
            answers,
            price,
        )

    save_proposal(
        job_id,
        price,
        proposal,
    )

    # -----------------------------------------------------
    # PROGRESS
    # -----------------------------------------------------

    progress_message = await update.message.reply_text(
        "Preparing your proposal...\n\n"
        "░░░░░░░░░░░░░░░░░░░░ 0%"
    )

    try:
        await proposal_progress(
            progress_message
        )

        pdf = build_proposal_pdf(
            owner=owner,
            job_id=job_id,
            client_name=client_name,
            answers=answers,
            proposal=proposal,
            price=price,
        )

        await update.message.reply_document(
            document=pdf,
            filename=f"Proposal_SB-{job_id:04d}.pdf",
            caption=(
                f"📄 Proposal SB-{job_id:04d}\n\n"
                "Your professional business proposal "
                "is ready."
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "💳 Payment",
                            callback_data=f"pay_{job_id}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "📄 View Proposal",
                            callback_data=f"proposal_{job_id}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "✏️ Request Changes",
                            callback_data=f"edit_{job_id}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "🏠 Home",
                            callback_data="client_home",
                        )
                    ],
                ]
            ),
        )

        try:
            await progress_message.edit_text(
                "Proposal ready.\n\n"
                "████████████████████ 100%\n\n"
                "📄 PDF generated successfully."
            )
        except Exception:
            pass

    except Exception as error:
        try:
            await progress_message.edit_text(
                "Proposal preparation failed.\n\n"
                f"Error: {error}"
            )
        except Exception:
            pass

        await update.message.reply_text(
            "I prepared the proposal, but the PDF "
            "could not be generated.\n\n"
            f"Error: {error}"
        )


# =========================================================
# EDIT ORDER START
# =========================================================

async def edit_order_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    await query.answer()

    match = re.match(
        r"^edit_(\d+)$",
        query.data or "",
    )

    if not match:
        await _send_callback_text(
            query,
            "Invalid project.",
            prefer_new_message=True,
        )
        return ConversationHandler.END

    job_id = int(match.group(1))
    user_id = update.effective_user.id

    if not client_owns_job(
        user_id,
        job_id,
    ):
        await _send_callback_text(
            query,
            "You don't have access to this project.",
            prefer_new_message=True,
        )
        return ConversationHandler.END

    context.user_data.clear()
    context.user_data["edit_job_id"] = job_id

    # Always send a new text message — Request Changes is often
    # pressed on the proposal PDF, and edit_message_text fails
    # on documents (same class of bug as Payment).
    await _send_callback_text(
        query,
        "Tell us what you'd like to change "
        "about the project or proposal.\n\n"
        "Type your changes in one message.",
        prefer_new_message=True,
    )

    return EDIT_REQUEST


# =========================================================
# EDIT REQUEST
# =========================================================

async def handle_edit_request(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    job_id = context.user_data.get(
        "edit_job_id"
    )

    if not job_id:
        await update.message.reply_text(
            "I couldn't identify the project."
        )

        return ConversationHandler.END

    user_id = update.effective_user.id

    if not client_owns_job(
        user_id,
        job_id,
    ):
        await update.message.reply_text(
            "You don't have access to this project."
        )

        return ConversationHandler.END

    request = clean_text(
        update.message.text
    )

    if not request:
        await update.message.reply_text(
            "Please describe the change you'd like "
            "to make."
        )

        return EDIT_REQUEST

    job = get_job(job_id)

    if not job:
        await update.message.reply_text(
            "That project could not be found."
        )

        return ConversationHandler.END

    answers = get_job_answers(job_id)

    if not isinstance(answers, dict):
        answers = dict(answers or {})

    answers["client_revision_request"] = request

    # -----------------------------------------------------
    # TIMELINE
    # -----------------------------------------------------

    new_timeline = extract_timeline_from_text(
        request
    )

    if new_timeline:
        answers["deadline"] = new_timeline

    # -----------------------------------------------------
    # QUANTITY
    # -----------------------------------------------------

    new_quantity = extract_quantity_from_text(
        request
    )

    if new_quantity:
        old_quantity = clean_text(
            answers.get(
                "quantity",
                "",
            )
        )

        if old_quantity:
            answers["quantity"] = (
                f"{new_quantity} "
                f"(updated from {old_quantity})"
            )
        else:
            answers["quantity"] = new_quantity

    # -----------------------------------------------------
    # CATERING / PARTY CONTEXT
    # -----------------------------------------------------

    revision_lower = request.lower()

    if (
        new_quantity
        and (
            "catering" in revision_lower
            or "birthday" in revision_lower
            or "food" in revision_lower
            or "party" in revision_lower
        )
    ):
        previous_requirements = clean_text(
            answers.get(
                "requirements",
                "",
            )
        )

        updated_requirement = (
            "Updated requirement: catering "
            f"for {new_quantity} people."
        )

        answers["requirements"] = (
            previous_requirements
            + "\n\n"
            + updated_requirement
        ).strip()

    # -----------------------------------------------------
    # OWNER
    # -----------------------------------------------------

    owner = owner_for_job(job, context)

    if owner is None:
        await update.message.reply_text(
            "The business configuration is unavailable."
        )

        return ConversationHandler.END

    # Professional rewrite of messy / long revision text
    try:
        answers = await normalize_client_answers(
            answers,
            owner=owner,
        )
    except Exception as error:
        print("Revision normalization failed:", error)

    save_job_answers(
        job_id,
        answers,
    )

    # -----------------------------------------------------
    # REPRICE (AI first, rules fallback — same job path)
    # -----------------------------------------------------

    ai_estimate = None
    try:
        ai_estimate = await estimate_price_with_ai(
            owner,
            answers,
        )
    except Exception as error:
        print("AI reprice failed:", error)

    if ai_estimate and ai_estimate.get("price", 0) > 0:
        price = float(ai_estimate["price"])
        analysis = {
            "complexity": ai_estimate.get(
                "complexity",
                "MEDIUM",
            ),
            "cushion_applied": "ai_estimate",
            "internal_analysis": ai_estimate.get(
                "reasoning",
                "AI-assisted revised price within owner bounds.",
            ),
            "in_scope": ai_estimate.get("in_scope", []),
            "out_of_scope": ai_estimate.get(
                "out_of_scope",
                [],
            ),
            "pricing_source": "ai",
        }
    else:
        price, analysis = calculate_business_price(
            owner,
            answers,
        )
        analysis["pricing_source"] = "rules"

    # Revisions must not ratchet the price up every time.
    # Keep previous quote unless the client clearly added scope.
    try:
        prev_price = float(job["quoted_price"] or 0)
    except Exception:
        prev_price = 0.0
    req_l = (request or "").lower()
    scope_up = any(
        w in req_l
        for w in (
            "more", "extra", "add", "also", "another", "plus",
            "larger", "bigger", "hours", "urgent", "asap",
            "today", "additional", "upgrade",
        )
    )
    if prev_price > 0:
        min_p = safe_float(row_get(owner, "min_price", 0), 0)
        max_p = safe_float(row_get(owner, "max_price", prev_price), prev_price)
        if not scope_up:
            # Cosmetic / clarification: keep prior price
            price = prev_price
            analysis = analysis or {}
            analysis["internal_analysis"] = (
                (analysis.get("internal_analysis") or "")
                + " Price held after revision (no clear scope increase)."
            ).strip()
        else:
            # Allow modest increase only, still inside band
            cap = min(max_p, prev_price * 1.15)
            price = min(max(price, prev_price), cap)
            price = max(min_p, min(max_p, price))

    save_job_analysis(
        job_id,
        complexity=analysis.get("complexity", "MEDIUM"),
        cushion_applied=analysis.get(
            "cushion_applied",
            "",
        ),
        internal_analysis=analysis.get(
            "internal_analysis",
            "",
        ),
    )

    if price <= 0:
        min_price = safe_float(row_get(owner, "min_price", 150), 150)
        max_price = safe_float(row_get(owner, "max_price", 400), 400)
        if min_price <= 0:
            min_price = 150.0
        if max_price < min_price:
            max_price = min_price
        price = round(min_price, 2)
        analysis = analysis or {}
        analysis["pricing_source"] = "min_max_fallback"
        analysis.setdefault("complexity", "MEDIUM")
        analysis.setdefault(
            "internal_analysis",
            "Revised quote near the low end of the studio price range.",
        )

    # -----------------------------------------------------
    # REGENERATE PROPOSAL
    # -----------------------------------------------------

    try:
        proposal = await generate_proposal(
            owner,
            answers,
            price,
            analysis=analysis,
        )
    except Exception:
        proposal = template_proposal(
            owner,
            answers,
            price,
        )

    save_proposal(
        job_id,
        price,
        proposal,
    )

    # -----------------------------------------------------
    # PROGRESS
    # -----------------------------------------------------

    progress_message = await update.message.reply_text(
        "Updating your proposal...\n\n"
        "░░░░░░░░░░░░░░░░░░░░ 0%"
    )

    try:
        await proposal_progress(
            progress_message
        )

        client_name = row_get(
            job,
            "client_name",
            update.effective_user.first_name or "Client",
        )

        pdf = build_proposal_pdf(
            owner=owner,
            job_id=job_id,
            client_name=client_name,
            answers=answers,
            proposal=proposal,
            price=price,
            change_request=request,
        )

        await update.message.reply_document(
            document=pdf,
            filename=f"Proposal_SB-{job_id:04d}_Revised.pdf",
            caption=(
                f"📄 Revised Proposal SB-{job_id:04d}\n\n"
                "Your requested changes have been applied."
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "💳 Payment",
                            callback_data=f"pay_{job_id}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "📄 View Proposal",
                            callback_data=f"proposal_{job_id}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "✏️ Request Changes",
                            callback_data=f"edit_{job_id}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "🏠 Home",
                            callback_data="client_home",
                        )
                    ],
                ]
            ),
        )

        try:
            await progress_message.edit_text(
                "Proposal updated successfully.\n\n"
                "████████████████████ 100%\n\n"
                "📄 Revised PDF generated."
            )
        except Exception:
            pass

    except Exception as error:
        try:
            await progress_message.edit_text(
                "Proposal update failed.\n\n"
                f"Error: {error}"
            )
        except Exception:
            pass

        await update.message.reply_text(
            "The proposal was updated, but the PDF "
            "could not be generated.\n\n"
            f"Error: {error}"
        )

    return ConversationHandler.END


# =========================================================
# CANCEL
# =========================================================

async def cancel_intake(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data.clear()

    await update.message.reply_text(
        "Project intake cancelled."
    )

    return ConversationHandler.END


# =========================================================
# MY ORDERS
# =========================================================

async def my_orders(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    await query.answer()

    user_id = update.effective_user.id

    business_id = context.user_data.get("owner_id")
    orders = get_client_orders(
        user_id,
        business_id=business_id if business_id else None,
    )

    if not orders:
        await query.edit_message_text(
            "You don't have any projects yet.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "➕ New Project",
                            callback_data="new_order",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "🏠 Home",
                            callback_data="client_home",
                        )
                    ],
                ]
            ),
        )

        return

    buttons = []

    for order in orders[:20]:
        buttons.append(
            [
                InlineKeyboardButton(
                    f"#{order['id']} — {order['status']}",
                    callback_data=f"order_{order['id']}",
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                "🏠 Home",
                callback_data="client_home",
            )
        ]
    )

    await query.edit_message_text(
        "Your projects:",
        reply_markup=InlineKeyboardMarkup(
            buttons
        ),
    )


# =========================================================
# ORDER DETAIL
# =========================================================

async def order_detail(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    await query.answer()

    match = re.match(
        r"^order_(\d+)$",
        query.data or "",
    )

    if not match:
        return

    order_id = int(match.group(1))
    user_id = update.effective_user.id

    job = get_client_job(
        user_id,
        order_id,
    )

    if not job:
        await query.edit_message_text(
            "Project not found."
        )

        return

    buttons = []

    if row_get(
        job,
        "proposal_text",
    ):
        buttons.append(
            [
                InlineKeyboardButton(
                    "📄 Proposal",
                    callback_data=f"proposal_{order_id}",
                )
            ]
        )

    quoted_price = row_get(
        job,
        "quoted_price",
    )

    status = row_get(
        job,
        "status",
        "",
    )

    if (
        quoted_price
        and status == "QUOTED"
    ):
        buttons.append(
            [
                InlineKeyboardButton(
                    "💳 Payment",
                    callback_data=f"pay_{order_id}",
                )
            ]
        )

    if status not in (
        "CLOSED",
        "DELIVERED",
    ):
        buttons.append(
            [
                InlineKeyboardButton(
                    "✏️ Request Changes",
                    callback_data=f"edit_{order_id}",
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                "📦 My Orders",
                callback_data="my_orders",
            )
        ]
    )

    buttons.append(
        [
            InlineKeyboardButton(
                "🏠 Home",
                callback_data="client_home",
            )
        ]
    )

    text = (
        f"Project #{order_id}\n\n"
        f"Status: {status}\n"
    )

    if quoted_price:
        currency = row_get(
            job,
            "currency",
            "USD",
        )

        text += (
            f"Quote: {currency} "
            f"{float(quoted_price):,.2f}\n"
        )

    complexity = row_get(
        job,
        "complexity",
    )

    if complexity:
        text += (
            f"Complexity: {complexity}\n"
        )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            buttons
        ),
    )


# =========================================================
# VIEW PROPOSAL
# =========================================================

async def view_proposal(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    await query.answer()

    match = re.match(
        r"^proposal_(\d+)$",
        query.data or "",
    )

    if not match:
        return

    job_id = int(match.group(1))
    user_id = update.effective_user.id

    job = get_client_job(
        user_id,
        job_id,
    )

    if not job:
        await query.edit_message_text(
            "Proposal not found."
        )

        return

    proposal = row_get(
        job,
        "proposal_text",
        "",
    )

    if not proposal:
        await query.edit_message_text(
            "A proposal has not been generated yet."
        )

        return

    quoted_price = safe_float(
        row_get(
            job,
            "quoted_price",
            0,
        )
    )

    answers = get_job_answers(job_id)

    if not isinstance(answers, dict):
        answers = dict(answers or {})

    owner = owner_for_job(job, context)

    if owner:
        client_name = row_get(
            job,
            "client_name",
            "Client",
        )

        try:
            pdf = build_proposal_pdf(
                owner=owner,
                job_id=job_id,
                client_name=client_name,
                answers=answers,
                proposal=proposal,
                price=quoted_price,
                change_request=answers.get(
                    "client_revision_request",
                    "",
                ),
            )

            await query.message.reply_document(
                document=pdf,
                filename=f"Proposal_SB-{job_id:04d}.pdf",
                caption=f"📄 Proposal SB-{job_id:04d}",
            )

        except Exception as error:
            await query.message.reply_text(
                "The proposal exists, but the PDF "
                "could not be generated.\n\n"
                f"Error: {error}"
            )

    buttons = [
        [
            InlineKeyboardButton(
                "💳 Payment",
                callback_data=f"pay_{job_id}",
            )
        ],
        [
            InlineKeyboardButton(
                "✏️ Request Changes",
                callback_data=f"edit_{job_id}",
            )
        ],
        [
            InlineKeyboardButton(
                "🏠 Home",
                callback_data="client_home",
            )
        ],
    ]

    try:
        await query.edit_message_text(
            proposal,
            reply_markup=InlineKeyboardMarkup(
                buttons
            ),
        )

    except Exception as error:
        if "There is no text in the message to edit" in str(error):
            await query.message.reply_text(
                proposal,
                reply_markup=InlineKeyboardMarkup(
                    buttons
                ),
            )
        else:
            raise


# =========================================================
# PAYMENT PAGE
# =========================================================

async def _send_callback_text(
    query,
    text,
    reply_markup=None,
    parse_mode=None,
    prefer_new_message=False,
):
    """
    Buttons are often on a PDF document message.
    Prefer a new reply for payment flows so clicks always
    produce visible UI. Fallbacks: edit text, edit caption.
    """

    kwargs = {}
    if reply_markup is not None:
        kwargs["reply_markup"] = reply_markup
    if parse_mode is not None:
        kwargs["parse_mode"] = parse_mode

    if prefer_new_message:
        try:
            await query.message.reply_text(text, **kwargs)
            return
        except Exception:
            pass

    try:
        await query.edit_message_text(text, **kwargs)
        return
    except Exception:
        pass

    try:
        await query.edit_message_caption(caption=text, **kwargs)
        return
    except Exception:
        pass

    await query.message.reply_text(text, **kwargs)


async def payment_page(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    await query.answer("Opening payment…")

    match = re.match(
        r"^pay_(\d+)$",
        query.data or "",
    )

    if not match:
        return

    job_id = int(match.group(1))
    user_id = update.effective_user.id

    job = get_client_job(
        user_id,
        job_id,
    )

    if not job:
        await _send_callback_text(
            query,
            "Project not found.",
            prefer_new_message=True,
        )
        return

    owner = owner_for_job(job, context)

    if not owner:
        await _send_callback_text(
            query,
            "Payment information is unavailable.",
            prefer_new_message=True,
        )
        return

    address = clean_text(
        row_get(
            owner,
            "usdc_address",
        )
    )

    price = safe_float(
        row_get(
            job,
            "quoted_price",
            0,
        )
    )

    from config import PAYMENT_NETWORK as DEFAULT_PAYMENT_NETWORK

    network = clean_text(
        row_get(
            owner,
            "payment_network",
            DEFAULT_PAYMENT_NETWORK,
        )
    ) or DEFAULT_PAYMENT_NETWORK

    token = clean_text(
        row_get(
            owner,
            "payment_token",
            "USDC",
        )
    ) or "USDC"

    try:
        set_payment_details(
            job_id,
            payment_address=address,
            payment_network=network,
            payment_token=token,
            payment_amount=price,
        )
    except Exception:
        pass

    # HTML <code> makes the wallet one-tap copy on Telegram.
    # Escape user-controlled strings; leave the address in <code>.
    def _html(value: str) -> str:
        return (
            str(value)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    text = (
        f"💳 Payment — Project #{job_id}\n\n"
        f"Amount: <b>${price:,.2f} USD</b>\n"
        f"Network: {_html(network)}\n"
        f"Token: {_html(token)}\n\n"
    )

    if address:
        text += (
            "Send the exact amount to this wallet:\n"
            "(tap the address to copy)\n\n"
            f"<code>{_html(address)}</code>\n\n"
            "Only send the selected token on the specified network.\n\n"
        )
    else:
        text += (
            "The studio has not configured a payment wallet yet.\n\n"
        )

    text += (
        "After sending payment, press \"I've Paid\" "
        "and paste the transaction hash when asked."
    )

    await _send_callback_text(
        query,
        text,
        prefer_new_message=True,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ I've Paid",
                        callback_data=f"paid_{job_id}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🏠 Home",
                        callback_data="client_home",
                    )
                ],
            ]
        ),
    )


# =========================================================
# PAYMENT CONFIRMATION
# =========================================================

async def confirm_paid(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    await query.answer()

    match = re.match(
        r"^paid_(\d+)$",
        query.data or "",
    )

    if not match:
        return

    job_id = int(match.group(1))
    user_id = update.effective_user.id

    job = get_client_job(
        user_id,
        job_id,
    )

    if not job:
        await _send_callback_text(
            query,
            "Project not found.",
            prefer_new_message=True,
        )
        return

    context.user_data["payment_job_id"] = job_id

    await _send_callback_text(
        query,
        (
            f"Payment for Project #{job_id}\n\n"
            "Please send the transaction hash (TX hash) "
            "of the USDC payment.\n\n"
            "We will use it to verify the transaction "
            "on the network."
        ),
        prefer_new_message=True,
    )


# =========================================================
# PAYMENT TEXT FALLBACK
# =========================================================

async def handle_paid(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    text = clean_text(
        update.message.text
    )

    job_id = context.user_data.get(
        "payment_job_id"
    )

    if job_id:
        user_id = update.effective_user.id

        job = get_client_job(
            user_id,
            job_id,
        )

        if not job:
            await update.message.reply_text(
                "I couldn't find that project."
            )

            return

        tx_hash = text.strip()

        # Basic format check for a 0x + 64 hex chars transaction hash
        if not re.match(r"^0x[a-fA-F0-9]{64}$", tx_hash):
            await update.message.reply_text(
                "That doesn't look like a valid "
                "transaction hash.\n\n"
                "Please send the complete TX hash "
                "(0x followed by 64 hexadecimal characters)."
            )

            return

        # -------------------------------------------------
        # IMPORTANT:
        # Record the submitted transaction hash and mark
        # payment as pending / verifying.
        # Actual on-chain verification is intentionally
        # left for the next step (do not auto-confirm).
        # -------------------------------------------------

        # Capture before we write the hash, otherwise
        # updated_at becomes "now" and a valid payment
        # can look like it came from the past.
        min_timestamp = parse_iso_timestamp(
            row_get(job, "updated_at")
        ) or parse_iso_timestamp(
            row_get(job, "created_at")
        )

        current_payment_status = clean_text(
            row_get(job, "payment_status")
        ).upper()
        current_status = clean_text(
            row_get(job, "status")
        ).upper()

        if (
            current_payment_status == "CONFIRMED"
            or current_status == "PAID"
        ):
            await update.message.reply_text(
                f"Project #{job_id} is already paid.\n\n"
                "This transaction hash cannot be used again."
            )
            return

        other = find_other_job_using_tx_hash(
            tx_hash,
            exclude_job_id=job_id,
        )

        if other:
            await update.message.reply_text(
                "This transaction hash was already submitted "
                "and confirmed for another project.\n\n"
                "A confirmed payment cannot be reused."
            )
            return

        try:
            set_payment_tx_hash(job_id, tx_hash)
            mark_payment_pending(job_id)
            set_job_status(
                job_id,
                "PAYMENT_PENDING",
            )
        except Exception as e:
            await update.message.reply_text(
                "I received the transaction hash but "
                "could not record it. Please try again "
                "or contact the studio.\n\n"
                f"Error: {e}"
            )
            return

        details = get_payment_details(job_id) or {}
        recipient = clean_text(
            details.get("payment_address")
        )
        expected_amount = safe_float(
            details.get("payment_amount")
            or details.get("quoted_price")
            or 0
        )

        if not recipient:
            reject_payment(
                job_id,
                "Owner payment wallet is not configured.",
            )
            context.user_data.pop("payment_job_id", None)
            await update.message.reply_text(
                "Payment cannot be verified because the "
                "studio wallet is not configured."
            )
            return

        await update.message.reply_text(
            f"Checking transaction for Project #{job_id}...\n\n"
            f"{tx_hash}"
        )

        result = {}

        # Short retry window for unmined / unconfirmed txs.
        # Does not wait long enough to be abused as a stall.
        for attempt in range(3):
            result = verify_usdc_payment(
                tx_hash=tx_hash,
                recipient_address=recipient,
                expected_amount=expected_amount,
                min_timestamp=min_timestamp,
            )

            status = result.get("status")

            if status in ("PENDING", "CONFIRMING"):
                await asyncio.sleep(8)
                continue

            break

        context.user_data.pop("payment_job_id", None)
        context.user_data.pop("payment_tx_hash", None)

        if result.get("confirmed"):
            confirm_payment(
                job_id,
                tx_hash,
                expected_amount,
                payment_network=details.get(
                    "payment_network",
                    "Base",
                ),
                payment_token=details.get(
                    "payment_token",
                    "USDC",
                ),
            )

            client_name = clean_text(
                row_get(job, "client_name", "Client")
            ) or "Client"
            paid_amount = result.get("actual_amount") or expected_amount
            paid_confirmations = result.get("confirmations") or ""

            await update.message.reply_text(
                f"Payment confirmed for Project #{job_id}.\n\n"
                f"Amount: {paid_amount} USDC\n"
                f"Network: Base\n"
                f"Confirmations: {paid_confirmations}\n\n"
                f"TX hash:\n{tx_hash}"
            )

            receipt_pdf = None
            invoice_pdf = None

            try:
                owner = owner_for_job(job, context)
                studio_name = clean_text(
                    row_get(owner, "name", "Sovereign Studio") if owner else "Sovereign Studio"
                ) or "Sovereign Studio"

                try:
                    _oid = int(row_get(owner, "telegram_id", 0) or 0) if owner else 0
                except Exception:
                    _oid = 0
                signature = get_owner_signature(_oid) or {} if _oid else {}
                signature_name = clean_text(
                    signature.get("signature_name")
                ) or studio_name
                signature_title = clean_text(
                    signature.get("signature_title")
                ) or "Authorized representative"

                answers = get_job_answers(job_id)
                if not isinstance(answers, dict):
                    answers = dict(answers or {})
                project_title = clean_text(
                    answers.get("project", "Professional Services")
                ) or "Professional Services"
                if len(project_title) > 80:
                    project_title = project_title[:77] + "..."

                network = (details.get("payment_network") or "Base").replace("Sepolia", "").replace("sepolia", "").strip() or "Base"
                token = details.get("payment_token", "USDC")
                block_number = result.get("block_number") or ""
                paid_recipient = result.get("recipient") or recipient
                paid_sender = result.get("sender") or ""

                os.makedirs("data/receipts", exist_ok=True)
                os.makedirs("data/invoices", exist_ok=True)

                receipt_pdf = create_payment_receipt_pdf(
                    studio_name=studio_name,
                    client_name=client_name,
                    job_id=job_id,
                    amount=paid_amount,
                    currency="USDC",
                    network=network,
                    token=token,
                    tx_hash=tx_hash,
                    block_number=block_number,
                    confirmations=paid_confirmations,
                    recipient=paid_recipient,
                    sender=paid_sender,
                )

                receipt_path = f"data/receipts/RCPT-SB-{int(job_id):04d}.pdf"
                with open(receipt_path, "wb") as receipt_file:
                    receipt_file.write(receipt_pdf.getvalue())
                receipt_pdf.seek(0)
                save_receipt_file(job_id, receipt_path)

                await update.message.reply_document(
                    document=receipt_pdf,
                    filename=f"Receipt_SB-{int(job_id):04d}.pdf",
                    caption=(
                        f"📄 Payment receipt RCPT-SB-{int(job_id):04d}\n\n"
                        "Your payment has been verified on-chain."
                    ),
                )

                invoice_pdf = create_invoice_pdf(
                    studio_name=studio_name,
                    client_name=client_name,
                    job_id=job_id,
                    amount=paid_amount,
                    currency="USDC",
                    network=network,
                    token=token,
                    tx_hash=tx_hash,
                    block_number=block_number,
                    confirmations=paid_confirmations,
                    recipient=paid_recipient,
                    sender=paid_sender,
                    project_title=project_title,
                    signature_name=signature_name,
                    signature_title=signature_title,
                )

                invoice_path = f"data/invoices/INV-SB-{int(job_id):04d}.pdf"
                with open(invoice_path, "wb") as invoice_file:
                    invoice_file.write(invoice_pdf.getvalue())
                invoice_pdf.seek(0)
                save_invoice_file(job_id, invoice_path)

                await update.message.reply_document(
                    document=invoice_pdf,
                    filename=f"Invoice_SB-{int(job_id):04d}.pdf",
                    caption=(
                        f"🧾 Official invoice INV-SB-{int(job_id):04d}\n\n"
                        "Thank you for your payment."
                    ),
                )
            except Exception as error:
                receipt_pdf = None
                invoice_pdf = None
                await update.message.reply_text(
                    "Payment is confirmed, but the financial "
                    "documents could not be generated.\n\n"
                    f"Error: {error}"
                )

            client_username = ""
            try:
                client_username = row_get(job, "client_username", "") or ""
            except Exception:
                pass
            await notify_owner_payment_confirmed(
                context,
                job_id,
                client_name,
                tx_hash,
                paid_amount,
                paid_confirmations,
                receipt_pdf=receipt_pdf,
                invoice_pdf=invoice_pdf,
                client_username=client_username,
            )

            return

        reason = clean_text(
            result.get("reason")
        ) or "Payment could not be verified."

        status = result.get("status")

        if status in ("PENDING", "CONFIRMING"):
            await update.message.reply_text(
                "The transaction was found, but it does "
                "not have enough confirmations yet.\n\n"
                "Wait about a minute, then send the same "
                "TX hash again."
            )
            return

        reject_payment(job_id, reason)

        await update.message.reply_text(
            "Payment was not accepted.\n\n"
            f"{reason}\n\n"
            "Send a fresh USDC transfer on Base "
            "for this project, then submit the new TX hash."
        )

        return

    if text.upper() != "PAID":
        return

    user_id = update.effective_user.id

    job = get_latest_order(user_id)

    if not job:
        await update.message.reply_text(
            "I couldn't find an active project "
            "to attach that payment confirmation to."
        )

        return

    job_id = row_get(
        job,
        "id",
    )

    context.user_data["payment_job_id"] = job_id

    await update.message.reply_text(
        f"Payment confirmation for Project #{job_id}.\n\n"
        "Please send the transaction hash (TX hash) "
        "of the payment so it can be verified."
    )


# =========================================================
# SERVICES
# =========================================================

async def services_page(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    await query.answer()

    from config import OWNER_TELEGRAM_ID
    _oid = context.user_data.get("owner_id") or OWNER_TELEGRAM_ID
    owner = get_owner(_oid)

    if not owner:
        await query.edit_message_text(
            "Services are currently unavailable."
        )

        return

    services = clean_text(
        row_get(
            owner,
            "services_text",
        )
    )

    if not services:
        services = (
            "The studio is currently accepting "
            "custom project requests."
        )

    owner_name = clean_text(
        row_get(
            owner,
            "name",
            "Sovereign Studio",
        )
    )

    text = (
        f"{owner_name}\n\n"
        "🛠 Services:\n\n"
        f"{services}\n\n"
        "If you're unsure what service you need, "
        "just describe your problem or desired outcome "
        "and we'll help determine the appropriate scope."
    )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "➕ Start Project",
                        callback_data="new_order",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🏠 Home",
                        callback_data="client_home",
                    )
                ],
            ]
        ),
    )


# =========================================================
# CONTACT
# =========================================================

async def contact_studio(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    await query.answer()

    from config import OWNER_TELEGRAM_ID
    _oid = context.user_data.get("owner_id") or OWNER_TELEGRAM_ID
    owner = get_owner(_oid)

    if not owner:
        await query.edit_message_text(
            "Contact information is unavailable."
        )

        return

    owner_name = clean_text(
        row_get(
            owner,
            "name",
            "Sovereign Studio",
        )
    )

    text = (
        f"💬 Contact {owner_name}\n\n"
        "If you need help with a project, "
        "start a new project request and describe "
        "what you need.\n\n"
        "The studio will review the request and "
        "provide the appropriate next step."
    )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "➕ New Project",
                        callback_data="new_order",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🏠 Home",
                        callback_data="client_home",
                    )
                ],
            ]
        ),
    )


async def client_guide(update, context):
    query = update.callback_query
    if query:
        await query.answer()
        message = query.message
    else:
        message = update.message
    lines = [
        "How to order",
        "",
        "1. Open the studio invite link (/start their-slug) so you see their business name.",
        "2. Tap New order and answer a few questions.",
        "3. Review the proposal PDF and quote.",
        "4. Pay USDC on Base to the wallet shown.",
        "5. Paste the transaction hash from Basescan.",
        "6. Get receipt and invoice after confirmation.",
        "",
        "If you only pressed Start and no company name appears, you are not on a studio invite yet — ask them for their link.",
        "",
        "Want to run your own studio? Send /setup.",
    ]
    await message.reply_text(chr(10).join(lines))


async def owner_hint_setup(update, context):
    query = update.callback_query
    if query:
        await query.answer()
        message = query.message
    else:
        message = update.message
    lines = [
        "To create your business on Sovereign:",
        "",
        "Send /setup and follow the steps (name, niche, services, prices, email).",
        "",
        "Then open Payments and add your Base USDC wallet.",
        "Share your invite slug with clients so they see your brand.",
    ]
    await message.reply_text(chr(10).join(lines))
