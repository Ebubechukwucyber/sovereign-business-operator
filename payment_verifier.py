"""
Base Sepolia USDC payment verification.

TESTNET PAYMENT INFRASTRUCTURE

This module NEVER trusts a client-provided payment amount.

It verifies on-chain:

1. Transaction exists.
2. Transaction succeeded.
3. Required token contract was used.
4. USDC Transfer event exists.
5. Tokens were sent to the owner's configured wallet.
6. Amount is sufficient.
7. Required confirmations exist.

Network:
    Base Sepolia

Token:
    USDC

This file is intentionally self-contained and uses
standard Python libraries only.
"""

from __future__ import annotations

import json
import re
import time
from decimal import Decimal, InvalidOperation
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from config import (
    BASE_SEPOLIA_RPC_URL,
    BASE_SEPOLIA_CHAIN_ID,
    BASE_SEPOLIA_USDC_CONTRACT,
    BASE_SEPOLIA_CONFIRMATIONS,
    PAYMENT_MAX_AGE_SECONDS,
)


# =========================================================
# CONSTANTS
# =========================================================

USDC_DECIMALS = 6

# ERC-20 Transfer(address,address,uint256)
TRANSFER_EVENT_SIGNATURE = (
    "0xddf252ad1be2c89b69c2b068fc378"
    "daa952ba7f163c4a11628f55a4df523b3ef"
)

TX_HASH_PATTERN = re.compile(
    r"^0x[a-fA-F0-9]{64}$"
)

ADDRESS_PATTERN = re.compile(
    r"^0x[a-fA-F0-9]{40}$"
)


# =========================================================
# RPC
# =========================================================

def rpc_call(
    method,
    params=None,
):
    """
    Execute a JSON-RPC request against Base Sepolia.
    """

    if params is None:
        params = []

    rpc_url = str(
        BASE_SEPOLIA_RPC_URL or ""
    ).strip()

    if not rpc_url:
        raise RuntimeError(
            "BASE_SEPOLIA_RPC_URL is not configured."
        )

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params,
    }

    data = json.dumps(
        payload
    ).encode("utf-8")

    request = Request(
        rpc_url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": (
                "SovereignBusinessOperator/1.0"
            ),
        },
        method="POST",
    )

    try:

        with urlopen(
            request,
            timeout=20,
        ) as response:

            raw = response.read()

    except (
        HTTPError,
        URLError,
        TimeoutError,
    ) as exc:

        raise RuntimeError(
            "Base Sepolia RPC request failed: "
            f"{exc}"
        ) from exc

    try:

        result = json.loads(
            raw.decode("utf-8")
        )

    except (
        TypeError,
        ValueError,
    ) as exc:

        raise RuntimeError(
            "Invalid JSON returned by "
            "Base Sepolia RPC."
        ) from exc

    if result.get("error"):

        raise RuntimeError(
            str(
                result["error"]
            )
        )

    return result.get(
        "result"
    )


# =========================================================
# VALIDATION
# =========================================================

def normalize_address(address):
    """
    Normalize an Ethereum address for comparison.
    """

    return str(
        address or ""
    ).strip().lower()


def validate_tx_hash(tx_hash):
    """
    Validate an EVM transaction hash.

    Expected:

        0x + 64 hexadecimal characters
    """

    tx_hash = str(
        tx_hash or ""
    ).strip()

    return bool(
        TX_HASH_PATTERN.fullmatch(
            tx_hash
        )
    )


def validate_address(address):
    """
    Validate an EVM wallet or contract address.
    """

    address = str(
        address or ""
    ).strip()

    return bool(
        ADDRESS_PATTERN.fullmatch(
            address
        )
    )


# =========================================================
# HEX HELPERS
# =========================================================

def hex_to_int(value):
    """
    Convert a hexadecimal RPC value to an integer.
    """

    if value is None:
        return 0

    try:

        return int(
            str(value),
            16,
        )

    except (
        TypeError,
        ValueError,
    ):

        return 0


def topic_to_address(topic):
    """
    Convert an indexed Ethereum address topic
    into a normal 20-byte address.

    Ethereum indexed addresses are stored as
    32-byte topics with leading zero padding.
    """

    topic = str(
        topic or ""
    ).strip()

    if topic.startswith("0x"):
        topic = topic[2:]

    if len(topic) != 64:
        return ""

    return (
        "0x"
        + topic[-40:]
    ).lower()


def data_to_amount(data):
    """
    Convert ERC-20 Transfer event data into
    the raw uint256 token amount.
    """

    data = str(
        data or ""
    ).strip()

    if data.startswith("0x"):
        data = data[2:]

    if not data:
        return 0

    try:

        return int(
            data,
            16,
        )

    except (
        TypeError,
        ValueError,
    ):

        return 0


# =========================================================
# USDC AMOUNT HELPERS
# =========================================================

def usdc_to_units(amount):
    """
    Convert human-readable USDC to smallest units.

    Example:

        10.50 USDC
        ->
        10500000 units

    USDC uses 6 decimal places.
    """

    try:

        decimal_amount = Decimal(
            str(amount)
        )

    except (
        InvalidOperation,
        TypeError,
        ValueError,
    ):

        raise ValueError(
            "Invalid USDC amount."
        )

    if decimal_amount < 0:

        raise ValueError(
            "USDC amount cannot be negative."
        )

    scaled = (
        decimal_amount
        * (
            Decimal(10)
            ** USDC_DECIMALS
        )
    )

    # Never silently truncate a payment amount.
    if (
        scaled
        != scaled.to_integral_value()
    ):

        raise ValueError(
            "USDC amount has too many "
            "decimal places."
        )

    return int(
        scaled
    )


def units_to_usdc(units):
    """
    Convert smallest USDC units into
    human-readable USDC.
    """

    try:

        return (
            Decimal(
                int(units)
            )
            / (
                Decimal(10)
                ** USDC_DECIMALS
            )
        )

    except (
        TypeError,
        ValueError,
        InvalidOperation,
    ):

        return Decimal("0")


# =========================================================
# CHAIN
# =========================================================

def get_chain_id():
    """
    Return the connected blockchain chain ID.
    """

    result = rpc_call(
        "eth_chainId"
    )

    return hex_to_int(
        result
    )


def verify_chain():
    """
    Make sure the configured RPC is actually
    connected to Base Sepolia.
    """

    chain_id = get_chain_id()

    if chain_id != int(
        BASE_SEPOLIA_CHAIN_ID
    ):

        raise RuntimeError(
            "RPC endpoint is not Base Sepolia. "
            f"Expected chain ID "
            f"{BASE_SEPOLIA_CHAIN_ID}, "
            f"got {chain_id}."
        )

    return True


# =========================================================
# BLOCK
# =========================================================

def get_latest_block_number():
    """
    Return the latest Base Sepolia block number.
    """

    result = rpc_call(
        "eth_blockNumber"
    )

    return hex_to_int(
        result
    )


def get_block_timestamp(block_number):
    """
    Return the Unix timestamp for a block.
    """

    if not block_number:
        return 0

    result = rpc_call(
        "eth_getBlockByNumber",
        [
            hex(int(block_number)),
            False,
        ],
    )

    if not result:
        return 0

    return hex_to_int(
        result.get(
            "timestamp",
            "0x0",
        )
    )


# =========================================================
# TRANSACTION
# =========================================================

def get_transaction(
    tx_hash,
):
    """
    Get a transaction by hash.
    """

    return rpc_call(
        "eth_getTransactionByHash",
        [
            tx_hash
        ],
    )


def get_transaction_receipt(
    tx_hash,
):
    """
    Get a transaction receipt by hash.
    """

    return rpc_call(
        "eth_getTransactionReceipt",
        [
            tx_hash
        ],
    )


# =========================================================
# TRANSFER LOGS
# =========================================================

def find_usdc_transfers(
    receipt,
):
    """
    Find USDC Transfer events emitted by the
    configured Base Sepolia USDC contract.

    Returns a list like:

        [
            {
                "token_contract": "...",
                "from": "...",
                "to": "...",
                "amount_units": 10000000,
                "amount_usdc": "10",
                "log_index": 5,
            }
        ]
    """

    transfers = []

    if not receipt:
        return transfers

    logs = receipt.get(
        "logs",
        [],
    )

    configured_contract = normalize_address(
        BASE_SEPOLIA_USDC_CONTRACT
    )

    if not configured_contract:
        return transfers

    for log in logs:

        # -------------------------------------------------
        # CONTRACT
        # -------------------------------------------------

        address = normalize_address(
            log.get(
                "address",
                "",
            )
        )

        if address != configured_contract:
            continue

        # -------------------------------------------------
        # TOPICS
        # -------------------------------------------------

        topics = log.get(
            "topics",
            [],
        )

        if len(topics) < 3:
            continue

        # -------------------------------------------------
        # EVENT SIGNATURE
        # -------------------------------------------------

        event_signature = str(
            topics[0]
        ).lower()

        if (
            event_signature
            != TRANSFER_EVENT_SIGNATURE
        ):
            continue

        # -------------------------------------------------
        # FROM
        # -------------------------------------------------

        sender = topic_to_address(
            topics[1]
        )

        # -------------------------------------------------
        # TO
        # -------------------------------------------------

        recipient = topic_to_address(
            topics[2]
        )

        if not sender or not recipient:
            continue

        # -------------------------------------------------
        # AMOUNT
        # -------------------------------------------------

        amount_units = data_to_amount(
            log.get(
                "data",
                "0x0",
            )
        )

        # -------------------------------------------------
        # SAVE
        # -------------------------------------------------

        transfers.append(
            {
                "token_contract": address,
                "from": sender,
                "to": recipient,
                "amount_units": amount_units,
                "amount_usdc": str(
                    units_to_usdc(
                        amount_units
                    )
                ),
                "log_index": hex_to_int(
                    log.get(
                        "logIndex",
                        "0x0",
                    )
                ),
            }
        )

    return transfers


# =========================================================
# PAYMENT VERIFICATION
# =========================================================

def verify_usdc_payment(
    tx_hash,
    recipient_address,
    expected_amount,
    min_timestamp=0,
    max_age_seconds=None,
):
    """
    Verify a Base Sepolia USDC payment.

    IMPORTANT:

    The expected amount comes from the server/database.
    The client-provided amount is NEVER trusted.

    Verification checks:

    1. Transaction hash format.
    2. Recipient wallet format.
    3. USDC contract configuration.
    4. Base Sepolia network.
    5. Transaction existence.
    6. Transaction mining.
    7. Transaction success.
    8. Required confirmations.
    9. Correct USDC contract.
    10. USDC Transfer event.
    11. Correct recipient.
    12. Sufficient payment amount.

    Returns a dictionary suitable for saving
    in the jobs table.
    """

    tx_hash = str(
        tx_hash or ""
    ).strip()

    recipient_address = normalize_address(
        recipient_address
    )

    # =====================================================
    # BASIC VALIDATION
    # =====================================================

    if not validate_tx_hash(
        tx_hash
    ):

        return {
            "success": False,
            "confirmed": False,
            "status": "INVALID_TX_HASH",
            "reason": (
                "Invalid transaction hash."
            ),
        }

    if not validate_address(
        recipient_address
    ):

        return {
            "success": False,
            "confirmed": False,
            "status": "INVALID_RECIPIENT",
            "reason": (
                "Invalid recipient wallet address."
            ),
        }

    if not validate_address(
        BASE_SEPOLIA_USDC_CONTRACT
    ):

        return {
            "success": False,
            "confirmed": False,
            "status": "CONFIG_ERROR",
            "reason": (
                "Base Sepolia USDC contract "
                "is not configured correctly."
            ),
        }

    # =====================================================
    # EXPECTED AMOUNT
    # =====================================================

    try:

        expected_units = usdc_to_units(
            expected_amount
        )

    except ValueError as exc:

        return {
            "success": False,
            "confirmed": False,
            "status": "INVALID_AMOUNT",
            "reason": str(exc),
        }

    if expected_units <= 0:

        return {
            "success": False,
            "confirmed": False,
            "status": "INVALID_AMOUNT",
            "reason": (
                "Expected payment amount "
                "must be greater than zero."
            ),
        }

    # =====================================================
    # CHAIN CHECK
    # =====================================================

    try:

        verify_chain()

    except Exception as exc:

        return {
            "success": False,
            "confirmed": False,
            "status": "WRONG_NETWORK",
            "reason": str(exc),
        }

    # =====================================================
    # TRANSACTION
    # =====================================================

    try:

        transaction = get_transaction(
            tx_hash
        )

    except Exception as exc:

        return {
            "success": False,
            "confirmed": False,
            "status": "RPC_ERROR",
            "reason": str(exc),
            "tx_hash": tx_hash,
        }

    if not transaction:

        return {
            "success": False,
            "confirmed": False,
            "status": "NOT_FOUND",
            "reason": (
                "Transaction was not found "
                "on Base Sepolia."
            ),
            "tx_hash": tx_hash,
        }

    # =====================================================
    # RECEIPT
    # =====================================================

    try:

        receipt = get_transaction_receipt(
            tx_hash
        )

    except Exception as exc:

        return {
            "success": False,
            "confirmed": False,
            "status": "RPC_ERROR",
            "reason": str(exc),
            "tx_hash": tx_hash,
        }

    if not receipt:

        return {
            "success": False,
            "confirmed": False,
            "status": "PENDING",
            "reason": (
                "Transaction exists but has not "
                "been mined yet."
            ),
            "tx_hash": tx_hash,
        }

    # =====================================================
    # TRANSACTION STATUS
    # =====================================================

    receipt_status = hex_to_int(
        receipt.get(
            "status",
            "0x0",
        )
    )

    if receipt_status != 1:

        return {
            "success": False,
            "confirmed": False,
            "status": "FAILED",
            "reason": (
                "The transaction failed "
                "on-chain."
            ),
            "tx_hash": tx_hash,
        }

    # =====================================================
    # TRANSACTION BLOCK
    # =====================================================

    transaction_block = hex_to_int(
        receipt.get(
            "blockNumber",
            "0x0",
        )
    )

    if transaction_block <= 0:

        return {
            "success": False,
            "confirmed": False,
            "status": "PENDING",
            "reason": (
                "The transaction does not have "
                "a valid block number yet."
            ),
            "tx_hash": tx_hash,
        }

    # =====================================================
    # TIME WINDOW
    # =====================================================
    #
    # Reject recycled old payments and hashes that
    # predate the quote / payment instructions.
    #

    try:
        tx_timestamp = get_block_timestamp(
            transaction_block
        )
    except Exception as exc:
        return {
            "success": False,
            "confirmed": False,
            "status": "RPC_ERROR",
            "reason": str(exc),
            "tx_hash": tx_hash,
        }

    now_ts = int(time.time())

    if max_age_seconds is None:
        try:
            max_age_seconds = int(
                PAYMENT_MAX_AGE_SECONDS
            )
        except (TypeError, ValueError):
            max_age_seconds = 7200

    if max_age_seconds < 60:
        max_age_seconds = 60

    if tx_timestamp <= 0:
        return {
            "success": False,
            "confirmed": False,
            "status": "MISSING_TIMESTAMP",
            "reason": (
                "Could not read the transaction "
                "block timestamp."
            ),
            "tx_hash": tx_hash,
        }

    if tx_timestamp > now_ts + 120:
        return {
            "success": False,
            "confirmed": False,
            "status": "TX_IN_FUTURE",
            "reason": (
                "Transaction timestamp is in the future."
            ),
            "tx_hash": tx_hash,
            "tx_timestamp": tx_timestamp,
        }

    if tx_timestamp < now_ts - int(max_age_seconds):
        return {
            "success": False,
            "confirmed": False,
            "status": "TX_TOO_OLD",
            "reason": (
                "This transaction is too old to count "
                "for this payment. Send a new USDC "
                "transfer after the quote is issued."
            ),
            "tx_hash": tx_hash,
            "tx_timestamp": tx_timestamp,
            "max_age_seconds": int(max_age_seconds),
        }

    try:
        min_timestamp = int(min_timestamp or 0)
    except (TypeError, ValueError):
        min_timestamp = 0

    # 60s grace for clock / block-time skew
    if min_timestamp and tx_timestamp < (min_timestamp - 60):
        return {
            "success": False,
            "confirmed": False,
            "status": "TX_TOO_EARLY",
            "reason": (
                "This transaction was mined before "
                "payment was requested for this job. "
                "An older payment cannot be reused."
            ),
            "tx_hash": tx_hash,
            "tx_timestamp": tx_timestamp,
            "min_timestamp": min_timestamp,
        }

    # =====================================================
    # LATEST BLOCK
    # =====================================================

    try:

        latest_block = (
            get_latest_block_number()
        )

    except Exception as exc:

        return {
            "success": False,
            "confirmed": False,
            "status": "RPC_ERROR",
            "reason": str(exc),
            "tx_hash": tx_hash,
        }

    # =====================================================
    # CONFIRMATIONS
    # =====================================================

    confirmations = max(
        0,
        latest_block
        - transaction_block
        + 1,
    )

    try:

        required_confirmations = max(
            int(
                BASE_SEPOLIA_CONFIRMATIONS
            ),
            1,
        )

    except (
        TypeError,
        ValueError,
    ):

        required_confirmations = 1

    # -----------------------------------------------------
    # NOT ENOUGH CONFIRMATIONS
    # -----------------------------------------------------

    if (
        confirmations
        < required_confirmations
    ):

        return {
            "success": True,
            "confirmed": False,
            "status": "CONFIRMING",
            "reason": (
                "Transaction is valid and mined "
                "but is awaiting confirmations."
            ),
            "tx_hash": tx_hash,
            "confirmations": confirmations,
            "required_confirmations": (
                required_confirmations
            ),
            "block_number": transaction_block,
        }

    # =====================================================
    # FIND USDC TRANSFERS
    # =====================================================

    transfers = find_usdc_transfers(
        receipt
    )

    if not transfers:

        return {
            "success": False,
            "confirmed": False,
            "status": "NO_USDC_TRANSFER",
            "reason": (
                "No valid USDC Transfer event "
                "was found in the transaction."
            ),
            "tx_hash": tx_hash,
            "block_number": transaction_block,
            "confirmations": confirmations,
        }

    # =====================================================
    # FIND MATCHING PAYMENT
    # =====================================================

    matching_transfer = None

    for transfer in transfers:

        transfer_to = normalize_address(
            transfer.get(
                "to",
                "",
            )
        )

        amount_units = int(
            transfer.get(
                "amount_units",
                0,
            )
        )

        # -------------------------------------------------
        # RECIPIENT MUST MATCH
        # -------------------------------------------------

        if (
            transfer_to
            != recipient_address
        ):
            continue

        # -------------------------------------------------
        # PAYMENT MUST BE SUFFICIENT
        # -------------------------------------------------

        if (
            amount_units
            < expected_units
        ):
            continue

        matching_transfer = transfer

        break

    # =====================================================
    # NO MATCH
    # =====================================================

    if not matching_transfer:

        return {
            "success": False,
            "confirmed": False,
            "status": "AMOUNT_OR_RECIPIENT_MISMATCH",
            "reason": (
                "No matching USDC payment was found "
                "for the configured recipient and "
                "required amount."
            ),
            "tx_hash": tx_hash,
            "expected_amount": str(
                units_to_usdc(
                    expected_units
                )
            ),
            "recipient": recipient_address,
            "transfers": transfers,
            "block_number": transaction_block,
            "confirmations": confirmations,
        }

    # =====================================================
    # SUCCESS
    # =====================================================

    actual_units = int(
        matching_transfer.get(
            "amount_units",
            0,
        )
    )

    actual_amount = units_to_usdc(
        actual_units
    )

    return {
        "success": True,
        "confirmed": True,
        "status": "PAID",

        "tx_hash": tx_hash,

        "chain_id": int(
            BASE_SEPOLIA_CHAIN_ID
        ),

        "token": "USDC",

        "token_contract": (
            BASE_SEPOLIA_USDC_CONTRACT
        ),

        "recipient": recipient_address,

        "sender": matching_transfer.get(
            "from"
        ),

        "expected_amount": str(
            units_to_usdc(
                expected_units
            )
        ),

        "actual_amount": str(
            actual_amount
        ),

        "amount_units": actual_units,

        "confirmations": confirmations,

        "required_confirmations": (
            required_confirmations
        ),

        "block_number": transaction_block,

        "success_reason": (
            "Confirmed Base Sepolia "
            "USDC payment."
        ),
    }


# =========================================================
# SIMPLE PAYMENT STATUS
# =========================================================

def payment_status(
    tx_hash,
):
    """
    Useful for debugging/admin tools.

    This does NOT verify that the transaction
    paid a particular job.

    It only checks the basic transaction state.
    """

    if not validate_tx_hash(
        tx_hash
    ):

        return {
            "success": False,
            "reason": (
                "Invalid transaction hash."
            ),
        }

    try:

        transaction = get_transaction(
            tx_hash
        )

        receipt = get_transaction_receipt(
            tx_hash
        )

    except Exception as exc:

        return {
            "success": False,
            "reason": str(exc),
        }

    return {
        "success": True,

        "transaction_found": (
            transaction is not None
        ),

        "mined": (
            receipt is not None
        ),

        "status": (
            hex_to_int(
                receipt.get(
                    "status",
                    "0x0",
                )
            )
            if receipt
            else None
        ),

        "block_number": (
            hex_to_int(
                receipt.get(
                    "blockNumber",
                    "0x0",
                )
            )
            if receipt
            else None
        ),
    }