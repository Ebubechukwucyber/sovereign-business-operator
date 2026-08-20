from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import ConversationHandler

from config import OWNER_TELEGRAM_ID

from db import (
    get_owner,
    save_owner,
    get_all_jobs,
    get_job,
    set_job_paused,
    set_job_status,
    get_business_rules,
    save_business_rules,
    get_owner_signature,
    save_owner_signature,
    get_receipt_file,
    get_invoice_file,
)


# =========================================================
# STATES
# =========================================================

SETUP_NAME = 100
SETUP_NICHE = 101
SETUP_SERVICES = 102
SETUP_MIN_PRICE = 103
SETUP_MAX_PRICE = 104
SETUP_DAYS = 105

EDIT_NAME = 110
EDIT_NICHE = 111
EDIT_SERVICES = 112
EDIT_MIN_PRICE = 113
EDIT_MAX_PRICE = 114
EDIT_DAYS = 115

EDIT_WALLET = 120
EDIT_SIGNATURE_NAME = 121
EDIT_SIGNATURE_TITLE = 122
EDIT_SIGNATURE_IMAGE = 123


# =========================================================
# AUTHORIZATION
# =========================================================

def owner_only(update: Update) -> bool:
    user = update.effective_user

    if not user:
        return False

    return user.id == OWNER_TELEGRAM_ID


# =========================================================
# COMMON
# =========================================================

def owner_menu_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📦 Orders",
                    callback_data="owner_jobs",
                ),
            ],
            [
                InlineKeyboardButton(
                    "⚙️ Business Settings",
                    callback_data="owner_settings",
                ),
            ],
            [
                InlineKeyboardButton(
                    "💳 Payments",
                    callback_data="owner_payments",
                ),
                InlineKeyboardButton(
                    "✍️ Signature",
                    callback_data="owner_signature",
                ),
            ],
        ]
    )


def back_owner_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🏠 Owner Menu",
                    callback_data="owner_home",
                )
            ]
        ]
    )


def back_settings_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "⬅️ Business Settings",
                    callback_data="owner_settings",
                )
            ],
            [
                InlineKeyboardButton(
                    "🏠 Owner Menu",
                    callback_data="owner_home",
                )
            ],
        ]
    )


# =========================================================
# OWNER HOME
# =========================================================

async def owner_home(update, context):

    if not owner_only(update):
        return

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        message = query.message
    else:
        message = update.message

    owner = get_owner(OWNER_TELEGRAM_ID)

    if not owner or not owner["setup_complete"]:

        await message.reply_text(
            "Welcome, owner.\n\n"
            "Your studio is not configured yet. "
            "Follow these steps once:\n\n"
            "1. Send /setup — business name, niche, "
            "services, and pricing\n"
            "2. Open Payments — set your USDC wallet "
            "(Base mainnet USDC)\n"
            "3. Optional: Signature — name/title on invoices\n\n"
            "After that, clients can start projects and pay. "
            "You manage orders from this same bot.\n\n"
            "Start now: /setup"
        )

        return

    wallet = (
        owner["usdc_address"]
        or "Not configured"
    )

    signature_name = (
        owner["signature_name"]
        or "Not configured"
    )

    wallet_ok = wallet != "Not configured"
    next_hint = ""
    if not wallet_ok:
        next_hint = (
            "\n\nNext step: open Payments and set your "
            "USDC receive wallet so clients can pay."
        )

    await message.reply_text(
        f"🏢 {owner['name']} — Owner panel\n\n"
        f"Business type: "
        f"{owner['niche'] or 'Not specified'}\n"
        f"Services: "
        f"{owner['services_text'] or 'Not specified'}\n\n"
        f"💵 Price range: "
        f"${float(owner['min_price'] or 0):.2f}"
        f" - "
        f"${float(owner['max_price'] or 0):.2f}\n"
        f"⏱ Default delivery: "
        f"{owner['default_days']} days\n"
        f"💳 USDC wallet: "
        f"{'Configured' if wallet_ok else 'Not configured'}\n"
        f"✍️ Signature: {signature_name}\n\n"
        "What you can do here:\n"
        "• Orders — view jobs, mark delivered, resend docs\n"
        "• Business Settings — name, niche, prices\n"
        "• Payments — USDC wallet\n"
        "• Signature — invoice/receipt sign-off"
        f"{next_hint}",
        reply_markup=owner_menu_keyboard(),
    )


# =========================================================
# INITIAL SETUP
# =========================================================

async def setup_start(update, context):

    if not owner_only(update):
        return ConversationHandler.END

    context.user_data["setup"] = {}

    await update.message.reply_text(
        "Owner setup — step 1 of 6\n\n"
        "We'll set your studio name, niche, services, "
        "and pricing. You can change everything later "
        "in Business Settings.\n\n"
        "What is your business name?"
    )

    return SETUP_NAME


async def setup_name(update, context):

    value = update.message.text.strip()

    if not value:
        await update.message.reply_text(
            "Please enter your business name."
        )
        return SETUP_NAME

    context.user_data["setup"]["name"] = value

    await update.message.reply_text(
        "What type of business is this?\n\n"
        "Examples:\n"
        "• Catering\n"
        "• Bakery\n"
        "• Cleaning service\n"
        "• Photography\n"
        "• Graphic design\n"
        "• Construction\n"
        "• Logistics\n"
        "• Consulting\n"
        "• Beauty salon"
    )

    return SETUP_NICHE


async def setup_niche(update, context):

    value = update.message.text.strip()

    if not value:
        await update.message.reply_text(
            "Please enter your business type."
        )
        return SETUP_NICHE

    context.user_data["setup"]["niche"] = value

    await update.message.reply_text(
        "What services or products do you offer?\n\n"
        "List the main things customers can buy."
    )

    return SETUP_SERVICES


async def setup_services(update, context):

    value = update.message.text.strip()

    if not value:
        await update.message.reply_text(
            "Please enter your services or products."
        )
        return SETUP_SERVICES

    context.user_data["setup"]["services"] = value

    await update.message.reply_text(
        "What is your minimum project/order price in USD?"
    )

    return SETUP_MIN_PRICE


async def setup_min_price(update, context):

    try:
        value = float(update.message.text.strip())

        if value <= 0:
            raise ValueError

    except ValueError:
        await update.message.reply_text(
            "Enter a valid number, e.g. 50."
        )
        return SETUP_MIN_PRICE

    context.user_data["setup"]["min_price"] = value

    await update.message.reply_text(
        "What is your maximum project/order price in USD?"
    )

    return SETUP_MAX_PRICE


async def setup_max_price(update, context):

    try:
        value = float(update.message.text.strip())

        if value <= 0:
            raise ValueError

    except ValueError:
        await update.message.reply_text(
            "Enter a valid number, e.g. 1000."
        )
        return SETUP_MAX_PRICE

    context.user_data["setup"]["max_price"] = value

    await update.message.reply_text(
        "What's your standard delivery/fulfillment time in days?"
    )

    return SETUP_DAYS


async def setup_days(update, context):

    try:
        days = int(update.message.text.strip())

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

    business_rules = {
        "pricing": {
            "enabled": True,
            "model": "per_unit",
            "currency": "USD",
            "base_fee": 0.0,
            "unit": {
                "name": "unit",
                "price": data["min_price"],
            },
            "minimum": data["min_price"],
            "maximum": data["max_price"],
            "adjustments": [],
            "owner_approval": {
                "required": True,
                "required_above_maximum": True,
                "required_below_minimum": True,
                "required_for_manual_override": True,
            },
            "rounding": {
                "enabled": False,
                "nearest": 1,
            },
        },

        "buffer_percent": 0,
        "complexity_buffer_percent": 0,
        "complexity_days_buffer": 0,
        "large_quantity_threshold": 20,
        "large_project_days": 0,
        "rush_multiplier": 1.0,
        "quantity_pricing": True,
        "quantity_multiplier_enabled": True,
        "notes": "",
    }

    save_owner(
        telegram_id=OWNER_TELEGRAM_ID,
        name=data["name"],
        niche=data["niche"],
        services_text=data["services"],
        min_price=data["min_price"],
        max_price=data["max_price"],
        default_days=days,
        tone="professional",
        usdc_address="",
        setup_complete=1,
        business_rules=business_rules,
        signature_name="",
        signature_title="",
        signature_image="",
    )

    context.user_data.pop("setup", None)

    await update.message.reply_text(
        "✅ Business setup complete.\n\n"
        f"Business: {data['name']}\n"
        f"Type: {data['niche']}\n"
        f"Services: {data['services']}\n"
        f"Price range: "
        f"${data['min_price']:.2f} - "
        f"${data['max_price']:.2f}\n"
        f"Standard fulfillment: {days} days\n\n"
        "💰 Pricing engine: ACTIVE\n"
        "💳 Payment network: Base\n"
        "🪙 Payment token: USDC\n\n"
        "Finish setup with the buttons below — "
        "no need to send /start again.\n\n"
        "Recommended next: Payments (USDC wallet), "
        "then Signature.",
        reply_markup=owner_menu_keyboard(),
    )

    return ConversationHandler.END


# =========================================================
# CANCEL
# =========================================================

async def cancel_setup(update, context):

    context.user_data.pop("setup", None)
    context.user_data.pop("editing_setting", None)

    await update.message.reply_text(
        "Setup cancelled."
    )

    return ConversationHandler.END


# =========================================================
# BUSINESS SETTINGS
# =========================================================

def settings_keyboard():

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🏢 Business Name",
                    callback_data="edit_name",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🏷️ Business Type",
                    callback_data="edit_niche",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🛠 Services / Products",
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
                    "💳 Base USDC Payments",
                    callback_data="owner_payments",
                ),
            ],
            [
                InlineKeyboardButton(
                    "✍️ Signature",
                    callback_data="owner_signature",
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

    owner = get_owner(OWNER_TELEGRAM_ID)

    if not owner:
        await query.message.reply_text(
            "Run /setup first."
        )
        return

    min_price = float(owner["min_price"] or 0)
    max_price = float(owner["max_price"] or 0)

    await query.message.edit_text(
        "⚙️ Business Settings\n\n"
        f"Business: {owner['name']}\n"
        f"Type: {owner['niche'] or 'Not specified'}\n"
        f"Services: "
        f"{owner['services_text'] or 'Not specified'}\n"
        f"Min price: ${min_price:.2f}\n"
        f"Max price: ${max_price:.2f}\n"
        f"Delivery: {owner['default_days']} days\n\n"
        "Choose what you want to edit.",
        reply_markup=settings_keyboard(),
    )


# =========================================================
# EDIT BUSINESS SETTINGS
# =========================================================

async def edit_name_start(update, context):

    query = update.callback_query
    await query.answer()

    context.user_data["editing_setting"] = "name"

    await query.message.reply_text(
        "Enter the new business name."
    )

    return EDIT_NAME


async def edit_niche_start(update, context):

    query = update.callback_query
    await query.answer()

    context.user_data["editing_setting"] = "niche"

    await query.message.reply_text(
        "Enter the new business type."
    )

    return EDIT_NICHE


async def edit_services_start(update, context):

    query = update.callback_query
    await query.answer()

    context.user_data["editing_setting"] = "services"

    await query.message.reply_text(
        "Enter the services/products you offer."
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
        "Enter the new standard delivery time in days."
    )

    return EDIT_DAYS


async def save_setting_value(update, context):

    value = update.message.text.strip()

    owner = get_owner(OWNER_TELEGRAM_ID)

    if not owner:
        await update.message.reply_text(
            "Business setup was not found. Run /setup."
        )
        return ConversationHandler.END

    setting = context.user_data.get(
        "editing_setting"
    )

    data = {
        "name": owner["name"],
        "niche": owner["niche"],
        "services_text": owner["services_text"],
        "min_price": float(owner["min_price"] or 0),
        "max_price": float(owner["max_price"] or 0),
        "default_days": int(owner["default_days"] or 7),
    }

    if setting == "name":

        if not value:
            await update.message.reply_text(
                "Business name cannot be empty."
            )
            return EDIT_NAME

        data["name"] = value

    elif setting == "niche":

        if not value:
            await update.message.reply_text(
                "Business type cannot be empty."
            )
            return EDIT_NICHE

        data["niche"] = value

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

    else:

        await update.message.reply_text(
            "No setting is currently being edited."
        )

        return ConversationHandler.END

    rules = get_business_rules(
        OWNER_TELEGRAM_ID
    )

    if not isinstance(rules, dict):
        rules = {}

    pricing = rules.get(
        "pricing",
        {},
    )

    if not isinstance(pricing, dict):
        pricing = {}

    pricing["minimum"] = data["min_price"]
    pricing["maximum"] = data["max_price"]

    pricing.setdefault(
        "enabled",
        True,
    )

    pricing.setdefault(
        "model",
        "per_unit",
    )

    pricing.setdefault(
        "currency",
        "USD",
    )

    pricing["unit"] = {
        "name": pricing.get(
            "unit",
            {}
        ).get(
            "name",
            "unit",
        ),
        "price": data["min_price"],
    }

    rules["pricing"] = pricing

    save_owner(
        telegram_id=OWNER_TELEGRAM_ID,
        name=data["name"],
        niche=data["niche"],
        services_text=data["services_text"],
        min_price=data["min_price"],
        max_price=data["max_price"],
        default_days=data["default_days"],
        tone=owner["tone"] or "professional",
        usdc_address=owner["usdc_address"] or "",
        setup_complete=1,
        business_rules=rules,
        signature_name=owner["signature_name"] or "",
        signature_title=owner["signature_title"] or "",
        signature_image=owner["signature_image"] or "",
    )

    context.user_data.pop(
        "editing_setting",
        None,
    )

    await update.message.reply_text(
        "✅ Setting updated.\n\n"
        "💰 Pricing configuration synchronized."
    )

    return ConversationHandler.END


# =========================================================
# PAYMENTS
# =========================================================

def payments_keyboard():

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "💳 Change Base USDC Wallet",
                    callback_data="edit_wallet",
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Business Settings",
                    callback_data="owner_settings",
                )
            ],
            [
                InlineKeyboardButton(
                    "🏠 Owner Menu",
                    callback_data="owner_home",
                )
            ],
        ]
    )


async def payments_menu(update, context):

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

    wallet = owner["usdc_address"] or ""

    if wallet:
        wallet_display = wallet
    else:
        wallet_display = "Not configured"

    await query.message.edit_text(
        "💳 Payment Settings\n\n"
        "Network: Base\n"
        "Token: USDC\n\n"
        f"Wallet address:\n"
        f"{wallet_display}\n\n"
        "Customers will be instructed to send "
        "USDC on Base to this wallet.\n\n"
        "⚠️ Only use a wallet address that you control "
        "and that supports USDC on Base.",
        reply_markup=payments_keyboard(),
    )


async def edit_wallet_start(update, context):

    query = update.callback_query
    await query.answer()

    context.user_data["editing_setting"] = "wallet"

    await query.message.reply_text(
        "💳 Enter your Base USDC wallet address.\n\n"
        "This must be the address that should receive "
        "customer payments on Base.\n\n"
        "Example:\n"
        "0x..."
    )

    return EDIT_WALLET


async def save_wallet(update, context):

    value = update.message.text.strip()

    if not value:
        await update.message.reply_text(
            "Wallet address cannot be empty."
        )
        return EDIT_WALLET

    if not value.startswith("0x"):
        await update.message.reply_text(
            "That does not look like a valid EVM wallet address.\n\n"
            "Base wallet addresses normally start with 0x.\n"
            "Enter it again."
        )
        return EDIT_WALLET

    if len(value) != 42:
        await update.message.reply_text(
            "The wallet address should contain 42 characters "
            "including 0x.\n\n"
            "Enter the Base wallet address again."
        )
        return EDIT_WALLET

    owner = get_owner(
        OWNER_TELEGRAM_ID
    )

    if not owner:
        await update.message.reply_text(
            "Business setup was not found. Run /setup."
        )
        return ConversationHandler.END

    save_owner(
        telegram_id=OWNER_TELEGRAM_ID,
        name=owner["name"],
        niche=owner["niche"],
        services_text=owner["services_text"],
        min_price=float(owner["min_price"] or 0),
        max_price=float(owner["max_price"] or 0),
        default_days=int(owner["default_days"] or 7),
        tone=owner["tone"] or "professional",
        usdc_address=value,
        setup_complete=1,
        business_rules=get_business_rules(
            OWNER_TELEGRAM_ID
        ),
        signature_name=owner["signature_name"] or "",
        signature_title=owner["signature_title"] or "",
        signature_image=owner["signature_image"] or "",
    )

    context.user_data.pop(
        "editing_setting",
        None,
    )

    await update.message.reply_text(
        "✅ Base USDC wallet saved.\n\n"
        f"Wallet:\n{value}\n\n"
        "Customers can now be directed to this wallet "
        "for USDC payments on Base."
    )

    return ConversationHandler.END


# =========================================================
# SIGNATURE
# =========================================================

def signature_keyboard():

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "👤 Signature Name",
                    callback_data="edit_signature_name",
                )
            ],
            [
                InlineKeyboardButton(
                    "💼 Signature Title",
                    callback_data="edit_signature_title",
                )
            ],
            [
                InlineKeyboardButton(
                    "🖼 Signature Image",
                    callback_data="edit_signature_image",
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Business Settings",
                    callback_data="owner_settings",
                )
            ],
            [
                InlineKeyboardButton(
                    "🏠 Owner Menu",
                    callback_data="owner_home",
                )
            ],
        ]
    )


async def signature_menu(update, context):

    query = update.callback_query

    if not owner_only(update):
        await query.answer()
        return

    await query.answer()

    signature = get_owner_signature(
        OWNER_TELEGRAM_ID
    )

    name = (
        signature["signature_name"]
        or "Not configured"
    )

    title = (
        signature["signature_title"]
        or "Not configured"
    )

    image = (
        signature["signature_image"]
        or "Not configured"
    )

    await query.message.edit_text(
        "✍️ Business Signature\n\n"
        f"Name: {name}\n"
        f"Title: {title}\n"
        f"Image: {image}\n\n"
        "The signature can be attached to customer "
        "proposals and business communications.",
        reply_markup=signature_keyboard(),
    )


async def edit_signature_name_start(update, context):

    query = update.callback_query
    await query.answer()

    context.user_data["editing_setting"] = (
        "signature_name"
    )

    await query.message.reply_text(
        "Enter the name that should appear "
        "in your business signature."
    )

    return EDIT_SIGNATURE_NAME


async def edit_signature_title_start(update, context):

    query = update.callback_query
    await query.answer()

    context.user_data["editing_setting"] = (
        "signature_title"
    )

    await query.message.reply_text(
        "Enter your signature title.\n\n"
        "Example:\n"
        "Founder & CEO"
    )

    return EDIT_SIGNATURE_TITLE


async def edit_signature_image_start(update, context):

    query = update.callback_query
    await query.answer()

    context.user_data["editing_setting"] = (
        "signature_image"
    )

    await query.message.reply_text(
        "Send your signature image as a photo.\n\n"
        "The image will be stored as the Telegram "
        "file identifier for later use."
    )

    return EDIT_SIGNATURE_IMAGE


async def save_signature_text(update, context):

    value = update.message.text.strip()

    if not value:
        await update.message.reply_text(
            "This field cannot be empty."
        )

        if context.user_data.get(
            "editing_setting"
        ) == "signature_name":
            return EDIT_SIGNATURE_NAME

        return EDIT_SIGNATURE_TITLE

    owner = get_owner(
        OWNER_TELEGRAM_ID
    )

    if not owner:
        await update.message.reply_text(
            "Business setup was not found. Run /setup."
        )
        return ConversationHandler.END

    setting = context.user_data.get(
        "editing_setting"
    )

    signature_name = (
        owner["signature_name"]
        or ""
    )

    signature_title = (
        owner["signature_title"]
        or ""
    )

    if setting == "signature_name":
        signature_name = value

    elif setting == "signature_title":
        signature_title = value

    else:
        await update.message.reply_text(
            "No signature field is being edited."
        )
        return ConversationHandler.END

    save_owner_signature(
        telegram_id=OWNER_TELEGRAM_ID,
        signature_name=signature_name,
        signature_title=signature_title,
        signature_image=owner["signature_image"] or "",
    )

    context.user_data.pop(
        "editing_setting",
        None,
    )

    await update.message.reply_text(
        "✅ Signature updated."
    )

    return ConversationHandler.END


async def save_signature_image(update, context):

    if not update.message.photo:

        await update.message.reply_text(
            "Please send the signature as a photo."
        )

        return EDIT_SIGNATURE_IMAGE

    photo = update.message.photo[-1]

    file_id = photo.file_id

    owner = get_owner(
        OWNER_TELEGRAM_ID
    )

    if not owner:
        await update.message.reply_text(
            "Business setup was not found."
        )
        return ConversationHandler.END

    save_owner_signature(
        telegram_id=OWNER_TELEGRAM_ID,
        signature_name=owner["signature_name"] or "",
        signature_title=owner["signature_title"] or "",
        signature_image=file_id,
    )

    context.user_data.pop(
        "editing_setting",
        None,
    )

    await update.message.reply_text(
        "✅ Signature image saved."
    )

    return ConversationHandler.END


# =========================================================
# ORDERS LIST
# =========================================================

async def jobs_command(update, context):

    if not owner_only(update):
        return

    jobs = get_all_jobs()

    if update.callback_query:

        await update.callback_query.answer()
        message = update.callback_query.message

    else:

        message = update.message

    if not jobs:

        await message.reply_text(
            "📦 Sovereign Orders\n\n"
            "No orders yet.",
            reply_markup=back_owner_keyboard(),
        )

        return

    buttons = []

    for job in jobs:

        price = float(
            job["quoted_price"] or 0
        )

        price_text = (
            f"${price:.2f}"
            if price
            else "Unquoted"
        )

        paused = (
            " ⏸"
            if job["paused"]
            else ""
        )

        label = (
            f"#{job['id']:04d} "
            f"• {job['client_name'] or 'Client'} "
            f"• {price_text} "
            f"• {job['status']}{paused}"
        )

        buttons.append(
            [
                InlineKeyboardButton(
                    label,
                    callback_data=f"owner_job_{job['id']}",
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                "🏠 Owner Menu",
                callback_data="owner_home",
            )
        ]
    )

    await message.reply_text(
        "📦 Sovereign Orders\n\n"
        "Select an order to view the full details.",
        reply_markup=InlineKeyboardMarkup(
            buttons
        ),
    )


# =========================================================
# SINGLE ORDER VIEW
# =========================================================

def job_detail_keyboard(job):

    job_id = job["id"]
    status = (job["status"] or "").upper()
    payment_status = (job["payment_status"] or "").upper()

    pause_button = (
        InlineKeyboardButton(
            "▶️ Resume Order",
            callback_data=f"resume_job_{job_id}",
        )
        if job["paused"]
        else InlineKeyboardButton(
            "⏸ Pause Order",
            callback_data=f"pause_job_{job_id}",
        )
    )

    rows = [[pause_button]]

    if payment_status == "CONFIRMED" or status == "PAID":
        rows.append(
            [
                InlineKeyboardButton(
                    "✅ Mark Delivered",
                    callback_data=f"deliver_job_{job_id}",
                )
            ]
        )

    if status == "DELIVERED":
        rows.append(
            [
                InlineKeyboardButton(
                    "🔒 Close Order",
                    callback_data=f"close_job_{job_id}",
                )
            ]
        )

    if job["receipt_file"] or job["invoice_file"]:
        doc_row = []
        if job["receipt_file"]:
            doc_row.append(
                InlineKeyboardButton(
                    "📄 Receipt",
                    callback_data=f"resend_receipt_{job_id}",
                )
            )
        if job["invoice_file"]:
            doc_row.append(
                InlineKeyboardButton(
                    "🧾 Invoice",
                    callback_data=f"resend_invoice_{job_id}",
                )
            )
        if doc_row:
            rows.append(doc_row)

    rows.append(
        [
            InlineKeyboardButton(
                "📦 All Orders",
                callback_data="owner_jobs",
            ),
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                "🏠 Owner Menu",
                callback_data="owner_home",
            )
        ]
    )

    return InlineKeyboardMarkup(rows)


def format_job_details(job):

    price = float(
        job["quoted_price"] or 0
    )

    price_text = (
        f"${price:.2f} {job['currency'] or 'USD'}"
        if price
        else "Not quoted"
    )

    paused = (
        "⏸ YES"
        if job["paused"]
        else "NO"
    )

    answers_text = job["answers"] or "{}"

    proposal = (
        job["proposal_text"]
        or "No proposal generated."
    )

    notes = (
        job["notes"]
        or "No owner notes."
    )

    complexity = (
        job["complexity"]
        or "Not analyzed"
    )

    cushion = (
        job["cushion_applied"]
        or "None"
    )

    analysis = (
        job["internal_analysis"]
        or "No internal analysis."
    )

    return (
        f"📦 ORDER #{job['id']:04d}\n\n"

        f"👤 CLIENT\n"
        f"Name: {job['client_name'] or 'Unknown'}\n"
        f"Telegram ID: {job['client_telegram_id']}\n\n"

        f"📊 STATUS\n"
        f"Status: {job['status']}\n"
        f"Paused: {paused}\n\n"

        f"💰 PAYMENT / QUOTE\n"
        f"Price: {price_text}\n"
        f"Payment status: {job['payment_status'] or 'UNPAID'}\n"
        f"TX: {job['payment_tx_hash'] or '—'}\n"
        f"Deadline: {job['deadline'] or 'Not set'}\n\n"

        f"🧠 ANALYSIS\n"
        f"Complexity: {complexity}\n"
        f"Cushion: {cushion}\n"
        f"Internal analysis:\n"
        f"{analysis}\n\n"

        f"📝 CUSTOMER ANSWERS\n"
        f"{answers_text}\n\n"

        f"📄 PROPOSAL\n"
        f"{proposal}\n\n"

        f"📌 OWNER NOTES\n"
        f"{notes}\n\n"

        f"🕐 CREATED\n"
        f"{job['created_at']}\n\n"

        f"🕐 UPDATED\n"
        f"{job['updated_at']}"
    )


async def owner_job_detail(update, context):

    query = update.callback_query

    if not owner_only(update):
        await query.answer()
        return

    await query.answer()

    try:
        job_id = int(
            query.data.replace(
                "owner_job_",
                "",
            )
        )

    except ValueError:

        await query.message.reply_text(
            "Invalid order."
        )

        return

    job = get_job(job_id)

    if not job:

        await query.message.reply_text(
            f"Order #{job_id} was not found."
        )

        return

    await query.message.edit_text(
        format_job_details(job),
        reply_markup=job_detail_keyboard(job),
    )


# =========================================================
# PAUSE / RESUME CALLBACKS
# =========================================================

async def pause_job_callback(update, context):

    query = update.callback_query

    if not owner_only(update):
        await query.answer()
        return

    await query.answer()

    try:
        job_id = int(
            query.data.replace(
                "pause_job_",
                "",
            )
        )

    except ValueError:
        return

    job = get_job(job_id)

    if not job:
        await query.message.reply_text(
            "Order not found."
        )
        return

    set_job_paused(
        job_id,
        True,
    )

    job = get_job(job_id)

    await query.message.edit_text(
        format_job_details(job),
        reply_markup=job_detail_keyboard(job),
    )


async def resume_job_callback(update, context):

    query = update.callback_query

    if not owner_only(update):
        await query.answer()
        return

    await query.answer()

    try:
        job_id = int(
            query.data.replace(
                "resume_job_",
                "",
            )
        )

    except ValueError:
        return

    job = get_job(job_id)

    if not job:
        await query.message.reply_text(
            "Order not found."
        )
        return

    set_job_paused(
        job_id,
        False,
    )

    job = get_job(job_id)

    await query.message.edit_text(
        format_job_details(job),
        reply_markup=job_detail_keyboard(job),
    )


# =========================================================
# MARK DELIVERED / CLOSE / RESEND DOCS
# =========================================================

async def deliver_job_callback(update, context):

    query = update.callback_query

    if not owner_only(update):
        await query.answer()
        return

    await query.answer()

    try:
        job_id = int(query.data.replace("deliver_job_", ""))
    except ValueError:
        return

    job = get_job(job_id)

    if not job:
        await query.message.reply_text("Order not found.")
        return

    status = (job["status"] or "").upper()
    payment_status = (job["payment_status"] or "").upper()

    if payment_status != "CONFIRMED" and status != "PAID":
        await query.message.reply_text(
            "This order is not paid yet. "
            "Deliver only after payment is confirmed."
        )
        return

    set_job_status(job_id, "DELIVERED")
    job = get_job(job_id)

    try:
        await context.bot.send_message(
            chat_id=job["client_telegram_id"],
            text=(
                f"✅ Your project #{job_id} has been marked as delivered.\n\n"
                "If anything is missing, reply here and the studio will help."
            ),
        )
    except Exception:
        pass

    await query.message.edit_text(
        format_job_details(job),
        reply_markup=job_detail_keyboard(job),
    )


async def close_job_callback(update, context):

    query = update.callback_query

    if not owner_only(update):
        await query.answer()
        return

    await query.answer()

    try:
        job_id = int(query.data.replace("close_job_", ""))
    except ValueError:
        return

    job = get_job(job_id)

    if not job:
        await query.message.reply_text("Order not found.")
        return

    set_job_status(job_id, "CLOSED")
    job = get_job(job_id)

    await query.message.edit_text(
        format_job_details(job),
        reply_markup=job_detail_keyboard(job),
    )


async def resend_receipt_callback(update, context):

    query = update.callback_query

    if not owner_only(update):
        await query.answer()
        return

    await query.answer()

    try:
        job_id = int(query.data.replace("resend_receipt_", ""))
    except ValueError:
        return

    path = get_receipt_file(job_id)

    if not path:
        await query.message.reply_text(
            "No receipt file is saved for this order yet."
        )
        return

    try:
        with open(path, "rb") as f:
            await query.message.reply_document(
                document=f,
                filename=f"Receipt_SB-{int(job_id):04d}.pdf",
                caption=f"📄 Receipt for Project #{job_id}",
            )
    except Exception as error:
        await query.message.reply_text(
            f"Could not send the receipt.\n\nError: {error}"
        )


async def resend_invoice_callback(update, context):

    query = update.callback_query

    if not owner_only(update):
        await query.answer()
        return

    await query.answer()

    try:
        job_id = int(query.data.replace("resend_invoice_", ""))
    except ValueError:
        return

    path = get_invoice_file(job_id)

    if not path:
        await query.message.reply_text(
            "No invoice file is saved for this order yet."
        )
        return

    try:
        with open(path, "rb") as f:
            await query.message.reply_document(
                document=f,
                filename=f"Invoice_SB-{int(job_id):04d}.pdf",
                caption=f"🧾 Invoice for Project #{job_id}",
            )
    except Exception as error:
        await query.message.reply_text(
            f"Could not send the invoice.\n\nError: {error}"
        )


# =========================================================
# COMMAND: /job
# =========================================================

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

    await update.message.reply_text(
        format_job_details(job),
        reply_markup=job_detail_keyboard(job),
    )


# =========================================================
# COMMAND: /pause
# =========================================================

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
        f"⏸ Order #{job_id:04d} is now paused."
    )


# =========================================================
# COMMAND: /resume
# =========================================================

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
        f"▶️ Order #{job_id:04d} has been resumed."
    )