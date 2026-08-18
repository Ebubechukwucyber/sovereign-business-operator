from telegram import Update
from telegram.ext import (
    ConversationHandler,
    ContextTypes,
)

from config import OWNER_TELEGRAM_ID
from db import save_owner


STUDIO_NAME, SERVICES, MIN_PRICE, MAX_PRICE, DEFAULT_DAYS = range(5)


def is_owner(update: Update) -> bool:
    return update.effective_user.id == OWNER_TELEGRAM_ID


async def setup_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    if not is_owner(update):
        await update.message.reply_text(
            "Sorry, that command is for the owner."
        )
        return ConversationHandler.END

    context.user_data["setup"] = {}

    await update.message.reply_text(
        "Let's set up your studio.\n\n"
        "What's your studio name?"
    )

    return STUDIO_NAME


async def studio_name(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    context.user_data["setup"]["name"] = update.message.text.strip()

    await update.message.reply_text(
        "What services do you offer?"
    )

    return SERVICES


async def services(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    context.user_data["setup"]["services"] = update.message.text.strip()

    await update.message.reply_text(
        "What's your minimum price in USD?"
    )

    return MIN_PRICE


async def min_price(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    try:
        value = float(update.message.text.strip())
        if value <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "Please enter a valid number, e.g. 150."
        )
        return MIN_PRICE

    context.user_data["setup"]["min_price"] = value

    await update.message.reply_text(
        "What's your maximum price in USD?"
    )

    return MAX_PRICE


async def max_price(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    try:
        value = float(update.message.text.strip())
        if value <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "Please enter a valid number, e.g. 400."
        )
        return MAX_PRICE

    setup = context.user_data["setup"]

    if value < setup["min_price"]:
        await update.message.reply_text(
            "Maximum price can't be below minimum price.\n"
            "Enter the maximum price again."
        )
        return MAX_PRICE

    setup["max_price"] = value

    await update.message.reply_text(
        "What's your default delivery time in days?"
    )

    return DEFAULT_DAYS


async def default_days(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    try:
        value = int(update.message.text.strip())
        if value <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "Please enter a whole number, e.g. 7."
        )
        return DEFAULT_DAYS

    setup = context.user_data["setup"]
    setup["default_days"] = value

    save_owner(
        telegram_id=update.effective_user.id,
        name=setup["name"],
        services_text=setup["services"],
        min_price=setup["min_price"],
        max_price=setup["max_price"],
        default_days=setup["default_days"],
    )

    context.user_data.pop("setup", None)

    await update.message.reply_text(
        "Setup complete ✅\n\n"
        f"Studio: {setup['name']}\n"
        f"Services: {setup['services']}\n"
        f"Price: ${setup['min_price']:.0f}–${setup['max_price']:.0f}\n"
        f"Default delivery: {setup['default_days']} days"
    )

    return ConversationHandler.END


async def setup_cancel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    context.user_data.pop("setup", None)

    await update.message.reply_text(
        "Setup cancelled."
    )

    return ConversationHandler.END