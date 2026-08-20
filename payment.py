"""
Base Sepolia USDC payment verification.

This module NEVER trusts a client-provided payment amount.

It verifies on-chain:

1. Transaction exists.
2. Transaction succeeded.
3. Required token contract was used.
4. USDC Transfer event exists.
5. Tokens were sent to the owner's configured wallet.
6. Amount is sufficient.
7. Required confirmations exist.

This is TESTNET payment infrastructure.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from config import (
    BASE_SEPOLIA_RPC_URL,
    BASE_SEPOLIA_CHAIN_ID,
    BASE_SEPOLIA_USDC_CONTRACT,
    BASE_SEPOLIA_CONFIRMATIONS,
)


# =========================================================
# CONSTANTS
# =========================================================

USDC_DECIMALS = 6

TRANSFER_EVENT_SIGNATURE = (
    "0xddf252ad1be2c89b69c2b068fc378"
    "daa952ba7f163c4a11628f55a4df523b3ef"
)

TX_HASH_PATTERN = re.compile(
    r"^0x[a-fA-F0-9]{64}$"
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
        BASE_SEPOLIA_RPC_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "SovereignBusinessOperator/1.0",
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
            f"Base Sepolia RPC request failed: {exc}"
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
            "Invalid JSON returned by Base Sepolia RPC."
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
    return str(
        address or ""
    ).strip().lower()


def validate_tx_hash(tx_hash):
    tx_hash = str(
        tx_hash or ""
    ).strip()

    return bool(
        TX_HASH_PATTERN.match(
            tx_hash
        )
    )


def validate_address(address):
    address = str(
        address or ""
    ).strip()

    return bool(
        re.match(
            r"^0x[a-fA-F0-9]{40}$",
            address,
        )
    )


# =========================================================
# HEX HELPERS
# =========================================================

def hex_to_int(value):
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
    Indexed Ethereum address is encoded as
    32-byte topic with 12 leading zero bytes.
    """

    topic = str(
        topic or ""
    )

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
    Transfer event data contains uint256 amount.
    """

    data = str(
        data or ""
    )

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
# USDC AMOUNT
# =========================================================

def usdc_to_units(amount):
    """
    Convert human-readable USDC to base units.

    Example:
        10.50 USDC -> 10500000
    """

    try:

        decimal_amount = Decimal(
            str(amount)
        )

    except (
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

    return int(
        decimal_amount
        * (
            Decimal(10)
            ** USDC_DECIMALS
        )
    )


def units_to_usdc(units):
    try:

        return (
            Decimal(units)
            / (
                Decimal(10)
                ** USDC_DECIMALS
            )
        )

    except (
        TypeError,
        ValueError,
    ):

        return Decimal("0")


# =========================================================
# CHAIN
# =========================================================

def get_chain_id():
    result = rpc_call(
        "eth_chainId"
    )

    return hex_to_int(
        result
    )


def verify_chain():
    chain_id = get_chain_id()

    if chain_id != BASE_SEPOLIA_CHAIN_ID:

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
    result = rpc_call(
        "eth_blockNumber"
    )

    return hex_to_int(
        result
    )


# =========================================================
# TRANSACTION
# =========================================================

def get_transaction(
    tx_hash,
):
    return rpc_call(
        "eth_getTransactionByHash",
        [
            tx_hash
        ],
    )


def get_transaction_receipt(
    tx_hash,
):
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
    Find Transfer events emitted by the configured
    USDC contract.
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

    for log in logs:

        address = normalize_address(
            log.get(
                "address",
                "",
            )
        )

        if (
            not configured_contract
            or address != configured_contract
        ):
            continue

        topics = log.get(
            "topics",
            [],
        )

        if len(topics) < 3:
            continue

        event_signature = str(
            topics[0]
        ).lower()

        if (
            event_signature
            != TRANSFER_EVENT_SIGNATURE
        ):
            continue

        sender = topic_to_address(
            topics[1]
        )

        recipient = topic_to_address(
            topics[2]
        )

        amount_units = data_to_amount(
            log.get(
                "data",
                "0x0",
            )
        )

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
):
    """
    Verify a Base Sepolia USDC payment.

    Returns a structured result suitable for saving
    in the jobs table.
    """

    tx_hash = str(
        tx_hash or ""
    ).strip()

    recipient_address = normalize_address(
        recipient_address
    )

    # -----------------------------------------------------
    # BASIC VALIDATION
    # -----------------------------------------------------

    if not validate_tx_hash(
        tx_hash
    ):

        return {
            "success": False,
            "confirmed": False,
            "reason": "Invalid transaction hash.",
        }

    if not validate_address(
        recipient_address
    ):

        return {
            "success": False,
            "confirmed": False,
            "reason": "Invalid recipient wallet address.",
        }

    if not validate_address(
        BASE_SEPOLIA_USDC_CONTRACT
    ):

        return {
            "success": False,
            "confirmed": False,
            "reason": (
                "Base Sepolia USDC contract "
                "is not configured."
            ),
        }

    # -----------------------------------------------------
    # CHAIN CHECK
    # -----------------------------------------------------

    try:

        verify_chain()

    except Exception as exc:

        return {
            "success": False,
            "confirmed": False,
            "reason": str(exc),
        }

    # -----------------------------------------------------
    # EXPECTED AMOUNT
    # -----------------------------------------------------

    try:

        expected_units = usdc_to_units(
            expected_amount
        )

    except ValueError as exc:

        return {
            "success": False,
            "confirmed": False,
            "reason": str(exc),
        }

    # -----------------------------------------------------
    # TRANSACTION
    # -----------------------------------------------------

    try:

        transaction = get_transaction(
            tx_hash
        )

    except Exception as exc:

        return {
            "success": False,
            "confirmed": False,
            "reason": str(exc),
        }

    if not transaction:

        return {
            "success": False,
            "confirmed": False,
            "reason": (
                "Transaction was not found "
                "on Base Sepolia."
            ),
        }

    # -----------------------------------------------------
    # RECEIPT
    # -----------------------------------------------------

    try:

        receipt = get_transaction_receipt(
            tx_hash
        )

    except Exception as exc:

        return {
            "success": False,
            "confirmed": False,
            "reason": str(exc),
        }

    if not receipt:

        return {
            "success": False,
            "confirmed": False,
            "reason": (
                "Transaction exists but has not "
                "been mined yet."
            ),
        }

    # -----------------------------------------------------
    # TRANSACTION STATUS
    # -----------------------------------------------------

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
            "reason": (
                "The transaction failed on-chain."
            ),
            "tx_hash": tx_hash,
        }

    # -----------------------------------------------------
    # CONFIRMATIONS
    # -----------------------------------------------------

    transaction_block = hex_to_int(
        receipt.get(
            "blockNumber",
            "0x0",
        )
    )

    try:

        latest_block = get_latest_block_number()

    except Exception as exc:

        return {
            "success": False,
            "confirmed": False,
            "reason": str(exc),
            "tx_hash": tx_hash,
        }

    confirmations = max(
        0,
        latest_block
        - transaction_block
        + 1,
    )

    if (
        confirmations
        < BASE_SEPOLIA_CONFIRMATIONS
    ):

        return {
            "success": True,
            "confirmed": False,
            "reason": (
                "Transaction is valid but "
                "awaiting confirmations."
            ),
            "tx_hash": tx_hash,
            "confirmations": confirmations,
            "required_confirmations": (
                BASE_SEPOLIA_CONFIRMATIONS
            ),
            "block_number": transaction_block,
        }

    # -----------------------------------------------------
    # TOKEN TRANSFERS
    # -----------------------------------------------------

    transfers = find_usdc_transfers(
        receipt
    )

    if not transfers:

        return {
            "success": False,
            "confirmed": False,
            "reason": (
                "No valid USDC Transfer event "
                "was found in the transaction."
            ),
            "tx_hash": tx_hash,
        }

    # -----------------------------------------------------
    # MATCH PAYMENT
    # -----------------------------------------------------

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

        if (
            transfer_to
            == recipient_address
            and amount_units
            >= expected_units
        ):

            matching_transfer = (
                transfer
            )

            break

    if not matching_transfer:

        return {
            "success": False,
            "confirmed": False,
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
        }

    # -----------------------------------------------------
    # SUCCESS
    # -----------------------------------------------------

    actual_units = int(
        matching_transfer[
            "amount_units"
        ]
    )

    actual_amount = units_to_usdc(
        actual_units
    )

    return {
        "success": True,
        "confirmed": True,

        "tx_hash": tx_hash,

        "chain_id": BASE_SEPOLIA_CHAIN_ID,

        "token": "USDC",

        "token_contract": (
            BASE_SEPOLIA_USDC_CONTRACT
        ),

        "recipient": recipient_address,

        "sender": matching_transfer[
            "from"
        ],

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
            BASE_SEPOLIA_CONFIRMATIONS
        ),

        "block_number": transaction_block,

        "success_reason": (
            "Confirmed Base Sepolia USDC payment."
        ),
    }


# =========================================================
# SIMPLE STATUS
# =========================================================

def payment_status(
    tx_hash,
):
    """
    Useful for debugging/admin tools.
    """

    if not validate_tx_hash(
        tx_hash
    ):

        return {
            "success": False,
            "reason": "Invalid transaction hash.",
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