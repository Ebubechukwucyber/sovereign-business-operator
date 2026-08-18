from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import OWNER_TELEGRAM_ID, TELEGRAM_BOT_TOKEN
from db import init_db
from handlers.owner import (
    setup_start,
    studio_name,
    services,
    min_price,
    max_price,
    default_days,
    setup_cancel,
    STUDIO_NAME,
    SERVICES,
    MIN_PRICE,
    MAX_PRICE,
    DEFAULT_DAYS,
)


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    user_id = update.effective_user.id

    if user_id == OWNER_TELEGRAM_ID:
        await update.message.reply_text(
            "Welcome back, Owner.\n\n"
            "Sovereign Business Operator is online.\n\n"
            "/setup — configure your business"
        )
    else:
        await update.message.reply_text(
            "Hi! 👋\n\n"
            "I'm the studio assistant."
        )


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is missing from .env")

    if not OWNER_TELEGRAM_ID:
        raise ValueError("OWNER_TELEGRAM_ID is missing from .env")

    init_db()

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    setup_handler = ConversationHandler(
        entry_points=[
            CommandHandler("setup", setup_start)
        ],
        states={
            STUDIO_NAME: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    studio_name,
                )
            ],
            SERVICES: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    services,
                )
            ],
            MIN_PRICE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    min_price,
                )
            ],
            MAX_PRICE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    max_price,
                )
            ],
            DEFAULT_DAYS: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    default_days,
                )
            ],
        },
        fallbacks=[
            CommandHandler("cancel", setup_cancel)
        ],
    )

    app.add_handler(setup_handler)
    app.add_handler(CommandHandler("start", start))

    print("Sovereign Business Operator is running...")
    app.run_polling()


if __name__ == "__main__":
    main()