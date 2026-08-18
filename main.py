from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config import OWNER_TELEGRAM_ID, TELEGRAM_BOT_TOKEN


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    if user_id == OWNER_TELEGRAM_ID:
        await update.message.reply_text(
            "Welcome back, Owner.\n\n"
            "Sovereign Business Operator is online.\n\n"
            "Available commands:\n"
            "/setup — configure your business"
        )
    else:
        await update.message.reply_text(
            "Hi! 👋\n\n"
            "I'm the studio assistant. "
            "Tell me what kind of landing page you need."
        )


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is missing from .env")

    if not OWNER_TELEGRAM_ID:
        raise ValueError("OWNER_TELEGRAM_ID is missing from .env")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    print("Sovereign Business Operator is running...")
    app.run_polling()


if __name__ == "__main__":
    main()