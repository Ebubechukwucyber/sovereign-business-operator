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
    "llama-3.1-8b-instant",
).strip()


# =========================================================
# DATABASE
# =========================================================

DATABASE_PATH = os.getenv(
    "DATABASE_PATH",
    "sovereign.db",
).strip()


# =========================================================
# BASE SEPOLIA / USDC TESTNET
# =========================================================
#
# DEVELOPMENT NETWORK
#
# We are testing payments on Base Sepolia first.
#
# Base Sepolia:
# Chain ID = 84532
#
# DO NOT use the production Base network while testing.
#


BASE_SEPOLIA_CHAIN_ID = int(
    os.getenv(
        "BASE_SEPOLIA_CHAIN_ID",
        "84532",
    )
)


# =========================================================
# BASE SEPOLIA RPC
# =========================================================
#
# Default Base Sepolia public RPC.
#
# You can replace this in .env with another RPC provider
# later if needed.
#

BASE_SEPOLIA_RPC_URL = os.getenv(
    "BASE_SEPOLIA_RPC_URL",
    "https://sepolia.base.org",
).strip()


# =========================================================
# USDC CONTRACT
# =========================================================
#
# IMPORTANT:
#
# This MUST be the USDC TOKEN CONTRACT on Base Sepolia.
#
# It is NOT the business owner's receiving wallet.
#
# The owner's receiving wallet is stored separately in the
# database as the business payment wallet.
#
# Put the correct Base Sepolia USDC contract in .env:
#
# BASE_SEPOLIA_USDC_CONTRACT=...
#
# We deliberately do not hard-code an unknown contract
# address here.
#

BASE_SEPOLIA_USDC_CONTRACT = os.getenv(
    "BASE_SEPOLIA_USDC_CONTRACT",
    "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
).strip()


# =========================================================
# PAYMENT NETWORK
# =========================================================
#
# This is what the client sees on the payment page.
#

PAYMENT_NETWORK = os.getenv(
    "PAYMENT_NETWORK",
    "Base Sepolia",
).strip()


# =========================================================
# PAYMENT TOKEN
# =========================================================
#

PAYMENT_TOKEN = os.getenv(
    "PAYMENT_TOKEN",
    "USDC",
).strip()


# =========================================================
# REQUIRED CONFIRMATIONS
# =========================================================
#
# During testing we require 2 confirmations.
#
# Example:
#
# Transaction is included in block 100.
# Latest block is 101.
#
# confirmations =
# 101 - 100 + 1
# = 2
#
# Once the required number is reached, the payment can
# be considered confirmed.
#

BASE_SEPOLIA_CONFIRMATIONS = int(
    os.getenv(
        "BASE_SEPOLIA_CONFIRMATIONS",
        "2",
    )
)


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
# BLOCKCHAIN EXPLORER
# =========================================================
#
# Base Sepolia explorer.
#
# This is useful for putting a clickable transaction link
# inside the receipt.
#

BASE_SEPOLIA_EXPLORER_URL = os.getenv(
    "BASE_SEPOLIA_EXPLORER_URL",
    "https://sepolia.basescan.org",
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

    if BASE_SEPOLIA_CHAIN_ID != 84532:
        errors.append(
            "BASE_SEPOLIA_CHAIN_ID must be 84532 "
            "while using Base Sepolia."
        )

    if not BASE_SEPOLIA_RPC_URL:
        errors.append(
            "BASE_SEPOLIA_RPC_URL is not configured."
        )

    if not BASE_SEPOLIA_USDC_CONTRACT:
        errors.append(
            "BASE_SEPOLIA_USDC_CONTRACT is not configured."
        )

    if not PAYMENT_NETWORK:
        errors.append(
            "PAYMENT_NETWORK is not configured."
        )

    if not PAYMENT_TOKEN:
        errors.append(
            "PAYMENT_TOKEN is not configured."
        )

    if BASE_SEPOLIA_CONFIRMATIONS < 1:
        errors.append(
            "BASE_SEPOLIA_CONFIRMATIONS must be at least 1."
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