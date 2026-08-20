import json
import urllib.request
import urllib.error
from decimal import Decimal


# =========================================================
# ERC-20 TRANSFER EVENT
# =========================================================

TRANSFER_EVENT_TOPIC = (
    "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a"
    "df523b3ef"
)


# =========================================================
# JSON-RPC
# =========================================================

def rpc_call(
    rpc_url,
    method,
    params,
    timeout=20,
):
    payload = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params,
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        rpc_url,
        data=payload,
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout,
        ) as response:
            raw = response.read().decode("utf-8")

    except urllib.error.URLError as error:
        raise RuntimeError(
            f"Blockchain RPC connection failed: {error}"
        )

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        raise RuntimeError(
            "Blockchain RPC returned invalid JSON."
        )

    if "error" in result:
        error = result["error"]

        raise RuntimeError(
            str(
                error.get(
                    "message",
                    "Blockchain RPC error.",
                )
            )
        )

    return result.get("result")


# =========================================================
# HELPERS
# =========================================================

def clean_hex(value):
    if value is None:
        return ""

    value = str(value).strip()

    if not value:
        return ""

    if not value.startswith("0x"):
        value = "0x" + value

    return value


def normalize_address(address):
    address = clean_hex(address)

    if not address:
        return ""

    return address.lower()


def hex_to_int(value):
    if value is None:
        return 0

    try:
        return int(value, 16)
    except (
        TypeError,
        ValueError,
    ):
        return 0


def address_from_topic(topic):
    topic = clean_hex(topic)

    if len(topic) < 42:
        return ""

    return (
        "0x"
        + topic[-40:]
    ).lower()


def normalize_tx_hash(tx_hash):
    tx_hash = str(
        tx_hash or ""
    ).strip()

    if not tx_hash:
        return ""

    if not tx_hash.startswith("0x"):
        tx_hash = "0x" + tx_hash

    return tx_hash


def is_valid_tx_hash(tx_hash):
    tx_hash = normalize_tx_hash(
        tx_hash
    )

    if len(tx_hash) != 66:
        return False

    allowed = set(
        "0123456789abcdefABCDEF"
    )

    return all(
        char in allowed
        for char in tx_hash[2:]
    )


# =========================================================
# TRANSACTION LOOKUP
# =========================================================

def get_transaction(
    rpc_url,
    tx_hash,
):
    return rpc_call(
        rpc_url,
        "eth_getTransactionByHash",
        [
            normalize_tx_hash(tx_hash)
        ],
    )


def get_transaction_receipt(
    rpc_url,
    tx_hash,
):
    return rpc_call(
        rpc_url,
        "eth_getTransactionReceipt",
        [
            normalize_tx_hash(tx_hash)
        ],
    )


def get_latest_block(
    rpc_url,
):
    result = rpc_call(
        rpc_url,
        "eth_blockNumber",
        [],
    )

    return hex_to_int(result)


# =========================================================
# VERIFY PAYMENT
# =========================================================

def verify_usdc_payment(
    *,
    rpc_url,
    chain_id,
    usdc_contract,
    recipient_address,
    tx_hash,
    expected_amount_usdc,
    required_confirmations=2,
):
    """
    Verify an ERC-20 USDC payment on Base Sepolia.

    Returns a dictionary:

        {
            "success": True/False,
            "status": "...",
            "reason": "...",
            "tx_hash": "...",
            "amount_usdc": ...,
            "sender": "...",
            "recipient": "...",
            "block_number": ...,
            "confirmations": ...
        }
    """

    tx_hash = normalize_tx_hash(
        tx_hash
    )

    usdc_contract = normalize_address(
        usdc_contract
    )

    recipient_address = normalize_address(
        recipient_address
    )

    # -----------------------------------------------------
    # BASIC VALIDATION
    # -----------------------------------------------------

    if not is_valid_tx_hash(
        tx_hash
    ):
        return {
            "success": False,
            "status": "INVALID_TX_HASH",
            "reason": (
                "The transaction hash format "
                "is invalid."
            ),
            "tx_hash": tx_hash,
        }

    if not usdc_contract:
        return {
            "success": False,
            "status": "CONFIG_ERROR",
            "reason": (
                "Base Sepolia USDC contract "
                "is not configured."
            ),
            "tx_hash": tx_hash,
        }

    if not recipient_address:
        return {
            "success": False,
            "status": "CONFIG_ERROR",
            "reason": (
                "The studio payment wallet "
                "is not configured."
            ),
            "tx_hash": tx_hash,
        }

    try:
        expected_amount = Decimal(
            str(expected_amount_usdc)
        )
    except Exception:
        expected_amount = Decimal("0")

    if expected_amount <= 0:
        return {
            "success": False,
            "status": "INVALID_AMOUNT",
            "reason": (
                "The expected payment amount "
                "is invalid."
            ),
            "tx_hash": tx_hash,
        }

    # -----------------------------------------------------
    # CHAIN ID
    # -----------------------------------------------------

    try:
        actual_chain_id = hex_to_int(
            rpc_call(
                rpc_url,
                "eth_chainId",
                [],
            )
        )
    except Exception as error:
        return {
            "success": False,
            "status": "RPC_ERROR",
            "reason": str(error),
            "tx_hash": tx_hash,
        }

    if actual_chain_id != int(chain_id):
        return {
            "success": False,
            "status": "WRONG_NETWORK",
            "reason": (
                f"Connected RPC is chain "
                f"{actual_chain_id}, expected "
                f"{chain_id}."
            ),
            "tx_hash": tx_hash,
        }

    # -----------------------------------------------------
    # TRANSACTION
    # -----------------------------------------------------

    try:
        transaction = get_transaction(
            rpc_url,
            tx_hash,
        )
    except Exception as error:
        return {
            "success": False,
            "status": "RPC_ERROR",
            "reason": str(error),
            "tx_hash": tx_hash,
        }

    if transaction is None:
        return {
            "success": False,
            "status": "NOT_FOUND",
            "reason": (
                "The transaction could not be "
                "found on the network."
            ),
            "tx_hash": tx_hash,
        }

    # -----------------------------------------------------
    # RECEIPT
    # -----------------------------------------------------

    try:
        receipt = get_transaction_receipt(
            rpc_url,
            tx_hash,
        )
    except Exception as error:
        return {
            "success": False,
            "status": "RPC_ERROR",
            "reason": str(error),
            "tx_hash": tx_hash,
        }

    # Transaction exists but hasn't been mined.
    if receipt is None:
        return {
            "success": False,
            "status": "PENDING",
            "reason": (
                "The transaction has not been "
                "mined yet."
            ),
            "tx_hash": tx_hash,
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
            "status": "FAILED",
            "reason": (
                "The blockchain transaction "
                "failed."
            ),
            "tx_hash": tx_hash,
        }

    # -----------------------------------------------------
    # BLOCK
    # -----------------------------------------------------

    transaction_block = hex_to_int(
        receipt.get(
            "blockNumber"
        )
    )

    if transaction_block <= 0:
        return {
            "success": False,
            "status": "PENDING",
            "reason": (
                "The transaction has not "
                "received a valid block yet."
            ),
            "tx_hash": tx_hash,
        }

    try:
        latest_block = get_latest_block(
            rpc_url
        )
    except Exception as error:
        return {
            "success": False,
            "status": "RPC_ERROR",
            "reason": str(error),
            "tx_hash": tx_hash,
        }

    confirmations = (
        latest_block
        - transaction_block
        + 1
    )

    # -----------------------------------------------------
    # CONFIRMATIONS
    # -----------------------------------------------------

    required_confirmations = max(
        int(required_confirmations),
        1,
    )

    if confirmations < required_confirmations:
        return {
            "success": False,
            "status": "CONFIRMATIONS_PENDING",
            "reason": (
                f"Payment transaction is confirmed "
                f"on-chain but only has "
                f"{confirmations} confirmation(s). "
                f"{required_confirmations} required."
            ),
            "tx_hash": tx_hash,
            "block_number": transaction_block,
            "confirmations": confirmations,
            "required_confirmations": (
                required_confirmations
            ),
        }

    # -----------------------------------------------------
    # FIND USDC TRANSFER
    # -----------------------------------------------------

    logs = receipt.get(
        "logs",
        [],
    )

    matching_transfers = []

    for log in logs:

        log_address = normalize_address(
            log.get("address")
        )

        if log_address != usdc_contract:
            continue

        topics = log.get(
            "topics",
            [],
        )

        if len(topics) < 3:
            continue

        topic0 = clean_hex(
            topics[0]
        ).lower()

        if topic0 != TRANSFER_EVENT_TOPIC:
            continue

        sender = address_from_topic(
            topics[1]
        )

        recipient = address_from_topic(
            topics[2]
        )

        data = clean_hex(
            log.get(
                "data",
                "0x",
            )
        )

        raw_amount = hex_to_int(
            data
        )

        amount_usdc = (
            Decimal(raw_amount)
            / Decimal("1000000")
        )

        matching_transfers.append(
            {
                "sender": sender,
                "recipient": recipient,
                "raw_amount": raw_amount,
                "amount_usdc": amount_usdc,
            }
        )

    if not matching_transfers:
        return {
            "success": False,
            "status": "NO_USDC_TRANSFER",
            "reason": (
                "No USDC transfer from the "
                "configured Base Sepolia USDC "
                "contract was found in the "
                "transaction."
            ),
            "tx_hash": tx_hash,
            "block_number": transaction_block,
            "confirmations": confirmations,
        }

    # -----------------------------------------------------
    # FIND TRANSFER TO STUDIO WALLET
    # -----------------------------------------------------

    valid_payment = None

    for transfer in matching_transfers:

        if normalize_address(
            transfer["recipient"]
        ) != recipient_address:
            continue

        if transfer["amount_usdc"] < expected_amount:
            continue

        valid_payment = transfer
        break

    if valid_payment is None:

        recipients = [
            transfer["recipient"]
            for transfer in matching_transfers
        ]

        amounts = [
            str(
                transfer["amount_usdc"]
            )
            for transfer in matching_transfers
        ]

        return {
            "success": False,
            "status": "AMOUNT_OR_RECIPIENT_MISMATCH",
            "reason": (
                "The transaction contains a USDC "
                "transfer, but it does not contain "
                "the required amount sent to the "
                "studio wallet."
            ),
            "tx_hash": tx_hash,
            "expected_amount_usdc": str(
                expected_amount
            ),
            "transfer_recipients": recipients,
            "transfer_amounts": amounts,
            "block_number": transaction_block,
            "confirmations": confirmations,
        }

    # -----------------------------------------------------
    # SUCCESS
    # -----------------------------------------------------

    return {
        "success": True,
        "status": "PAID",
        "reason": (
            "USDC payment successfully verified "
            "on Base Sepolia."
        ),
        "tx_hash": tx_hash,
        "sender": valid_payment["sender"],
        "recipient": valid_payment["recipient"],
        "amount_usdc": str(
            valid_payment["amount_usdc"]
        ),
        "expected_amount_usdc": str(
            expected_amount
        ),
        "block_number": transaction_block,
        "confirmations": confirmations,
        "required_confirmations": (
            required_confirmations
        ),
        "chain_id": actual_chain_id,
        "usdc_contract": usdc_contract,
    }