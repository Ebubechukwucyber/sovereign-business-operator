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
    get_owner,
    save_owner,
    get_all_jobs,
    get_job,
    set_job_paused,
)


# =========================================================
# STATES
# =========================================================

SETUP_NAME = 100
SETUP_SERVICES = 101
SETUP_MIN_PRICE = 102
SETUP_MAX_PRICE = 103
SETUP_DAYS = 104

EDIT_NAME = 110
EDIT_SERVICES = 111
EDIT_MIN_PRICE = 112
EDIT_MAX_PRICE = 113
EDIT_DAYS = 114


def owner_only(update: Update) -> bool:
    return (
        update.effective_user.id
        == OWNER_TELEGRAM_ID
    )


# =========================================================
# OWNER MENU
# =========================================================

def owner_menu_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📦 Jobs",
                    callback_data="owner_jobs",
                ),
            ],
            [
                InlineKeyboardButton(
                    "⚙️ Studio Settings",
                    callback_data="owner_settings",
                ),
            ],
        ]
    )


async def owner_home(update, context):

    if not owner_only(update):
        return

    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
    else:
        message = update.message

    owner = get_owner(
        OWNER_TELEGRAM_ID
    )

    if owner and owner["setup_complete"]:

        await message.reply_text(
            f"🏢 {owner['name']}\n\n"
            "Owner control panel.",
            reply_markup=owner_menu_keyboard(),
        )

    else:

        await message.reply_text(
            "Your studio isn't configured yet.\n\n"
            "Use /setup to get started."
        )


# =========================================================
# INITIAL SETUP
# =========================================================

async def setup_start(update, context):

    if not owner_only(update):
        return ConversationHandler.END

    context.user_data["setup"] = {}

    await update.message.reply_text(
        "Let's configure your studio.\n\n"
        "What is your studio/business name?"
    )

    return SETUP_NAME


async def setup_name(update, context):

    value = update.message.text.strip()

    if not value:
        await update.message.reply_text(
            "Please enter your studio name."
        )
        return SETUP_NAME

    context.user_data["setup"]["name"] = value

    await update.message.reply_text(
        "What services do you sell?"
    )

    return SETUP_SERVICES


async def setup_services(update, context):

    value = update.message.text.strip()

    if not value:
        await update.message.reply_text(
            "Please enter your services."
        )
        return SETUP_SERVICES

    context.user_data["setup"]["services"] = value

    await update.message.reply_text(
        "What is your minimum project price in USD?"
    )

    return SETUP_MIN_PRICE


async def setup_min_price(update, context):

    try:
        value = float(
            update.message.text.strip()
        )

        if value <= 0:
            raise ValueError

    except ValueError:

        await update.message.reply_text(
            "Enter a valid number, e.g. 150."
        )

        return SETUP_MIN_PRICE

    context.user_data["setup"]["min_price"] = value

    await update.message.reply_text(
        "What is your maximum project price in USD?"
    )

    return SETUP_MAX_PRICE


async def setup_max_price(update, context):

    try:
        value = float(
            update.message.text.strip()
        )

        if value <= 0:
            raise ValueError

    except ValueError:

        await update.message.reply_text(
            "Enter a valid number, e.g. 400."
        )

        return SETUP_MAX_PRICE

    context.user_data["setup"]["max_price"] = value

    await update.message.reply_text(
        "What's your default delivery time in days?"
    )

    return SETUP_DAYS


async def setup_days(update, context):

    try:
        days = int(
            update.message.text.strip()
        )

        if days <= 0:
            raise ValueError

    except ValueError:

        await update.message.reply_text(
            "Enter a whole number, e.g. 7."
        )

        return SETUP_DAYS

    data = context.user_data["setup"]

    if data["max_price"] < data["min_price"]:

        await update.message.reply_text(
            "Maximum price cannot be lower than minimum price.\n\n"
            "Enter the maximum price again."
        )

        return SETUP_MAX_PRICE

    save_owner(
        telegram_id=OWNER_TELEGRAM_ID,
        name=data["name"],
        niche="landing pages",
        services_text=data["services"],
        min_price=data["min_price"],
        max_price=data["max_price"],
        default_days=days,
        tone="professional",
        setup_complete=1,
    )

    context.user_data.pop(
        "setup",
        None,
    )

    await update.message.reply_text(
        "✅ Studio setup complete.\n\n"
        "Your business is ready to accept orders."
    )

    return ConversationHandler.END


async def cancel_setup(update, context):

    context.user_data.pop(
        "setup",
        None,
    )

    await update.message.reply_text(
        "Setup cancelled."
    )

    return ConversationHandler.END


# =========================================================
# SETTINGS
# =========================================================

def settings_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🏢 Studio Name",
                    callback_data="edit_name",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🛠 Services",
                    callback_data="edit_services",
                ),
            ],
            [
                InlineKeyboardButton(
                    "💵 Minimum Price",
                    callback_data="edit_min",
                ),
                InlineKeyboardButton(
                    "💵 Maximum Price",
                    callback_data="edit_max",
                ),
            ],
            [
                InlineKeyboardButton(
                    "⏱ Delivery Days",
                    callback_data="edit_days",
                ),
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Owner Menu",
                    callback_data="owner_home",
                ),
            ],
        ]
    )


async def settings_menu(update, context):

    query = update.callback_query

    if not owner_only(update):
        await query.answer()
        return

    await query.answer()

    owner = get_owner(
        OWNER_TELEGRAM_ID
    )

    if not owner:
        await query.message.reply_text(
            "Run /setup first."
        )
        return

    text = (
        "⚙️ Studio Settings\n\n"
        f"Studio: {owner['name']}\n"
        f"Services: {owner['services_text']}\n"
        f"Min price: ${owner['min_price']:.0f}\n"
        f"Max price: ${owner['max_price']:.0f}\n"
        f"Delivery: {owner['default_days']} days\n\n"
        "Choose what you want to edit."
    )

    await query.message.edit_text(
        text,
        reply_markup=settings_keyboard(),
    )


async def edit_name_start(update, context):

    query = update.callback_query
    await query.answer()

    context.user_data["editing_setting"] = "name"

    await query.message.reply_text(
        "Enter the new studio name."
    )

    return EDIT_NAME


async def edit_services_start(update, context):

    query = update.callback_query
    await query.answer()

    context.user_data["editing_setting"] = "services"

    await query.message.reply_text(
        "Enter the services you want to offer."
    )

    return EDIT_SERVICES


async def edit_min_start(update, context):

    query = update.callback_query
    await query.answer()

    context.user_data["editing_setting"] = "min"

    await query.message.reply_text(
        "Enter the new minimum price."
    )

    return EDIT_MIN_PRICE


async def edit_max_start(update, context):

    query = update.callback_query
    await query.answer()

    context.user_data["editing_setting"] = "max"

    await query.message.reply_text(
        "Enter the new maximum price."
    )

    return EDIT_MAX_PRICE


async def edit_days_start(update, context):

    query = update.callback_query
    await query.answer()

    context.user_data["editing_setting"] = "days"

    await query.message.reply_text(
        "Enter the new default delivery time in days."
    )

    return EDIT_DAYS


async def save_setting_value(update, context):

    value = update.message.text.strip()

    owner = get_owner(
        OWNER_TELEGRAM_ID
    )

    if not owner:
        await update.message.reply_text(
            "Studio setup was not found. Run /setup."
        )
        return ConversationHandler.END

    setting = context.user_data.get(
        "editing_setting"
    )

    data = {
        "name": owner["name"],
        "services_text": owner["services_text"],
        "min_price": owner["min_price"],
        "max_price": owner["max_price"],
        "default_days": owner["default_days"],
    }

    if setting == "name":

        if not value:
            await update.message.reply_text(
                "Studio name cannot be empty."
            )
            return EDIT_NAME

        data["name"] = value

    elif setting == "services":

        if not value:
            await update.message.reply_text(
                "Services cannot be empty."
            )
            return EDIT_SERVICES

        data["services_text"] = value

    elif setting == "min":

        try:
            number = float(value)

            if number <= 0:
                raise ValueError

        except ValueError:

            await update.message.reply_text(
                "Enter a valid price."
            )

            return EDIT_MIN_PRICE

        if number > data["max_price"]:

            await update.message.reply_text(
                "Minimum price cannot exceed maximum price."
            )

            return EDIT_MIN_PRICE

        data["min_price"] = number

    elif setting == "max":

        try:
            number = float(value)

            if number <= 0:
                raise ValueError

        except ValueError:

            await update.message.reply_text(
                "Enter a valid price."
            )

            return EDIT_MAX_PRICE

        if number < data["min_price"]:

            await update.message.reply_text(
                "Maximum price cannot be below minimum price."
            )

            return EDIT_MAX_PRICE

        data["max_price"] = number

    elif setting == "days":

        try:
            number = int(value)

            if number <= 0:
                raise ValueError

        except ValueError:

            await update.message.reply_text(
                "Enter a whole number of days."
            )

            return EDIT_DAYS

        data["default_days"] = number

    save_owner(
        telegram_id=OWNER_TELEGRAM_ID,
        name=data["name"],
        niche=owner["niche"],
        services_text=data["services_text"],
        min_price=data["min_price"],
        max_price=data["max_price"],
        default_days=data["default_days"],
        tone=owner["tone"],
        usdc_address=owner["usdc_address"],
        setup_complete=1,
    )

    context.user_data.pop(
        "editing_setting",
        None,
    )

    await update.message.reply_text(
        "✅ Setting updated."
    )

    return ConversationHandler.END


# =========================================================
# JOBS
# =========================================================

async def jobs_command(update, context):

    if not owner_only(update):
        return

    jobs = get_all_jobs()

    if not jobs:

        await update.message.reply_text(
            "No orders yet."
        )

        return

    lines = [
        "📦 Sovereign Jobs",
        "",
    ]

    for job in jobs:

        price = job["quoted_price"]

        price_text = (
            f"${price:.0f}"
            if price
            else "—"
        )

        paused = (
            " • PAUSED"
            if job["paused"]
            else ""
        )

        lines.append(
            f"#{job['id']} • "
            f"{job['client_name'] or 'Client'} • "
            f"{price_text} • "
            f"{job['status']}"
            f"{paused}"
        )

    await update.message.reply_text(
        "\n".join(lines)
    )


async def job_command(update, context):

    if not owner_only(update):
        return

    if not context.args:

        await update.message.reply_text(
            "Usage: /job <id>"
        )

        return

    try:
        job_id = int(
            context.args[0]
        )

    except ValueError:

        await update.message.reply_text(
            "Job ID must be a number."
        )

        return

    job = get_job(job_id)

    if not job:

        await update.message.reply_text(
            f"Job #{job_id} was not found."
        )

        return

    price = job["quoted_price"]

    price_text = (
        f"${price:.0f} USD"
        if price
        else "Not quoted"
    )

    paused = (
        "Yes"
        if job["paused"]
        else "No"
    )

    text = (
        f"📦 Order #{job['id']}\n\n"
        f"Client: {job['client_name']}\n"
        f"Telegram ID: {job['client_telegram_id']}\n"
        f"Status: {job['status']}\n"
        f"Price: {price_text}\n"
        f"Paused: {paused}\n"
        f"Created: {job['created_at']}"
    )

    await update.message.reply_text(
        text
    )


async def pause_command(update, context):

    if not owner_only(update):
        return

    if not context.args:

        await update.message.reply_text(
            "Usage: /pause <id>"
        )

        return

    try:
        job_id = int(
            context.args[0]
        )

    except ValueError:

        await update.message.reply_text(
            "Job ID must be a number."
        )

        return

    job = get_job(job_id)

    if not job:

        await update.message.reply_text(
            f"Job #{job_id} was not found."
        )

        return

    set_job_paused(
        job_id,
        True,
    )

    await update.message.reply_text(
        f"⏸ Order #{job_id} is now paused."
    )


async def resume_command(update, context):

    if not owner_only(update):
        return

    if not context.args:

        await update.message.reply_text(
            "Usage: /resume <id>"
        )

        return

    try:
        job_id = int(
            context.args[0]
        )

    except ValueError:

        await update.message.reply_text(
            "Job ID must be a number."
        )

        return

    job = get_job(job_id)

    if not job:

        await update.message.reply_text(
            f"Job #{job_id} was not found."
        )

        return

    set_job_paused(
        job_id,
        False,
    )

    await update.message.reply_text(
        f"▶️ Order #{job_id} has been resumed."
    )