import os

from dotenv import load_dotenv


load_dotenv()


# =========================================================
# TELEGRAM
# =========================================================

TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
    "",
).strip()


TELEGRAM_BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "").strip().lstrip("@")

OWNER_TELEGRAM_ID = int(
    os.getenv(
        "OWNER_TELEGRAM_ID",
        "0",
    )
)


# =========================================================
# LLM
# =========================================================

LLM_API_KEY = os.getenv(
    "LLM_API_KEY",
    "",
).strip()


LLM_BASE_URL = os.getenv(
    "LLM_BASE_URL",
    "https://api.groq.com/openai/v1",
).strip()


LLM_MODEL = os.getenv(
    "LLM_MODEL",
    # Groq free tier — fast & widely available
    "openai/gpt-oss-20b",
).strip()


# =========================================================
# DATABASE
# =========================================================

DATABASE_PATH = os.getenv(
    "DATABASE_PATH",
    "sovereign.db",
).strip()


# =========================================================
# BASE + USDC PAYMENT NETWORK
# =========================================================
#
# Default: Base MAINNET (required for production / hackathon
# mainnet submissions).
#
# Base mainnet chain id: 8453
# Official Circle USDC on Base:
#   0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
#
# Optional testnet: set env to Sepolia values
# (chain 84532, sepolia RPC, sepolia USDC).
#
# The owner's RECEIVING WALLET is stored in the database
# (Payments settings). It is NOT the USDC contract below.
#

BASE_CHAIN_ID = int(
    os.getenv(
        "BASE_CHAIN_ID",
        os.getenv("BASE_SEPOLIA_CHAIN_ID", "8453"),
    )
)

BASE_RPC_URL = os.getenv(
    "BASE_RPC_URL",
    os.getenv(
        "BASE_SEPOLIA_RPC_URL",
        "https://mainnet.base.org",
    ),
).strip()

# Circle native USDC on Base mainnet
BASE_USDC_CONTRACT = os.getenv(
    "BASE_USDC_CONTRACT",
    os.getenv(
        "BASE_SEPOLIA_USDC_CONTRACT",
        "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    ),
).strip()

BASE_CONFIRMATIONS = int(
    os.getenv(
        "BASE_CONFIRMATIONS",
        os.getenv("BASE_SEPOLIA_CONFIRMATIONS", "3"),
    )
)

BASE_EXPLORER_URL = os.getenv(
    "BASE_EXPLORER_URL",
    os.getenv(
        "BASE_SEPOLIA_EXPLORER_URL",
        "https://basescan.org",
    ),
).strip()

# Back-compat aliases used by payment_verifier.py
BASE_SEPOLIA_CHAIN_ID = BASE_CHAIN_ID
BASE_SEPOLIA_RPC_URL = BASE_RPC_URL
BASE_SEPOLIA_USDC_CONTRACT = BASE_USDC_CONTRACT
BASE_SEPOLIA_CONFIRMATIONS = BASE_CONFIRMATIONS
BASE_SEPOLIA_EXPLORER_URL = BASE_EXPLORER_URL


# =========================================================
# PAYMENT NETWORK (client-facing label)
# =========================================================

PAYMENT_NETWORK = os.getenv(
    "PAYMENT_NETWORK",
    "Base",
).strip()


# =========================================================
# PAYMENT TOKEN
# =========================================================

PAYMENT_TOKEN = os.getenv(
    "PAYMENT_TOKEN",
    "USDC",
).strip()


# Maximum age of a payment transaction, in seconds.
# Older hashes are rejected to prevent recycling an
# earlier payment for a new job.
PAYMENT_MAX_AGE_SECONDS = int(
    os.getenv(
        "PAYMENT_MAX_AGE_SECONDS",
        "7200",
    )
)


# =========================================================
# PAYMENT VERIFICATION
# =========================================================
#
# This MUST remain enabled for the payment flow.
#
# The bot must NOT trust a TX hash merely because the client
# submitted one.
#
# The verifier checks:
#
# 1. TX hash format
# 2. Correct blockchain network
# 3. Transaction exists
# 4. Transaction is mined
# 5. Transaction succeeded
# 6. Required confirmations
# 7. Correct USDC contract
# 8. Correct receiving wallet
# 9. Correct payment amount
#

PAYMENT_VERIFICATION_ENABLED = os.getenv(
    "PAYMENT_VERIFICATION_ENABLED",
    "true",
).strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)


# =========================================================
# PAYMENT RECEIPTS
# =========================================================
#
# Once blockchain verification succeeds, the system will
# generate a professional payment receipt/invoice PDF.
#

PAYMENT_RECEIPT_ENABLED = os.getenv(
    "PAYMENT_RECEIPT_ENABLED",
    "true",
).strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)


# =========================================================
# PAYMENT STATUS
# =========================================================
#
# These are configuration constants used by the payment
# workflow so we don't have random status strings scattered
# throughout the project.
#

PAYMENT_STATUS_PENDING = "PAYMENT_PENDING"

PAYMENT_STATUS_VERIFIED = "PAID"

PAYMENT_STATUS_FAILED = "PAYMENT_FAILED"


# =========================================================
# RECEIPT SETTINGS
# =========================================================
#
# Prefix used when generating payment receipt numbers.
#

PAYMENT_RECEIPT_PREFIX = os.getenv(
    "PAYMENT_RECEIPT_PREFIX",
    "RCPT",
).strip()


# =========================================================
# APPLICATION
# =========================================================

APP_NAME = os.getenv(
    "APP_NAME",
    "Sovereign Business Operator",
).strip()


APP_ENV = os.getenv(
    "APP_ENV",
    "development",
).strip()


# =========================================================
# DEBUG
# =========================================================
#
# Keep this TRUE while we're testing.
#
# Set to false when moving to production.
#

DEBUG = os.getenv(
    "DEBUG",
    "true",
).strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)


# =========================================================
# VALIDATION
# =========================================================

def validate_payment_config():
    """
    Validate the blockchain payment configuration.

    This does not contact the blockchain.
    It only checks that the required configuration values
    exist and have sensible values.
    """

    errors = []

    if BASE_CHAIN_ID not in (8453, 84532):
        errors.append(
            "BASE_CHAIN_ID must be 8453 (Base mainnet) "
            "or 84532 (Base Sepolia)."
        )

    if not BASE_RPC_URL:
        errors.append(
            "BASE_RPC_URL is not configured."
        )

    if not BASE_USDC_CONTRACT:
        errors.append(
            "BASE_USDC_CONTRACT is not configured."
        )

    if not PAYMENT_NETWORK:
        errors.append(
            "PAYMENT_NETWORK is not configured."
        )

    if not PAYMENT_TOKEN:
        errors.append(
            "PAYMENT_TOKEN is not configured."
        )

    if BASE_CONFIRMATIONS < 1:
        errors.append(
            "BASE_CONFIRMATIONS must be at least 1."
        )

    return errors


# =========================================================
# OPTIONAL STARTUP CHECK
# =========================================================
#
# We intentionally do not raise an exception here.
#
# This allows the bot to start even if payment configuration
# is temporarily incomplete, while the payment page can
# report that payment configuration is unavailable.
#

PAYMENT_CONFIG_ERRORS = validate_payment_config()

# =========================================================
# OPTIONAL EMAIL NOTIFY (after payment confirmed)
# =========================================================
# Set these on Railway to email the owner a paid-order summary.
# Uses standard library smtplib — no extra packages.

OWNER_NOTIFY_EMAIL = os.getenv("OWNER_NOTIFY_EMAIL", "").strip()
SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER or "").strip()

# Resend (preferred for hackathon / Railway)
EMAIL_ENABLED = os.getenv("EMAIL_ENABLED", "true").strip().lower() in (
    "1", "true", "yes", "on",
)
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
EMAIL_FROM = os.getenv(
    "EMAIL_FROM",
    SMTP_FROM or "onboarding@resend.dev",
).strip()
