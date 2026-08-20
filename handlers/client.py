import json
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

from db import (
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
)

from ai import (
    generate_proposal,
    template_proposal,
)

from pricing import calculate_price
from pdf_generator import create_proposal_pdf


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
        "What do you need us to do for you?\n\n"
        "Please describe the project or service in your own words.",
    ),
    (
        "requirements",
        "What are the main things you want included?",
    ),
    (
        "quantity",
        "How much work is involved?\n\n"
        "For example: number of items, locations, people, "
        "hours, pages, products, deliverables, or anything "
        "else that helps us understand the size of the job.",
    ),
    (
        "deadline",
        "When would you like the work completed?",
    ),
    (
        "additional",
        "Is there anything else we should know before preparing "
        "your quote?",
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
    rules = get_rules(owner)

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

    if not result.get(
        "success",
        False,
    ):
        return (
            0,
            {
                **analysis,
                "pricing_error": result.get(
                    "reason",
                    "Unable to calculate price.",
                ),
                "pricing_result": result,
            },
        )

    price = result.get("price")

    if price is None:
        return (
            0,
            {
                **analysis,
                "pricing_error": (
                    "Pricing engine returned "
                    "no price."
                ),
                "pricing_result": result,
            },
        )

    return (
        round(float(price), 2),
        {
            **analysis,
            "pricing_result": result,
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

    keyboard = [
        [
            InlineKeyboardButton(
                "➕ New Project",
                callback_data="new_order",
            )
        ],
        [
            InlineKeyboardButton(
                "📦 My Orders",
                callback_data="my_orders",
            )
        ],
        [
            InlineKeyboardButton(
                "🛠 Services",
                callback_data="services",
            )
        ],
        [
            InlineKeyboardButton(
                "💬 Contact Studio",
                callback_data="contact_studio",
            )
        ],
    ]

    text = (
        "Welcome to Sovereign Studio.\n\n"
        "Tell us what you need and we'll help "
        "turn it into a clear project scope and quote."
    )

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

    owner = get_owner(
        OWNER_TELEGRAM_ID
    )

    if owner is None:
        await query.edit_message_text(
            "The business is not fully configured yet."
        )

        return ConversationHandler.END

    context.user_data.clear()

    context.user_data["owner_id"] = row_get(
        owner,
        "telegram_id",
        OWNER_TELEGRAM_ID,
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

    await update.message.reply_text(
        GENERIC_QUESTIONS[0][1]
    )

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

    if question_index >= len(GENERIC_QUESTIONS):
        return ConversationHandler.END

    key = GENERIC_QUESTIONS[
        question_index
    ][0]

    answers[key] = answer

    question_index += 1

    context.user_data["question_index"] = question_index

    if question_index < len(GENERIC_QUESTIONS):
        await update.message.reply_text(
            GENERIC_QUESTIONS[
                question_index
            ][1]
        )

        return QUESTION_STATES[
            question_index
        ]

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
    )

    save_job_answers(
        job_id,
        answers,
    )

    price, analysis = calculate_business_price(
        owner,
        answers,
    )

    save_job_analysis(
        job_id,
        complexity=analysis["complexity"],
        cushion_applied=analysis["cushion_applied"],
        internal_analysis=analysis["internal_analysis"],
    )

    if price <= 0:
        await update.message.reply_text(
            "We received your project request.\n\n"
            "The studio needs to review the pricing "
            "configuration before a quote can be issued."
        )

        return

    # -----------------------------------------------------
    # GENERATE PROPOSAL
    # -----------------------------------------------------

    try:
        proposal = await generate_proposal(
            owner,
            answers,
            price,
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
        await query.edit_message_text(
            "Invalid project."
        )

        return ConversationHandler.END

    job_id = int(match.group(1))
    user_id = update.effective_user.id

    if not client_owns_job(
        user_id,
        job_id,
    ):
        await query.edit_message_text(
            "You don't have access to this project."
        )

        return ConversationHandler.END

    context.user_data.clear()
    context.user_data["edit_job_id"] = job_id

    await query.edit_message_text(
        "Tell us what you'd like to change "
        "about the project or proposal."
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

    save_job_answers(
        job_id,
        answers,
    )

    # -----------------------------------------------------
    # OWNER
    # -----------------------------------------------------

    from config import OWNER_TELEGRAM_ID

    owner = get_owner(
        OWNER_TELEGRAM_ID
    )

    if owner is None:
        await update.message.reply_text(
            "The business configuration is unavailable."
        )

        return ConversationHandler.END

    # -----------------------------------------------------
    # REPRICE
    # -----------------------------------------------------

    price, analysis = calculate_business_price(
        owner,
        answers,
    )

    save_job_analysis(
        job_id,
        complexity=analysis["complexity"],
        cushion_applied=analysis["cushion_applied"],
        internal_analysis=analysis["internal_analysis"],
    )

    if price <= 0:
        await update.message.reply_text(
            "Your changes were saved, but the studio "
            "needs to review the pricing configuration "
            "before issuing a revised quote."
        )

        return ConversationHandler.END

    # -----------------------------------------------------
    # REGENERATE PROPOSAL
    # -----------------------------------------------------

    try:
        proposal = await generate_proposal(
            owner,
            answers,
            price,
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
                            "📄 View Proposal",
                            callback_data=f"proposal_{job_id}",
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

    orders = get_client_orders(user_id)

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

    from config import OWNER_TELEGRAM_ID

    owner = get_owner(
        OWNER_TELEGRAM_ID
    )

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

async def payment_page(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    await query.answer()

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
        await query.edit_message_text(
            "Project not found."
        )

        return

    from config import OWNER_TELEGRAM_ID

    owner = get_owner(
        OWNER_TELEGRAM_ID
    )

    if not owner:
        await query.edit_message_text(
            "Payment information is unavailable."
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

    network = clean_text(
        row_get(
            owner,
            "payment_network",
            "Base",
        )
    ) or "Base"

    token = clean_text(
        row_get(
            owner,
            "payment_token",
            "USDC",
        )
    ) or "USDC"

    text = (
        f"💳 Payment — Project #{job_id}\n\n"
        f"Amount: ${price:,.2f} USD\n"
        f"Network: {network}\n"
        f"Token: {token}\n\n"
    )

    if address:
        text += (
            "Send the exact amount to the wallet below:\n\n"
            f"`{address}`\n\n"
            "⚠️ Only send the selected token on the "
            "specified network.\n\n"
        )
    else:
        text += (
            "⚠️ The studio has not configured a payment "
            "wallet yet.\n\n"
        )

    text += (
        "After sending the payment, press "
        "\"I've Paid\" and provide the transaction hash "
        "when requested."
    )

    await query.edit_message_text(
        text,
        parse_mode="Markdown",
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
        await query.edit_message_text(
            "Project not found."
        )

        return

    context.user_data["payment_job_id"] = job_id

    await query.edit_message_text(
        f"Payment for Project #{job_id}\n\n"
        "Please send the transaction hash (TX hash) "
        "of the USDC payment.\n\n"
        "We will use it to verify the transaction "
        "on the network."
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

        tx_hash = text

        if len(tx_hash) < 20:
            await update.message.reply_text(
                "That doesn't look like a valid "
                "transaction hash.\n\n"
                "Please send the complete TX hash."
            )

            return

        # -------------------------------------------------
        # IMPORTANT:
        # This records the submitted transaction hash.
        # Actual blockchain verification is handled by
        # the payment verification layer.
        # -------------------------------------------------

        try:
            set_job_status(
                job_id,
                "PAYMENT_PENDING",
            )
        except Exception:
            pass

        context.user_data["payment_tx_hash"] = tx_hash

        await update.message.reply_text(
            f"Transaction received for Project #{job_id}.\n\n"
            f"TX hash:\n{tx_hash}\n\n"
            "⏳ Payment verification is now pending.\n\n"
            "The transaction will be checked on the "
            "configured network before the project is "
            "marked as paid."
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

    owner = get_owner(
        OWNER_TELEGRAM_ID
    )

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

    owner = get_owner(
        OWNER_TELEGRAM_ID
    )

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