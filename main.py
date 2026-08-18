from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from config import (
    TELEGRAM_BOT_TOKEN,
    OWNER_TELEGRAM_ID,
)

from db import init_db

from handlers.owner import (
    setup_start,
    setup_name,
    setup_services,
    setup_min_price,
    setup_max_price,
    setup_days,
    cancel_setup,

    settings_menu,
    edit_name_start,
    edit_services_start,
    edit_min_start,
    edit_max_start,
    edit_days_start,
    save_setting_value,

    owner_home,

    jobs_command,
    job_command,
    pause_command,
    resume_command,

    SETUP_NAME,
    SETUP_SERVICES,
    SETUP_MIN_PRICE,
    SETUP_MAX_PRICE,
    SETUP_DAYS,

    EDIT_NAME,
    EDIT_SERVICES,
    EDIT_MIN_PRICE,
    EDIT_MAX_PRICE,
    EDIT_DAYS,
)

from handlers.client import (
    start_client,
    new_order_start,
    handle_client_name,
    handle_intake_answer,
    handle_edit_request,
    cancel_intake,

    client_home,
    my_orders,
    order_detail,
    payment_page,
    confirm_paid,
    edit_order_start,
    view_proposal,
    services_page,
    contact_studio,
    handle_paid,

    NAME,
    QUESTION_1,
    QUESTION_2,
    QUESTION_3,
    QUESTION_4,
    QUESTION_5,
    EDIT_REQUEST,
)


# =========================================================
# /START
# =========================================================

async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user_id = update.effective_user.id

    if user_id == OWNER_TELEGRAM_ID:

        await owner_home(
            update,
            context,
        )

        return ConversationHandler.END

    await start_client(
        update,
        context,
    )

    return ConversationHandler.END


# =========================================================
# MAIN
# =========================================================

def main():

    init_db()

    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is missing from .env"
        )

    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    # =====================================================
    # OWNER SETUP
    # =====================================================

    owner_setup_conversation = ConversationHandler(
        entry_points=[
            CommandHandler(
                "setup",
                setup_start,
            ),
        ],

        states={

            SETUP_NAME: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    setup_name,
                )
            ],

            SETUP_SERVICES: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    setup_services,
                )
            ],

            SETUP_MIN_PRICE: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    setup_min_price,
                )
            ],

            SETUP_MAX_PRICE: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    setup_max_price,
                )
            ],

            SETUP_DAYS: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    setup_days,
                )
            ],
        },

        fallbacks=[
            CommandHandler(
                "cancel",
                cancel_setup,
            ),
        ],

        allow_reentry=True,
    )

    application.add_handler(
        owner_setup_conversation
    )

    # =====================================================
    # OWNER SETTINGS EDITING
    # =====================================================

    owner_settings_conversation = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                edit_name_start,
                pattern=r"^edit_name$",
            ),
            CallbackQueryHandler(
                edit_services_start,
                pattern=r"^edit_services$",
            ),
            CallbackQueryHandler(
                edit_min_start,
                pattern=r"^edit_min$",
            ),
            CallbackQueryHandler(
                edit_max_start,
                pattern=r"^edit_max$",
            ),
            CallbackQueryHandler(
                edit_days_start,
                pattern=r"^edit_days$",
            ),
        ],

        states={

            EDIT_NAME: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    save_setting_value,
                )
            ],

            EDIT_SERVICES: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    save_setting_value,
                )
            ],

            EDIT_MIN_PRICE: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    save_setting_value,
                )
            ],

            EDIT_MAX_PRICE: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    save_setting_value,
                )
            ],

            EDIT_DAYS: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    save_setting_value,
                )
            ],
        },

        fallbacks=[
            CommandHandler(
                "cancel",
                cancel_setup,
            ),
        ],

        allow_reentry=True,
    )

    application.add_handler(
        owner_settings_conversation
    )

    # =====================================================
    # CLIENT ORDER CONVERSATION
    # =====================================================

    client_order_conversation = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                new_order_start,
                pattern=r"^new_order$",
            ),

            CallbackQueryHandler(
                edit_order_start,
                pattern=r"^edit_\d+$",
            ),
        ],

        states={

            NAME: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    handle_client_name,
                )
            ],

            QUESTION_1: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    handle_intake_answer,
                )
            ],

            QUESTION_2: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    handle_intake_answer,
                )
            ],

            QUESTION_3: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    handle_intake_answer,
                )
            ],

            QUESTION_4: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    handle_intake_answer,
                )
            ],

            QUESTION_5: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    handle_intake_answer,
                )
            ],

            EDIT_REQUEST: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    handle_edit_request,
                )
            ],
        },

        fallbacks=[
            CommandHandler(
                "cancel",
                cancel_intake,
            ),
        ],

        allow_reentry=True,
    )

    application.add_handler(
        client_order_conversation
    )

    # =====================================================
    # /START
    # =====================================================

    application.add_handler(
        CommandHandler(
            "start",
            start_command,
        ),
    )

    # =====================================================
    # OWNER COMMANDS
    # =====================================================

    application.add_handler(
        CommandHandler(
            "jobs",
            jobs_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "job",
            job_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "pause",
            pause_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "resume",
            resume_command,
        )
    )

    # =====================================================
    # OWNER BUTTONS
    # =====================================================

    application.add_handler(
        CallbackQueryHandler(
            owner_home,
            pattern=r"^owner_home$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            settings_menu,
            pattern=r"^owner_settings$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            jobs_command,
            pattern=r"^owner_jobs$",
        )
    )

    # =====================================================
    # CLIENT BUTTONS
    # =====================================================

    application.add_handler(
        CallbackQueryHandler(
            client_home,
            pattern=r"^client_home$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            my_orders,
            pattern=r"^my_orders$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            order_detail,
            pattern=r"^order_\d+$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            payment_page,
            pattern=r"^pay_\d+$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            confirm_paid,
            pattern=r"^paid_\d+$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            view_proposal,
            pattern=r"^proposal_\d+$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            services_page,
            pattern=r"^services$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            contact_studio,
            pattern=r"^contact_studio$",
        )
    )

    # =====================================================
    # TEXT "PAID" FALLBACK
    # =====================================================

    application.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            handle_paid,
        )
    )

    print(
        "Sovereign Business Operator is running..."
    )

    application.run_polling()


if __name__ == "__main__":
    main()