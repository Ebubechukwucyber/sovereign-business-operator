
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
    # =====================================================
    # SETUP
    # =====================================================

    setup_start,
    setup_name,
    setup_niche,
    setup_services,
    setup_min_price,
    setup_max_price,
    setup_days,
    setup_email,
    cancel_setup,

    SETUP_NAME,
    SETUP_NICHE,
    SETUP_SERVICES,
    SETUP_MIN_PRICE,
    SETUP_MAX_PRICE,
    SETUP_DAYS,
    SETUP_EMAIL,

    # =====================================================
    # SETTINGS
    # =====================================================

    settings_menu,
    edit_name_start,
    edit_niche_start,
    edit_services_start,
    edit_min_start,
    edit_max_start,
    edit_days_start,
    edit_slug_start,
    save_slug_value,
    save_setting_value,

    EDIT_NAME,
    EDIT_NICHE,
    EDIT_SERVICES,
    EDIT_MIN_PRICE,
    EDIT_MAX_PRICE,
    EDIT_DAYS,
    EDIT_SLUG,

    # =====================================================
    # PAYMENTS
    # =====================================================

    payments_menu,
    edit_wallet_start,
    save_wallet,

    EDIT_WALLET,

    # =====================================================
    # SIGNATURE
    # =====================================================

    signature_menu,
    edit_signature_name_start,
    edit_signature_title_start,
    edit_signature_image_start,
    save_signature_text,
    save_signature_image,

    EDIT_SIGNATURE_NAME,
    EDIT_SIGNATURE_TITLE,
    EDIT_SIGNATURE_IMAGE,

    # =====================================================
    # OWNER HOME / JOBS
    # =====================================================

    owner_home,
    owner_stats_callback,
    owner_guide_callback,
    admin_stats_command,
    jobs_command,
    job_command,
    pause_command,
    resume_command,

    # =====================================================
    # ORDER CALLBACKS
    # =====================================================

    owner_job_detail,
    pause_job_callback,
    resume_job_callback,
    deliver_job_callback,
    close_job_callback,
    resend_receipt_callback,
    resend_invoice_callback,
    export_job_callback,
    export_all_jobs_callback,
    sendfile_job_start,
    sendfile_job_receive,
    sendfile_cancel,
    SEND_FILE_WAIT,
)


from handlers.client import (
    # =====================================================
    # CLIENT
    # =====================================================

    start_client,
    client_guide,
    owner_hint_setup,
    new_order_start,
    handle_client_name,
    handle_intake_answer,
    handle_edit_request,
    cancel_intake,

    client_home,
    my_orders,
    order_detail,

    # =====================================================
    # PAYMENTS
    # =====================================================

    payment_page,
    confirm_paid,
    handle_paid,

    # =====================================================
    # ORDERS / PROPOSALS
    # =====================================================

    edit_order_start,
    view_proposal,

    # =====================================================
    # SERVICES / CONTACT
    # =====================================================

    services_page,
    contact_studio,

    # =====================================================
    # CLIENT STATES
    # =====================================================

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
    """
    Main entry point.

    Registered owner (no client invite args) -> owner panel.
    Client invite /start slug -> client UI for that business.
    """

    user = update.effective_user

    if not user:
        return ConversationHandler.END

    user_id = user.id

    # Client deep-link always wins (owner can preview another studio)
    has_client_args = bool(context.args)

    if not has_client_args:
        try:
            from db import get_owner
            row = get_owner(user_id)
            is_owner = (
                row is not None
                and int(row["setup_complete"] or 0) == 1
            )
        except Exception:
            is_owner = False

        if is_owner or (OWNER_TELEGRAM_ID and user_id == OWNER_TELEGRAM_ID):
            await owner_home(update, context)
            return ConversationHandler.END

    await start_client(update, context)
    return ConversationHandler.END


# =========================================================
# BUILD APPLICATION
# =========================================================

def build_application():

    # -----------------------------------------------------
    # CHECK TOKEN
    # -----------------------------------------------------

    if not TELEGRAM_BOT_TOKEN:

        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is missing from .env"
        )

    # -----------------------------------------------------
    # CREATE APPLICATION
    # -----------------------------------------------------

    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )


    # =====================================================
    # OWNER SETUP CONVERSATION
    # =====================================================

    owner_setup_conversation = ConversationHandler(

        entry_points=[
            CommandHandler(
                "setup",
                setup_start,
            ),
        ],

        states={

            # -------------------------------------------------
            # BUSINESS NAME
            # -------------------------------------------------

            SETUP_NAME: [

                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    setup_name,
                ),

            ],

            # -------------------------------------------------
            # BUSINESS TYPE
            # -------------------------------------------------

            SETUP_NICHE: [

                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    setup_niche,
                ),

            ],

            # -------------------------------------------------
            # SERVICES
            # -------------------------------------------------

            SETUP_SERVICES: [

                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    setup_services,
                ),

            ],

            # -------------------------------------------------
            # MINIMUM PRICE
            # -------------------------------------------------

            SETUP_MIN_PRICE: [

                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    setup_min_price,
                ),

            ],

            # -------------------------------------------------
            # MAXIMUM PRICE
            # -------------------------------------------------

            SETUP_MAX_PRICE: [

                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    setup_max_price,
                ),

            ],

            # -------------------------------------------------
            # DELIVERY DAYS
            # -------------------------------------------------

            SETUP_DAYS: [

                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    setup_days,
                ),

            ],

            SETUP_EMAIL: [

                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    setup_email,
                ),

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
    # OWNER BUSINESS SETTINGS CONVERSATION
    # =====================================================

    owner_settings_conversation = ConversationHandler(

        entry_points=[

            # -------------------------------------------------
            # EDIT NAME
            # -------------------------------------------------

            CallbackQueryHandler(
                edit_name_start,
                pattern=r"^edit_name$",
            ),

            # -------------------------------------------------
            # EDIT BUSINESS TYPE
            # -------------------------------------------------

            CallbackQueryHandler(
                edit_niche_start,
                pattern=r"^edit_niche$",
            ),

            # -------------------------------------------------
            # EDIT SERVICES
            # -------------------------------------------------

            CallbackQueryHandler(
                edit_services_start,
                pattern=r"^edit_services$",
            ),

            # -------------------------------------------------
            # EDIT MINIMUM PRICE
            # -------------------------------------------------

            CallbackQueryHandler(
                edit_min_start,
                pattern=r"^edit_min$",
            ),

            # -------------------------------------------------
            # EDIT MAXIMUM PRICE
            # -------------------------------------------------

            CallbackQueryHandler(
                edit_max_start,
                pattern=r"^edit_max$",
            ),

            # -------------------------------------------------
            # EDIT DELIVERY DAYS
            # -------------------------------------------------

            CallbackQueryHandler(
                edit_days_start,
                pattern=r"^edit_days$",
            ),
            CallbackQueryHandler(
                edit_slug_start,
                pattern=r"^edit_slug$",
            ),
        ],

        states={

            # -------------------------------------------------
            # NAME
            # -------------------------------------------------

            EDIT_NAME: [

                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    save_setting_value,
                ),

            ],

            # -------------------------------------------------
            # NICHE
            # -------------------------------------------------

            EDIT_NICHE: [

                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    save_setting_value,
                ),

            ],

            # -------------------------------------------------
            # SERVICES
            # -------------------------------------------------

            EDIT_SERVICES: [

                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    save_setting_value,
                ),

            ],

            # -------------------------------------------------
            # MINIMUM PRICE
            # -------------------------------------------------

            EDIT_MIN_PRICE: [

                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    save_setting_value,
                ),

            ],

            # -------------------------------------------------
            # MAXIMUM PRICE
            # -------------------------------------------------

            EDIT_MAX_PRICE: [

                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    save_setting_value,
                ),

            ],

            # -------------------------------------------------
            # DELIVERY DAYS
            # -------------------------------------------------

            EDIT_SLUG: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    save_slug_value,
                ),
            ],
            EDIT_DAYS: [

                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    save_setting_value,
                ),

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
    # OWNER PAYMENT / SIGNATURE CONVERSATION
    # =====================================================

    owner_payment_signature_conversation = ConversationHandler(

        entry_points=[

            # -------------------------------------------------
            # EDIT WALLET
            # -------------------------------------------------

            CallbackQueryHandler(
                edit_wallet_start,
                pattern=r"^edit_wallet$",
            ),

            # -------------------------------------------------
            # EDIT SIGNATURE NAME
            # -------------------------------------------------

            CallbackQueryHandler(
                edit_signature_name_start,
                pattern=r"^edit_signature_name$",
            ),

            # -------------------------------------------------
            # EDIT SIGNATURE TITLE
            # -------------------------------------------------

            CallbackQueryHandler(
                edit_signature_title_start,
                pattern=r"^edit_signature_title$",
            ),

            # -------------------------------------------------
            # EDIT SIGNATURE IMAGE
            # -------------------------------------------------

            CallbackQueryHandler(
                edit_signature_image_start,
                pattern=r"^edit_signature_image$",
            ),
        ],

        states={

            # -------------------------------------------------
            # WALLET
            # -------------------------------------------------

            EDIT_WALLET: [

                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    save_wallet,
                ),

            ],

            # -------------------------------------------------
            # SIGNATURE NAME
            # -------------------------------------------------

            EDIT_SIGNATURE_NAME: [

                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    save_signature_text,
                ),

            ],

            # -------------------------------------------------
            # SIGNATURE TITLE
            # -------------------------------------------------

            EDIT_SIGNATURE_TITLE: [

                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    save_signature_text,
                ),

            ],

            # -------------------------------------------------
            # SIGNATURE IMAGE
            # -------------------------------------------------

            EDIT_SIGNATURE_IMAGE: [

                MessageHandler(
                    filters.PHOTO,
                    save_signature_image,
                ),

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
        owner_payment_signature_conversation
    )


    # =====================================================
    # CLIENT ORDER / PROJECT INTAKE
    # =====================================================

    client_order_conversation = ConversationHandler(

        entry_points=[

            # -------------------------------------------------
            # NEW ORDER
            # -------------------------------------------------

            CallbackQueryHandler(
                new_order_start,
                pattern=r"^new_order$",
            ),

            # -------------------------------------------------
            # EDIT EXISTING ORDER
            # -------------------------------------------------

            CallbackQueryHandler(
                edit_order_start,
                pattern=r"^edit_\d+$",
            ),
        ],

        states={

            # -------------------------------------------------
            # CLIENT NAME
            # -------------------------------------------------

            NAME: [

                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    handle_client_name,
                ),

            ],

            # -------------------------------------------------
            # QUESTION 1
            # -------------------------------------------------

            QUESTION_1: [

                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    handle_intake_answer,
                ),

            ],

            # -------------------------------------------------
            # QUESTION 2
            # -------------------------------------------------

            QUESTION_2: [

                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    handle_intake_answer,
                ),

            ],

            # -------------------------------------------------
            # QUESTION 3
            # -------------------------------------------------

            QUESTION_3: [

                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    handle_intake_answer,
                ),

            ],

            # -------------------------------------------------
            # QUESTION 4
            # -------------------------------------------------

            QUESTION_4: [

                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    handle_intake_answer,
                ),

            ],

            # -------------------------------------------------
            # QUESTION 5
            # -------------------------------------------------

            QUESTION_5: [

                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    handle_intake_answer,
                ),

            ],

            # -------------------------------------------------
            # EDIT REQUEST
            # -------------------------------------------------

            EDIT_REQUEST: [

                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    handle_edit_request,
                ),

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
        )
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
    # OWNER DASHBOARD
    # =====================================================

    application.add_handler(
        CallbackQueryHandler(
            owner_home,
            pattern=r"^owner_home$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            owner_stats_callback,
            pattern=r"^owner_stats$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            owner_guide_callback,
            pattern=r"^owner_guide$",
        )
    )

    application.add_handler(
        CommandHandler(
            "admin_stats",
            admin_stats_command,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            client_guide,
            pattern=r"^client_guide$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            owner_hint_setup,
            pattern=r"^owner_hint_setup$",
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
    # OWNER PAYMENTS
    # =====================================================

    application.add_handler(
        CallbackQueryHandler(
            payments_menu,
            pattern=r"^owner_payments$",
        )
    )


    # =====================================================
    # OWNER SIGNATURE
    # =====================================================

    application.add_handler(
        CallbackQueryHandler(
            signature_menu,
            pattern=r"^owner_signature$",
        )
    )


    # =====================================================
    # OWNER ORDER DETAIL
    # =====================================================

    application.add_handler(
        CallbackQueryHandler(
            owner_job_detail,
            pattern=r"^owner_job_\d+$",
        )
    )


    # =====================================================
    # PAUSE / RESUME ORDER CALLBACKS
    # =====================================================

    application.add_handler(
        CallbackQueryHandler(
            pause_job_callback,
            pattern=r"^pause_job_\d+$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            resume_job_callback,
            pattern=r"^resume_job_\d+$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            deliver_job_callback,
            pattern=r"^deliver_job_\d+$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            close_job_callback,
            pattern=r"^close_job_\d+$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            resend_receipt_callback,
            pattern=r"^resend_receipt_\d+$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            resend_invoice_callback,
            pattern=r"^resend_invoice_\d+$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            export_job_callback,
            pattern=r"^export_job_\d+$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            export_all_jobs_callback,
            pattern=r"^export_all_jobs$",
        )
    )

    owner_sendfile_conversation = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                sendfile_job_start,
                pattern=r"^sendfile_job_\d+$",
            ),
        ],
        states={
            SEND_FILE_WAIT: [
                MessageHandler(
                    filters.Document.ALL
                    | filters.PHOTO
                    | filters.VIDEO
                    | filters.AUDIO,
                    sendfile_job_receive,
                ),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", sendfile_cancel),
        ],
        allow_reentry=True,
    )
    application.add_handler(owner_sendfile_conversation)


    # =====================================================
    # CLIENT HOME
    # =====================================================

    application.add_handler(
        CallbackQueryHandler(
            client_home,
            pattern=r"^client_home$",
        )
    )


    # =====================================================
    # CLIENT ORDERS
    # =====================================================

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


    # =====================================================
    # PAYMENTS
    # =====================================================

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


    # =====================================================
    # PROPOSALS
    # =====================================================

    application.add_handler(
        CallbackQueryHandler(
            view_proposal,
            pattern=r"^proposal_\d+$",
        )
    )


    # =====================================================
    # SERVICES
    # =====================================================

    application.add_handler(
        CallbackQueryHandler(
            services_page,
            pattern=r"^services$",
        )
    )


    # =====================================================
    # CONTACT
    # =====================================================

    application.add_handler(
        CallbackQueryHandler(
            contact_studio,
            pattern=r"^contact_studio$",
        )
    )


    # =====================================================
    # PAYMENT TEXT FALLBACK
    # =====================================================

    application.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            handle_paid,
        )
    )


    return application


# =========================================================
# MAIN
# =========================================================

def main():

    # -----------------------------------------------------
    # INITIALIZE DATABASE
    # -----------------------------------------------------

    init_db()

    # -----------------------------------------------------
    # BUILD APPLICATION
    # -----------------------------------------------------

    application = build_application()

    # -----------------------------------------------------
    # LOG
    # -----------------------------------------------------

    print(
        "Sovereign Business Operator is running..."
    )

    print(
        "Business-agnostic client intake enabled."
    )

    print(
        "Base USDC payment system enabled."
    )

    print(
        "Owner payment and signature controls enabled."
    )

    # -----------------------------------------------------
    # START BOT
    # -----------------------------------------------------

    application.run_polling()


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    main()

