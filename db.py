# db.py

import json
import sqlite3
from datetime import datetime

from config import DATABASE_PATH


# =========================================================
# CONNECTION
# =========================================================

def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def now():
    return datetime.utcnow().isoformat()


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def init_db():
    conn = get_connection()

    # =====================================================
    # OWNERS
    # =====================================================

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS owners (
            telegram_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            niche TEXT DEFAULT '',
            services_text TEXT DEFAULT '',

            min_price REAL DEFAULT 150,
            max_price REAL DEFAULT 400,
            default_days INTEGER DEFAULT 7,

            tone TEXT DEFAULT 'professional',

            usdc_address TEXT DEFAULT '',

            setup_complete INTEGER DEFAULT 0,

            business_rules TEXT DEFAULT '{}',

            signature_name TEXT DEFAULT '',
            signature_title TEXT DEFAULT '',
            signature_image TEXT DEFAULT '',
            notify_email TEXT DEFAULT '',
            slug TEXT DEFAULT '',

            created_at TEXT DEFAULT '',
            updated_at TEXT DEFAULT ''
        )
        """
    )

    # =====================================================
    # JOBS
    # =====================================================

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            business_id INTEGER DEFAULT 0,

            client_telegram_id INTEGER NOT NULL,
            client_name TEXT DEFAULT '',

            status TEXT DEFAULT 'NEW',

            answers TEXT DEFAULT '{}',

            quoted_price REAL DEFAULT 0,
            currency TEXT DEFAULT 'USD',

            deadline TEXT DEFAULT '',

            proposal_text TEXT DEFAULT '',

            notes TEXT DEFAULT '',

            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,

            paused INTEGER DEFAULT 0,

            complexity TEXT DEFAULT '',
            cushion_applied TEXT DEFAULT '',
            internal_analysis TEXT DEFAULT '',

            payment_status TEXT DEFAULT 'UNPAID',
            payment_network TEXT DEFAULT 'Base',
            payment_token TEXT DEFAULT 'USDC',
            payment_address TEXT DEFAULT '',
            payment_tx_hash TEXT DEFAULT '',
            payment_confirmed_at TEXT DEFAULT '',

            payment_amount REAL DEFAULT 0,

            receipt_file TEXT DEFAULT '',
            invoice_file TEXT DEFAULT ''
        )
        """
    )

    # =====================================================
    # MIGRATIONS — OWNERS
    # =====================================================

    _ensure_column(
        conn,
        "owners",
        "business_rules",
        "TEXT DEFAULT '{}'",
    )

    _ensure_column(
        conn,
        "owners",
        "signature_name",
        "TEXT DEFAULT ''",
    )

    _ensure_column(
        conn,
        "owners",
        "signature_title",
        "TEXT DEFAULT ''",
    )

    _ensure_column(
        conn,
        "owners",
        "signature_image",
        "TEXT DEFAULT ''",
    )

    _ensure_column(
        conn,
        "owners",
        "created_at",
        "TEXT DEFAULT ''",
    )

    _ensure_column(
        conn,
        "owners",
        "updated_at",
        "TEXT DEFAULT ''",
    )

    _ensure_column(
        conn,
        "owners",
        "notify_email",
        "TEXT DEFAULT ''",
    )

    _ensure_column(
        conn,
        "owners",
        "slug",
        "TEXT DEFAULT ''",
    )

    # =====================================================
    # MIGRATIONS — JOBS
    # =====================================================

    _ensure_column(
        conn,
        "jobs",
        "complexity",
        "TEXT DEFAULT ''",
    )

    _ensure_column(
        conn,
        "jobs",
        "cushion_applied",
        "TEXT DEFAULT ''",
    )

    _ensure_column(
        conn,
        "jobs",
        "internal_analysis",
        "TEXT DEFAULT ''",
    )

    # Payment fields
    _ensure_column(
        conn,
        "jobs",
        "payment_status",
        "TEXT DEFAULT 'UNPAID'",
    )

    _ensure_column(
        conn,
        "jobs",
        "payment_network",
        "TEXT DEFAULT 'Base'",
    )

    _ensure_column(
        conn,
        "jobs",
        "payment_token",
        "TEXT DEFAULT 'USDC'",
    )

    _ensure_column(
        conn,
        "jobs",
        "payment_address",
        "TEXT DEFAULT ''",
    )

    _ensure_column(
        conn,
        "jobs",
        "payment_tx_hash",
        "TEXT DEFAULT ''",
    )

    _ensure_column(
        conn,
        "jobs",
        "payment_confirmed_at",
        "TEXT DEFAULT ''",
    )

    _ensure_column(
        conn,
        "jobs",
        "payment_amount",
        "REAL DEFAULT 0",
    )

    _ensure_column(
        conn,
        "jobs",
        "receipt_file",
        "TEXT DEFAULT ''",
    )

    _ensure_column(
        conn,
        "jobs",
        "invoice_file",
        "TEXT DEFAULT ''",
    )

    _ensure_column(
        conn,
        "jobs",
        "business_id",
        "INTEGER DEFAULT 0",
    )

    _ensure_column(
        conn,
        "jobs",
        "client_username",
        "TEXT DEFAULT ''",
    )

    # Multi-tenant backfill: jobs without business_id → sole/first owner
    try:
        owners = conn.execute(
            "SELECT telegram_id, name, slug FROM owners WHERE setup_complete = 1"
        ).fetchall()
        if owners:
            default_biz = owners[0]["telegram_id"]
            conn.execute(
                """
                UPDATE jobs SET business_id = ?
                WHERE business_id IS NULL OR business_id = 0
                """,
                (default_biz,),
            )
            for o in owners:
                tid = o["telegram_id"]
                slug = (o["slug"] or "").strip() if "slug" in o.keys() else ""
                if not slug:
                    name = o["name"] or f"biz-{tid}"
                    import re
                    base = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")[:40] or f"biz-{tid}"
                    slug = base
                    n = 0
                    while conn.execute(
                        "SELECT 1 FROM owners WHERE slug = ? AND telegram_id != ?",
                        (slug, tid),
                    ).fetchone():
                        n += 1
                        slug = f"{base}-{n}"
                    conn.execute(
                        "UPDATE owners SET slug = ? WHERE telegram_id = ?",
                        (slug, tid),
                    )
    except Exception as error:
        print("multi-tenant backfill:", error)

    conn.commit()
    conn.close()


def _ensure_column(
    conn,
    table_name,
    column_name,
    definition,
):
    columns = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    existing_columns = {
        row["name"]
        for row in columns
    }

    if column_name not in existing_columns:
        conn.execute(
            f"""
            ALTER TABLE {table_name}
            ADD COLUMN {column_name} {definition}
            """
        )


# =========================================================
# OWNER
# =========================================================


def _slugify(text: str) -> str:
    import re
    text = (text or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return (text or "studio")[:40]


def ensure_owner_slug(telegram_id, name="") -> str:
    """Assign a unique public slug for deep links if missing."""
    row = get_owner(telegram_id)
    if not row:
        return ""
    try:
        existing = (row["slug"] or "").strip()
    except Exception:
        existing = ""
    if existing:
        return existing

    base = _slugify(name or row["name"] or f"biz-{telegram_id}")
    slug = base
    conn = get_connection()
    n = 0
    while True:
        found = conn.execute(
            "SELECT telegram_id FROM owners WHERE slug = ? AND telegram_id != ?",
            (slug, telegram_id),
        ).fetchone()
        if not found:
            break
        n += 1
        slug = f"{base}-{n}"
    conn.execute(
        "UPDATE owners SET slug = ?, updated_at = ? WHERE telegram_id = ?",
        (slug, now(), telegram_id),
    )
    conn.commit()
    conn.close()
    return slug


def get_owner_by_slug(slug: str):
    slug = (slug or "").strip().lower()
    if not slug:
        return None
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM owners WHERE lower(slug) = ? AND setup_complete = 1",
        (slug,),
    ).fetchone()
    conn.close()
    return row


def list_setup_owners():
    """All businesses that finished setup (multi-tenant catalog)."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT * FROM owners
        WHERE setup_complete = 1
        ORDER BY name COLLATE NOCASE
        """
    ).fetchall()
    conn.close()
    return rows


def get_business_jobs(business_id):
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT * FROM jobs
        WHERE business_id = ?
        ORDER BY id DESC
        """,
        (business_id,),
    ).fetchall()
    conn.close()
    return rows


def get_owner(telegram_id):
    conn = get_connection()

    row = conn.execute(
        """
        SELECT *
        FROM owners
        WHERE telegram_id = ?
        """,
        (telegram_id,),
    ).fetchone()

    conn.close()

    return row


def save_owner(
    telegram_id,
    name,
    niche="",
    services_text="",
    min_price=150,
    max_price=400,
    default_days=7,
    tone="professional",
    usdc_address="",
    setup_complete=1,
    business_rules=None,
    signature_name="",
    signature_title="",
    signature_image="",
    notify_email="",
):
    timestamp = now()

    if business_rules is None:
        business_rules = {}

    if isinstance(
        business_rules,
        str,
    ):
        try:
            business_rules = json.loads(
                business_rules
            )

            if not isinstance(
                business_rules,
                dict,
            ):
                business_rules = {}

        except (
            TypeError,
            json.JSONDecodeError,
        ):
            business_rules = {}

    rules_json = json.dumps(
        business_rules
    )

    conn = get_connection()

    conn.execute(
        """
        INSERT INTO owners (
            telegram_id,
            name,
            niche,
            services_text,
            min_price,
            max_price,
            default_days,
            tone,
            usdc_address,
            setup_complete,
            business_rules,
            signature_name,
            signature_title,
            signature_image,
            notify_email,
            created_at,
            updated_at
        )

        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?
        )

        ON CONFLICT(telegram_id)
        DO UPDATE SET
            name = excluded.name,
            niche = excluded.niche,
            services_text = excluded.services_text,
            min_price = excluded.min_price,
            max_price = excluded.max_price,
            default_days = excluded.default_days,
            tone = excluded.tone,
            usdc_address = excluded.usdc_address,
            setup_complete = excluded.setup_complete,
            business_rules = excluded.business_rules,
            signature_name = excluded.signature_name,
            signature_title = excluded.signature_title,
            signature_image = excluded.signature_image,
            notify_email = excluded.notify_email,
            updated_at = excluded.updated_at
        """,
        (
            telegram_id,
            name,
            niche,
            services_text,
            min_price,
            max_price,
            default_days,
            tone,
            usdc_address,
            setup_complete,
            rules_json,
            signature_name,
            signature_title,
            signature_image,
            notify_email or "",
            timestamp,
            timestamp,
        ),
    )

    conn.commit()
    conn.close()


# =========================================================
# OWNER SIGNATURE
# =========================================================

def update_owner_notify_email(telegram_id, notify_email=""):
    conn = get_connection()
    conn.execute(
        """
        UPDATE owners
        SET notify_email = ?, updated_at = ?
        WHERE telegram_id = ?
        """,
        (notify_email or "", now(), telegram_id),
    )
    conn.commit()
    conn.close()



def save_owner_signature(
    telegram_id,
    signature_name="",
    signature_title="",
    signature_image="",
):
    timestamp = now()

    conn = get_connection()

    conn.execute(
        """
        UPDATE owners
        SET
            signature_name = ?,
            signature_title = ?,
            signature_image = ?,
            updated_at = ?
        WHERE telegram_id = ?
        """,
        (
            signature_name,
            signature_title,
            signature_image,
            timestamp,
            telegram_id,
        ),
    )

    conn.commit()
    conn.close()


def get_owner_signature(telegram_id):
    owner = get_owner(
        telegram_id
    )

    if not owner:
        return {
            "signature_name": "",
            "signature_title": "",
            "signature_image": "",
        }

    return {
        "signature_name": (
            owner["signature_name"]
            or ""
        ),
        "signature_title": (
            owner["signature_title"]
            or ""
        ),
        "signature_image": (
            owner["signature_image"]
            or ""
        ),
    }


# =========================================================
# BUSINESS RULES
# =========================================================

def get_business_rules(telegram_id):
    owner = get_owner(
        telegram_id
    )

    if not owner:
        return {}

    raw = (
        owner["business_rules"]
        or ""
    )

    if not raw:
        return {}

    try:
        rules = json.loads(raw)

        if isinstance(
            rules,
            dict,
        ):
            return rules

    except (
        TypeError,
        json.JSONDecodeError,
    ):
        pass

    return {}


def save_business_rules(
    telegram_id,
    rules,
):
    if not isinstance(
        rules,
        dict,
    ):
        raise ValueError(
            "Business rules must be a dictionary."
        )

    timestamp = now()

    conn = get_connection()

    conn.execute(
        """
        UPDATE owners
        SET
            business_rules = ?,
            updated_at = ?
        WHERE telegram_id = ?
        """,
        (
            json.dumps(rules),
            timestamp,
            telegram_id,
        ),
    )

    conn.commit()
    conn.close()


# =========================================================
# PRICING
# =========================================================

DEFAULT_PRICING_RULES = {
    "enabled": True,

    "model": "base_plus_unit",

    "currency": "USD",

    "base_fee": 0,

    "unit": {
        "name": "unit",
        "price": 0,
    },

    "minimum": 150,

    "maximum": 400,

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
}


def get_default_pricing_rules():
    return json.loads(
        json.dumps(
            DEFAULT_PRICING_RULES
        )
    )


def merge_pricing_rules(
    defaults,
    overrides,
):
    if not isinstance(
        defaults,
        dict,
    ):
        defaults = {}

    if not isinstance(
        overrides,
        dict,
    ):
        overrides = {}

    result = json.loads(
        json.dumps(defaults)
    )

    for key, value in overrides.items():

        if (
            isinstance(value, dict)
            and isinstance(
                result.get(key),
                dict,
            )
        ):
            result[key] = merge_pricing_rules(
                result[key],
                value,
            )

        else:
            result[key] = value

    return result


def get_pricing_rules(
    telegram_id,
):
    rules = get_business_rules(
        telegram_id
    )

    pricing = rules.get(
        "pricing",
        {},
    )

    if not isinstance(
        pricing,
        dict,
    ):
        pricing = {}

    return merge_pricing_rules(
        get_default_pricing_rules(),
        pricing,
    )


def save_pricing_rules(
    telegram_id,
    pricing_rules,
):
    if not isinstance(
        pricing_rules,
        dict,
    ):
        raise ValueError(
            "Pricing rules must be a dictionary."
        )

    current_rules = get_business_rules(
        telegram_id
    )

    current_rules["pricing"] = (
        merge_pricing_rules(
            get_default_pricing_rules(),
            pricing_rules,
        )
    )

    save_business_rules(
        telegram_id,
        current_rules,
    )


def update_pricing_rule(
    telegram_id,
    key,
    value,
):
    pricing = get_pricing_rules(
        telegram_id
    )

    pricing[key] = value

    save_pricing_rules(
        telegram_id,
        pricing,
    )


def reset_pricing_rules(
    telegram_id,
):
    save_pricing_rules(
        telegram_id,
        get_default_pricing_rules(),
    )


# =========================================================
# ORDERS
# =========================================================

def create_order(
    client_telegram_id,
    client_name="",
):
    return create_job(
        client_telegram_id,
        client_name,
    )


def get_order(order_id):
    return get_job(
        order_id
    )


def get_client_orders(
    client_telegram_id,
    business_id=None,
):
    conn = get_connection()

    if business_id:
        rows = conn.execute(
            """
            SELECT *
            FROM jobs
            WHERE client_telegram_id = ?
              AND business_id = ?
            ORDER BY id DESC
            """,
            (
                client_telegram_id,
                int(business_id),
            ),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT *
            FROM jobs
            WHERE client_telegram_id = ?
            ORDER BY id DESC
            """,
            (
                client_telegram_id,
            ),
        ).fetchall()

    conn.close()

    return rows


def get_active_orders(
    client_telegram_id,
):
    conn = get_connection()

    rows = conn.execute(
        """
        SELECT *
        FROM jobs
        WHERE client_telegram_id = ?
        AND status NOT IN (
            'CLOSED',
            'DELIVERED'
        )
        ORDER BY id DESC
        """,
        (
            client_telegram_id,
        ),
    ).fetchall()

    conn.close()

    return rows


def get_latest_order(
    client_telegram_id,
):
    conn = get_connection()

    row = conn.execute(
        """
        SELECT *
        FROM jobs
        WHERE client_telegram_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            client_telegram_id,
        ),
    ).fetchone()

    conn.close()

    return row


def create_job(
    client_telegram_id,
    client_name="",
    client_username="",
    business_id=0,
):
    timestamp = now()

    conn = get_connection()

    cursor = conn.execute(
        """
        INSERT INTO jobs (
            business_id,
            client_telegram_id,
            client_name,
            client_username,
            status,
            answers,
            quoted_price,
            currency,
            deadline,
            proposal_text,
            notes,
            created_at,
            updated_at,
            paused,
            complexity,
            cushion_applied,
            internal_analysis,
            payment_status,
            payment_network,
            payment_token,
            payment_address,
            payment_tx_hash,
            payment_confirmed_at,
            payment_amount,
            receipt_file,
            invoice_file
        )

        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """,
        (
            int(business_id or 0),
            client_telegram_id,
            client_name,
            client_username or "",
            "NEW",
            "{}",
            0,
            "USD",
            "",
            "",
            "",
            timestamp,
            timestamp,
            0,
            "",
            "",
            "",
            "UNPAID",
            "Base",
            "USDC",
            "",
            "",
            "",
            0,
            "",
            "",
        ),
    )

    conn.commit()

    job_id = cursor.lastrowid

    conn.close()

    return job_id


# =========================================================
# JOB LOOKUPS
# =========================================================

def get_job(job_id):
    conn = get_connection()

    row = conn.execute(
        """
        SELECT *
        FROM jobs
        WHERE id = ?
        """,
        (
            job_id,
        ),
    ).fetchone()

    conn.close()

    return row


def get_client_job(
    client_telegram_id,
    job_id,
):
    conn = get_connection()

    row = conn.execute(
        """
        SELECT *
        FROM jobs
        WHERE id = ?
        AND client_telegram_id = ?
        """,
        (
            job_id,
            client_telegram_id,
        ),
    ).fetchone()

    conn.close()

    return row


def get_open_job(
    client_telegram_id,
):
    conn = get_connection()

    row = conn.execute(
        """
        SELECT *
        FROM jobs
        WHERE client_telegram_id = ?
        AND status NOT IN (
            'CLOSED',
            'DELIVERED'
        )
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            client_telegram_id,
        ),
    ).fetchone()

    conn.close()

    return row


def get_all_jobs():
    conn = get_connection()

    rows = conn.execute(
        """
        SELECT *
        FROM jobs
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()

    return rows


# =========================================================
# ANSWERS
# =========================================================

def save_job_answers(
    job_id,
    answers,
):
    timestamp = now()

    if not isinstance(
        answers,
        dict,
    ):
        answers = {}

    conn = get_connection()

    conn.execute(
        """
        UPDATE jobs
        SET
            answers = ?,
            status = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            json.dumps(answers),
            "QUALIFYING",
            timestamp,
            job_id,
        ),
    )

    conn.commit()
    conn.close()


def get_job_answers(job_id):
    job = get_job(
        job_id
    )

    if not job:
        return {}

    try:
        answers = json.loads(
            job["answers"]
        )

        if isinstance(
            answers,
            dict,
        ):
            return answers

    except (
        TypeError,
        json.JSONDecodeError,
    ):
        pass

    return {}


# =========================================================
# JOB ANALYSIS
# =========================================================

def save_job_analysis(
    job_id,
    complexity="",
    cushion_applied="",
    internal_analysis="",
):
    timestamp = now()

    conn = get_connection()

    conn.execute(
        """
        UPDATE jobs
        SET
            complexity = ?,
            cushion_applied = ?,
            internal_analysis = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            complexity,
            cushion_applied,
            internal_analysis,
            timestamp,
            job_id,
        ),
    )

    conn.commit()
    conn.close()


def get_job_analysis(job_id):
    conn = get_connection()

    row = conn.execute(
        """
        SELECT
            complexity,
            cushion_applied,
            internal_analysis
        FROM jobs
        WHERE id = ?
        """,
        (
            job_id,
        ),
    ).fetchone()

    conn.close()

    if not row:
        return {}

    return {
        "complexity": (
            row["complexity"]
            or ""
        ),
        "cushion_applied": (
            row["cushion_applied"]
            or ""
        ),
        "internal_analysis": (
            row["internal_analysis"]
            or ""
        ),
    }


# =========================================================
# PROPOSALS
# =========================================================

def save_proposal(
    job_id,
    price,
    proposal_text,
    currency="USD",
    deadline="",
):
    timestamp = now()

    conn = get_connection()

    conn.execute(
        """
        UPDATE jobs
        SET
            quoted_price = ?,
            proposal_text = ?,
            currency = ?,
            deadline = ?,
            status = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            price,
            proposal_text,
            currency,
            deadline,
            "QUOTED",
            timestamp,
            job_id,
        ),
    )

    conn.commit()
    conn.close()


def get_proposal(job_id):
    conn = get_connection()

    row = conn.execute(
        """
        SELECT
            id,
            proposal_text,
            quoted_price,
            currency,
            deadline,
            status,
            created_at,
            updated_at
        FROM jobs
        WHERE id = ?
        """,
        (
            job_id,
        ),
    ).fetchone()

    conn.close()

    return row


# =========================================================
# STATUS
# =========================================================

def set_job_status(
    job_id,
    status,
):
    timestamp = now()

    conn = get_connection()

    conn.execute(
        """
        UPDATE jobs
        SET
            status = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            status,
            timestamp,
            job_id,
        ),
    )

    conn.commit()
    conn.close()


def set_order_status(
    order_id,
    status,
):
    set_job_status(
        order_id,
        status,
    )


# =========================================================
# PAUSE / RESUME
# =========================================================

def set_job_paused(
    job_id,
    paused,
):
    timestamp = now()

    conn = get_connection()

    conn.execute(
        """
        UPDATE jobs
        SET
            paused = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            1 if paused else 0,
            timestamp,
            job_id,
        ),
    )

    conn.commit()
    conn.close()


def set_order_paused(
    order_id,
    paused,
):
    set_job_paused(
        order_id,
        paused,
    )


# =========================================================
# NOTES
# =========================================================

def update_job_status_and_notes(
    job_id,
    status=None,
    notes=None,
):
    timestamp = now()

    conn = get_connection()

    if (
        status is not None
        and notes is not None
    ):
        conn.execute(
            """
            UPDATE jobs
            SET
                status = ?,
                notes = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                status,
                notes,
                timestamp,
                job_id,
            ),
        )

    elif status is not None:
        conn.execute(
            """
            UPDATE jobs
            SET
                status = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                status,
                timestamp,
                job_id,
            ),
        )

    elif notes is not None:
        conn.execute(
            """
            UPDATE jobs
            SET
                notes = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                notes,
                timestamp,
                job_id,
            ),
        )

    conn.commit()
    conn.close()


# =========================================================
# PAYMENT
# =========================================================

def set_payment_details(
    job_id,
    payment_address="",
    payment_network="Base",
    payment_token="USDC",
    payment_amount=0,
):
    """
    Save the payment instructions for a job.

    Payment instructions for Base mainnet USDC.
    """

    timestamp = now()

    conn = get_connection()

    conn.execute(
        """
        UPDATE jobs
        SET
            payment_address = ?,
            payment_network = ?,
            payment_token = ?,
            payment_amount = ?,
            payment_status = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            payment_address,
            payment_network,
            payment_token,
            payment_amount,
            "AWAITING_PAYMENT",
            timestamp,
            job_id,
        ),
    )

    conn.commit()
    conn.close()


def get_payment_details(job_id):
    conn = get_connection()

    row = conn.execute(
        """
        SELECT
            id,
            quoted_price,
            currency,
            payment_status,
            payment_network,
            payment_token,
            payment_address,
            payment_amount,
            payment_tx_hash,
            payment_confirmed_at,
            receipt_file,
            invoice_file
        FROM jobs
        WHERE id = ?
        """,
        (
            job_id,
        ),
    ).fetchone()

    conn.close()

    if not row:
        return {}

    return {
        "job_id": row["id"],
        "quoted_price": row["quoted_price"] or 0,
        "currency": row["currency"] or "USD",
        "payment_status": (
            row["payment_status"]
            or "UNPAID"
        ),
        "payment_network": (
            row["payment_network"]
            or "Base"
        ),
        "payment_token": (
            row["payment_token"]
            or "USDC"
        ),
        "payment_address": (
            row["payment_address"]
            or ""
        ),
        "payment_amount": (
            row["payment_amount"]
            or 0
        ),
        "payment_tx_hash": (
            row["payment_tx_hash"]
            or ""
        ),
        "payment_confirmed_at": (
            row["payment_confirmed_at"]
            or ""
        ),
        "receipt_file": (
            row["receipt_file"]
            or ""
        ),
        "invoice_file": (
            row["invoice_file"]
            or ""
        ),
    }


def set_payment_tx_hash(
    job_id,
    tx_hash,
):
    """
    Store a transaction hash submitted by the client.

    IMPORTANT:
    Saving a hash does NOT mean payment is confirmed.
    Confirmation must happen after blockchain verification.
    """

    timestamp = now()

    tx_hash = str(
        tx_hash or ""
    ).strip()

    conn = get_connection()

    conn.execute(
        """
        UPDATE jobs
        SET
            payment_tx_hash = ?,
            payment_status = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            tx_hash,
            "TX_SUBMITTED",
            timestamp,
            job_id,
        ),
    )

    conn.commit()
    conn.close()


def confirm_payment(
    job_id,
    tx_hash,
    amount,
    payment_network="Base",
    payment_token="USDC",
):
    """
    Mark payment as CONFIRMED.

    This function should only be called AFTER the
    blockchain verification code has confirmed:

    1. Transaction exists.
    2. Transaction is successful.
    3. Correct network.
    4. Correct token.
    5. Correct recipient address.
    6. Correct amount.
    """

    timestamp = now()

    tx_hash = str(
        tx_hash or ""
    ).strip()

    conn = get_connection()

    conn.execute(
        """
        UPDATE jobs
        SET
            payment_status = ?,
            payment_tx_hash = ?,
            payment_amount = ?,
            payment_network = ?,
            payment_token = ?,
            payment_confirmed_at = ?,
            status = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            "CONFIRMED",
            tx_hash,
            amount,
            payment_network,
            payment_token,
            timestamp,
            "PAID",
            timestamp,
            job_id,
        ),
    )

    conn.commit()
    conn.close()


def reject_payment(
    job_id,
    reason="",
):
    """
    Mark a submitted payment as rejected.

    The transaction hash is preserved for audit purposes.
    """

    timestamp = now()

    reason = str(
        reason or ""
    ).strip()

    conn = get_connection()

    current = conn.execute(
        """
        SELECT notes
        FROM jobs
        WHERE id = ?
        """,
        (
            job_id,
        ),
    ).fetchone()

    existing_notes = ""

    if current:
        existing_notes = (
            current["notes"]
            or ""
        )

    if reason:
        if existing_notes:
            existing_notes += "\n"

        existing_notes += (
            "Payment verification rejected: "
            + reason
        )

    conn.execute(
        """
        UPDATE jobs
        SET
            payment_status = ?,
            notes = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            "REJECTED",
            existing_notes,
            timestamp,
            job_id,
        ),
    )

    conn.commit()
    conn.close()


def mark_payment_pending(
    job_id,
):
    timestamp = now()

    conn = get_connection()

    conn.execute(
        """
        UPDATE jobs
        SET
            payment_status = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            "VERIFYING",
            timestamp,
            job_id,
        ),
    )

    conn.commit()
    conn.close()


def find_other_job_using_tx_hash(tx_hash, exclude_job_id=None):
    """
    Replay protection.

    Reject a hash only if it was already submitted
    and confirmed on another job.
    """

    tx_hash = str(tx_hash or "").strip().lower()

    if not tx_hash:
        return None

    conn = get_connection()

    if exclude_job_id is None:
        row = conn.execute(
            """
            SELECT id, payment_status, status
            FROM jobs
            WHERE lower(payment_tx_hash) = ?
              AND (
                  payment_status = 'CONFIRMED'
                  OR status = 'PAID'
              )
            LIMIT 1
            """,
            (tx_hash,),
        ).fetchone()
    else:
        row = conn.execute(
            """
            SELECT id, payment_status, status
            FROM jobs
            WHERE lower(payment_tx_hash) = ?
              AND id != ?
              AND (
                  payment_status = 'CONFIRMED'
                  OR status = 'PAID'
              )
            LIMIT 1
            """,
            (tx_hash, exclude_job_id),
        ).fetchone()

    conn.close()

    if not row:
        return None

    return {
        "id": row["id"],
        "payment_status": row["payment_status"],
        "status": row["status"],
    }


def is_payment_confirmed(job_id):
    conn = get_connection()

    row = conn.execute(
        """
        SELECT payment_status
        FROM jobs
        WHERE id = ?
        """,
        (
            job_id,
        ),
    ).fetchone()

    conn.close()

    if not row:
        return False

    return (
        row["payment_status"]
        == "CONFIRMED"
    )


# =========================================================
# RECEIPT / INVOICE FILES
# =========================================================

def save_receipt_file(
    job_id,
    receipt_file,
):
    timestamp = now()

    conn = get_connection()

    conn.execute(
        """
        UPDATE jobs
        SET
            receipt_file = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            str(
                receipt_file or ""
            ),
            timestamp,
            job_id,
        ),
    )

    conn.commit()
    conn.close()


def save_invoice_file(
    job_id,
    invoice_file,
):
    timestamp = now()

    conn = get_connection()

    conn.execute(
        """
        UPDATE jobs
        SET
            invoice_file = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            str(
                invoice_file or ""
            ),
            timestamp,
            job_id,
        ),
    )

    conn.commit()
    conn.close()


def get_receipt_file(job_id):
    conn = get_connection()

    row = conn.execute(
        """
        SELECT receipt_file
        FROM jobs
        WHERE id = ?
        """,
        (
            job_id,
        ),
    ).fetchone()

    conn.close()

    if not row:
        return ""

    return (
        row["receipt_file"]
        or ""
    )


def get_invoice_file(job_id):
    conn = get_connection()

    row = conn.execute(
        """
        SELECT invoice_file
        FROM jobs
        WHERE id = ?
        """,
        (
            job_id,
        ),
    ).fetchone()

    conn.close()

    if not row:
        return ""

    return (
        row["invoice_file"]
        or ""
    )


# =========================================================
# CLIENT OWNERSHIP
# =========================================================

def client_owns_job(
    client_telegram_id,
    job_id,
):
    conn = get_connection()

    row = conn.execute(
        """
        SELECT id
        FROM jobs
        WHERE id = ?
        AND client_telegram_id = ?
        """,
        (
            job_id,
            client_telegram_id,
        ),
    ).fetchone()

    conn.close()

    return row is not None


def client_owns_order(
    client_telegram_id,
    order_id,
):
    return client_owns_job(
        client_telegram_id,
        order_id,
    )


# =========================================================
# DELETE / RESET HELPERS
# =========================================================

def delete_job(job_id):
    conn = get_connection()

    conn.execute(
        """
        DELETE FROM jobs
        WHERE id = ?
        """,
        (
            job_id,
        ),
    )

    conn.commit()
    conn.close()


def clear_all_jobs():
    conn = get_connection()

    conn.execute(
        """
        DELETE FROM jobs
        """
    )

    conn.commit()
    conn.close()


# =========================================================
# DATABASE STARTUP
# =========================================================

if __name__ == "__main__":
    init_db()
    print(
        "Database initialized successfully."
    )