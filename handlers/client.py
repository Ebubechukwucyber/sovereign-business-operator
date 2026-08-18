import json
import asyncio

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ConversationHandler,
    ContextTypes,
)

from config import OWNER_TELEGRAM_ID

from db import (
    create_job,
    get_client_jobs,
    get_client_job,
    get_job,
    get_owner,
    save_job_answers,
    save_proposal,
    set_job_status,
)

from agent import (
    calculate_price,
    generate_proposal,
    template_proposal,
)

from pdf_generator import create_proposal_pdf


# =========================================================
# STATES
# =========================================================

NAME = 200
QUESTION_1 = 201
QUESTION_2 = 202
QUESTION_3 = 203
QUESTION_4 = 204
QUESTION_5 = 205

EDIT_REQUEST = 210


QUESTIONS = [
    (
        "page_for",
        "What is the page for?\n\n"
        "For example: product, gym, event, personal brand."
    ),
    (
        "sections",
        "How many pages or major sections do you need?"
    ),
    (
        "deadline",
        "What's your deadline?"
    ),
    (
        "brand_copy",
        "Do you already have your copy and brand assets?"
    ),
    (
        "budget",
        "What's your budget range?"
    ),
]


# =========================================================
# HELPERS
# =========================================================

def is_owner(update):
    return (
        update.effective_user.id
        == OWNER_TELEGRAM_ID
    )


def load_answers(job):
    try:
        return json.loads(
            job["answers"]
        )
    except (
        TypeError,
        json.JSONDecodeError,
    ):
        return {}


def is_paid_message(text):
    return text.strip().lower() in {
        "paid",
        "i paid",
        "i've paid",
        "ive paid",
    }


def main_menu_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🆕 New Order",
                    callback_data="new_order",
                ),
                InlineKeyboardButton(
                    "📦 My Orders",
                    callback_data="my_orders",
                ),
            ],
            [
                InlineKeyboardButton(
                    "ℹ️ Services",
                    callback_data="services",
                ),
                InlineKeyboardButton(
                    "💬 Contact Studio",
                    callback_data="contact_studio",
                ),
            ],
        ]
    )


def order_keyboard(job):
    buttons = []

    if job["status"] in {
        "QUOTED",
        "WAITING_PAYMENT",
    }:
        buttons.append(
            [
                InlineKeyboardButton(
                    "✅ Accept & Pay",
                    callback_data=f"pay_{job['id']}",
                ),
                InlineKeyboardButton(
                    "✏️ Make Changes",
                    callback_data=f"edit_{job['id']}",
                ),
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                "📄 View Proposal",
                callback_data=f"proposal_{job['id']}",
            )
        ]
    )

    buttons.append(
        [
            InlineKeyboardButton(
                "⬅️ My Orders",
                callback_data="my_orders",
            ),
            InlineKeyboardButton(
                "🏠 Home",
                callback_data="client_home",
            ),
        ]
    )

    return InlineKeyboardMarkup(buttons)


async def update_progress(
    message,
    text,
    percent,
):
    total_blocks = 10

    filled = round(
        percent / 10
    )

    empty = (
        total_blocks
        - filled
    )

    bar = (
        "█" * filled
        + "░" * empty
    )

    await message.edit_text(
        f"{text}\n\n"
        f"`{bar}` {percent}%",
        parse_mode="Markdown",
    )


# =========================================================
# CLIENT HOME
# =========================================================

async def client_home(update, context):

    query = update.callback_query

    if query:
        await query.answer()

        await query.message.edit_text(
            "👋 Welcome to Sovereign Studio.\n\n"
            "What would you like to do?",
            reply_markup=main_menu_keyboard(),
        )

    else:

        await update.message.reply_text(
            "👋 Welcome to Sovereign Studio.\n\n"
            "What would you like to do?",
            reply_markup=main_menu_keyboard(),
        )


async def start_client(update, context):

    if is_owner(update):
        return ConversationHandler.END

    context.user_data.clear()

    await client_home(
        update,
        context,
    )

    return ConversationHandler.END


# =========================================================
# NEW ORDER
# =========================================================

async def new_order_start(update, context):

    query = update.callback_query
    await query.answer()

    if is_owner(update):
        return ConversationHandler.END

    owner = get_owner(
        OWNER_TELEGRAM_ID
    )

    if owner is None or not owner["setup_complete"]:

        await query.message.reply_text(
            "The studio hasn't completed setup yet."
        )

        return ConversationHandler.END

    context.user_data.clear()

    await query.message.reply_text(
        "🆕 New Order\n\n"
        "Before we start, what's your name?"
    )

    return NAME


async def handle_client_name(update, context):

    client_name = update.message.text.strip()

    if not client_name:

        await update.message.reply_text(
            "Please enter your name."
        )

        return NAME

    if len(client_name) > 100:

        await update.message.reply_text(
            "Please enter a shorter name."
        )

        return NAME

    client_id = update.effective_user.id

    job_id = create_job(
        client_id,
        client_name,
    )

    context.user_data["job_id"] = job_id
    context.user_data["answers"] = {}
    context.user_data["client_name"] = client_name

    await update.message.reply_text(
        f"Nice to meet you, {client_name}.\n\n"
        "I'll ask a few quick questions so I can scope your project."
    )

    await update.message.reply_text(
        QUESTIONS[0][1]
    )

    return QUESTION_1


# =========================================================
# INTAKE
# =========================================================

async def handle_intake_answer(update, context):

    job_id = context.user_data.get(
        "job_id"
    )

    answers = context.user_data.get(
        "answers",
        {},
    )

    if job_id is None:

        await update.message.reply_text(
            "Your order session expired.\n\n"
            "Tap 🆕 New Order to begin again.",
            reply_markup=main_menu_keyboard(),
        )

        return ConversationHandler.END

    job = get_job(job_id)

    if not job:

        await update.message.reply_text(
            "I couldn't find this order."
        )

        return ConversationHandler.END

    if job["paused"]:

        await update.message.reply_text(
            "This order is currently paused by the studio."
        )

        return ConversationHandler.END

    text = update.message.text.strip()

    if not text:

        await update.message.reply_text(
            "Please send an answer so I can continue."
        )

        return QUESTION_1 + len(answers)

    question_index = len(answers)

    if question_index >= len(QUESTIONS):

        return ConversationHandler.END

    key, _ = QUESTIONS[question_index]

    answers[key] = text

    context.user_data["answers"] = answers

    save_job_answers(
        job_id,
        answers,
    )

    next_index = len(answers)

    if next_index < len(QUESTIONS):

        await update.message.reply_text(
            QUESTIONS[next_index][1]
        )

        return QUESTION_1 + next_index

    # =====================================================
    # GENERATE PROPOSAL
    # =====================================================

    progress = await update.message.reply_text(
        "⚙️ Preparing your proposal..."
    )

    await update_progress(
        progress,
        "🔎 Reviewing your project requirements...",
        20,
    )

    await asyncio.sleep(0.3)

    owner = get_owner(
        OWNER_TELEGRAM_ID
    )

    if owner is None or not owner["setup_complete"]:

        await progress.edit_text(
            "The studio hasn't completed setup yet."
        )

        return ConversationHandler.END

    await update_progress(
        progress,
        "💰 Calculating project scope and pricing...",
        40,
    )

    price = calculate_price(
        owner,
        answers,
    )

    await asyncio.sleep(0.3)

    await update_progress(
        progress,
        "✍️ Writing your proposal...",
        60,
    )

    try:

        proposal = await generate_proposal(
            owner,
            answers,
            price,
        )

    except Exception as error:

        print(
            f"LLM proposal failed: {error}"
        )

        proposal = template_proposal(
            owner,
            answers,
            price,
        )

    await update_progress(
        progress,
        "📋 Finalizing project details...",
        80,
    )

    save_proposal(
        job_id,
        price,
        proposal,
    )

    await update_progress(
        progress,
        "📄 Generating your professional proposal PDF...",
        90,
    )

    client_name = context.user_data.get(
        "client_name",
        "Client",
    )

    timeline = (
        f"{owner['default_days']} days"
    )

    pdf = None

    try:

        pdf = create_proposal_pdf(
            studio_name=owner["name"],
            client_name=client_name,
            proposal_text=proposal,
            price=price,
            timeline=timeline,
            proposal_id=f"SB-{job_id:04d}",
        )

    except Exception as error:

        print(
            f"PDF generation failed: {error}"
        )

    await update_progress(
        progress,
        "✅ Proposal ready!",
        100,
    )

    await asyncio.sleep(0.5)

    try:
        await progress.delete()
    except Exception:
        pass

    set_job_status(
        job_id,
        "WAITING_PAYMENT",
    )

    job = get_job(job_id)

    await update.message.reply_text(
        proposal,
        reply_markup=order_keyboard(job),
    )

    if pdf:

        await update.message.reply_document(
            document=pdf,
            filename=f"proposal_SB-{job_id:04d}.pdf",
            caption=(
                "📄 Your professional proposal is attached."
            ),
        )

    context.user_data.clear()

    return ConversationHandler.END


# =========================================================
# MY ORDERS
# =========================================================

async def my_orders(update, context):

    query = update.callback_query
    await query.answer()

    client_id = update.effective_user.id

    jobs = get_client_jobs(
        client_id
    )

    if not jobs:

        await query.message.edit_text(
            "📦 My Orders\n\n"
            "You don't have any orders yet.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🆕 New Order",
                            callback_data="new_order",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "⬅️ Home",
                            callback_data="client_home",
                        )
                    ],
                ]
            ),
        )

        return

    lines = [
        "📦 My Orders",
        "",
    ]

    buttons = []

    for job in jobs:

        price = job["quoted_price"]

        price_text = (
            f"${price:.0f}"
            if price
            else "Not quoted"
        )

        lines.append(
            f"#{job['id']} • "
            f"{job['status']} • "
            f"{price_text}"
        )

        buttons.append(
            [
                InlineKeyboardButton(
                    f"📦 Order #{job['id']}",
                    callback_data=f"order_{job['id']}",
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                "🆕 New Order",
                callback_data="new_order",
            )
        ]
    )

    buttons.append(
        [
            InlineKeyboardButton(
                "⬅️ Home",
                callback_data="client_home",
            )
        ]
    )

    await query.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# =========================================================
# ORDER DETAIL
# =========================================================

async def order_detail(update, context):

    query = update.callback_query
    await query.answer()

    try:
        job_id = int(
            query.data.split("_")[1]
        )
    except (ValueError, IndexError):
        return

    job = get_client_job(
        update.effective_user.id,
        job_id,
    )

    if not job:

        await query.message.reply_text(
            "Order not found."
        )

        return

    price = job["quoted_price"]

    price_text = (
        f"${price:.0f} USD"
        if price
        else "Not quoted"
    )

    text = (
        f"📦 Order #{job['id']}\n\n"
        f"Client: {job['client_name']}\n"
        f"Status: {job['status']}\n"
        f"Price: {price_text}\n"
        f"Created: {job['created_at']}"
    )

    await query.message.edit_text(
        text,
        reply_markup=order_keyboard(job),
    )


# =========================================================
# ACCEPT & PAY
# =========================================================

async def payment_page(update, context):

    query = update.callback_query
    await query.answer()

    try:
        job_id = int(
            query.data.split("_")[1]
        )
    except (ValueError, IndexError):
        return

    job = get_client_job(
        update.effective_user.id,
        job_id,
    )

    if not job:
        return

    if job["status"] not in {
        "QUOTED",
        "WAITING_PAYMENT",
    }:

        await query.message.reply_text(
            "This order isn't currently awaiting payment."
        )

        return

    owner = get_owner(
        OWNER_TELEGRAM_ID
    )

    payment_text = (
        f"💳 Payment for Order #{job_id}\n\n"
        f"Amount: ${job['quoted_price']:.0f} USD\n\n"
        "For this demo, payment confirmation is simulated.\n\n"
        "After you've paid, tap the button below."
    )

    if owner and owner["usdc_address"]:

        payment_text += (
            "\n\nUSDC address:\n"
            f"`{owner['usdc_address']}`"
        )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ I Paid",
                    callback_data=f"paid_{job_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Back to Order",
                    callback_data=f"order_{job_id}",
                )
            ],
        ]
    )

    await query.message.edit_text(
        payment_text,
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


async def confirm_paid(update, context):

    query = update.callback_query
    await query.answer()

    try:
        job_id = int(
            query.data.split("_")[1]
        )
    except (ValueError, IndexError):
        return

    job = get_client_job(
        update.effective_user.id,
        job_id,
    )

    if not job:
        return

    if job["paused"]:

        await query.message.reply_text(
            "This order is currently paused."
        )

        return

    if job["status"] in {
        "QUOTED",
        "WAITING_PAYMENT",
    }:

        set_job_status(
            job_id,
            "PAID",
        )

        await query.message.edit_text(
            f"✅ Payment confirmed for Order #{job_id}.\n\n"
            "Your project is now in the production queue.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "📦 View Order",
                            callback_data=f"order_{job_id}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "📦 My Orders",
                            callback_data="my_orders",
                        )
                    ],
                ]
            ),
        )

        return

    if job["status"] == "PAID":

        await query.message.reply_text(
            "Payment is already confirmed."
        )

        return

    await query.message.reply_text(
        "This order isn't awaiting payment."
    )


# =========================================================
# EDIT PROPOSAL
# =========================================================

async def edit_order_start(update, context):

    query = update.callback_query
    await query.answer()

    try:
        job_id = int(
            query.data.split("_")[1]
        )
    except (ValueError, IndexError):
        return ConversationHandler.END

    job = get_client_job(
        update.effective_user.id,
        job_id,
    )

    if not job:
        await query.message.reply_text(
            "Order not found."
        )
        return ConversationHandler.END

    if job["status"] not in {
        "QUOTED",
        "WAITING_PAYMENT",
    }:

        await query.message.reply_text(
            "This order can no longer be edited at this stage."
        )

        return ConversationHandler.END

    context.user_data.clear()

    context.user_data["editing_job_id"] = job_id

    await query.message.reply_text(
        f"✏️ Edit Order #{job_id}\n\n"
        "Tell me what you'd like to change.\n\n"
        "For example:\n"
        "“Change it from 5 sections to 3 and make the deadline Friday.”"
    )

    return EDIT_REQUEST


async def handle_edit_request(update, context):

    job_id = context.user_data.get(
        "editing_job_id"
    )

    if not job_id:

        await update.message.reply_text(
            "I couldn't find the order you're editing."
        )

        return ConversationHandler.END

    job = get_client_job(
        update.effective_user.id,
        job_id,
    )

    if not job:

        await update.message.reply_text(
            "Order not found."
        )

        return ConversationHandler.END

    change_request = update.message.text.strip()

    if not change_request:

        await update.message.reply_text(
            "Tell me what you'd like to change."
        )

        return EDIT_REQUEST

    # Store the request in notes.
    notes = job["notes"] or ""

    updated_notes = (
        f"{notes}\n\n"
        f"Client change request: {change_request}"
    ).strip()

    from db import update_job_status_and_notes

    update_job_status_and_notes(
        job_id,
        status="QUALIFYING",
        notes=updated_notes,
    )

    answers = load_answers(job)

    # Keep the original intake data and add the requested
    # change so the LLM can incorporate it.
    answers["change_request"] = change_request

    save_job_answers(
        job_id,
        answers,
    )

    owner = get_owner(
        OWNER_TELEGRAM_ID
    )

    if not owner or not owner["setup_complete"]:

        await update.message.reply_text(
            "The studio hasn't completed setup yet."
        )

        return ConversationHandler.END

    progress = await update.message.reply_text(
        "⚙️ Updating your proposal..."
    )

    await update_progress(
        progress,
        "🔎 Reviewing your requested changes...",
        30,
    )

    await asyncio.sleep(0.3)

    price = calculate_price(
        owner,
        answers,
    )

    await update_progress(
        progress,
        "💰 Recalculating project scope...",
        50,
    )

    await asyncio.sleep(0.3)

    try:

        proposal = await generate_proposal(
            owner,
            answers,
            price,
        )

    except Exception as error:

        print(
            f"LLM revision failed: {error}"
        )

        proposal = template_proposal(
            owner,
            answers,
            price,
        )

    await update_progress(
        progress,
        "✍️ Writing your revised proposal...",
        70,
    )

    save_proposal(
        job_id,
        price,
        proposal,
    )

    await update_progress(
        progress,
        "📄 Generating revised PDF...",
        90,
    )

    pdf = None

    try:

        pdf = create_proposal_pdf(
            studio_name=owner["name"],
            client_name=job["client_name"],
            proposal_text=proposal,
            price=price,
            timeline=f"{owner['default_days']} days",
            proposal_id=f"SB-{job_id:04d}",
        )

    except Exception as error:

        print(
            f"PDF revision failed: {error}"
        )

    set_job_status(
        job_id,
        "WAITING_PAYMENT",
    )

    await update_progress(
        progress,
        "✅ Revised proposal ready!",
        100,
    )

    await asyncio.sleep(0.4)

    try:
        await progress.delete()
    except Exception:
        pass

    updated_job = get_job(job_id)

    await update.message.reply_text(
        "Here is your revised proposal:",
    )

    await update.message.reply_text(
        proposal,
        reply_markup=order_keyboard(updated_job),
    )

    if pdf:

        await update.message.reply_document(
            document=pdf,
            filename=f"proposal_SB-{job_id:04d}-revised.pdf",
            caption="📄 Revised proposal PDF",
        )

    context.user_data.clear()

    return ConversationHandler.END


# =========================================================
# VIEW PROPOSAL
# =========================================================

async def view_proposal(update, context):

    query = update.callback_query
    await query.answer()

    try:
        job_id = int(
            query.data.split("_")[1]
        )
    except (ValueError, IndexError):
        return

    job = get_client_job(
        update.effective_user.id,
        job_id,
    )

    if not job:
        return

    if not job["proposal_text"]:

        await query.message.reply_text(
            "A proposal hasn't been generated for this order yet."
        )

        return

    await query.message.reply_text(
        job["proposal_text"],
        reply_markup=order_keyboard(job),
    )


# =========================================================
# SERVICES
# =========================================================

async def services_page(update, context):

    query = update.callback_query
    await query.answer()

    owner = get_owner(
        OWNER_TELEGRAM_ID
    )

    if not owner:

        await query.message.reply_text(
            "Studio information isn't available yet."
        )

        return

    text = (
        f"ℹ️ {owner['name']}\n\n"
        f"{owner['services_text']}\n\n"
        f"Typical projects: "
        f"${owner['min_price']:.0f}–"
        f"${owner['max_price']:.0f}\n\n"
        f"Standard turnaround: "
        f"{owner['default_days']} days."
    )

    await query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🆕 New Order",
                        callback_data="new_order",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⬅️ Home",
                        callback_data="client_home",
                    )
                ],
            ]
        ),
    )


# =========================================================
# CONTACT
# =========================================================

async def contact_studio(update, context):

    query = update.callback_query
    await query.answer()

    await query.message.edit_text(
        "💬 Contact Studio\n\n"
        "Send your question in this chat and the studio "
        "can respond here.",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "⬅️ Home",
                        callback_data="client_home",
                    )
                ]
            ]
        ),
    )


# =========================================================
# TEXT "PAID" FALLBACK
# =========================================================

async def handle_paid(update, context):

    if is_owner(update):
        return

    text = update.message.text.strip()

    if not is_paid_message(text):
        return

    client_id = update.effective_user.id

    jobs = get_client_jobs(
        client_id
    )

    waiting = [
        job
        for job in jobs
        if job["status"]
        in {
            "QUOTED",
            "WAITING_PAYMENT",
        }
    ]

    if not waiting:

        await update.message.reply_text(
            "I couldn't find an order awaiting payment.\n\n"
            "Open 📦 My Orders to view your orders.",
            reply_markup=main_menu_keyboard(),
        )

        return

    job = waiting[0]

    if job["paused"]:

        await update.message.reply_text(
            "This order is currently paused."
        )

        return

    set_job_status(
        job["id"],
        "PAID",
    )

    await update.message.reply_text(
        f"✅ Payment confirmed for Order #{job['id']}.\n\n"
        "Your project is now in the production queue.",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "📦 View Order",
                        callback_data=f"order_{job['id']}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "📦 My Orders",
                        callback_data="my_orders",
                    )
                ],
            ]
        ),
    )


# =========================================================
# CANCEL
# =========================================================

async def cancel_intake(update, context):

    context.user_data.clear()

    await update.message.reply_text(
        "Cancelled.\n\n"
        "You can start again from the main menu.",
        reply_markup=main_menu_keyboard(),
    )

    return ConversationHandler.END