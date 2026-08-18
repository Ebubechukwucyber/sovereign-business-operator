import json
import sqlite3
from datetime import datetime

from config import DATABASE_PATH


def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
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
            setup_complete INTEGER DEFAULT 0
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            paused INTEGER DEFAULT 0
        )
        """
    )

    conn.commit()
    conn.close()


# =========================================================
# OWNER
# =========================================================

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
    niche="landing pages",
    services_text="",
    min_price=150,
    max_price=400,
    default_days=7,
    tone="professional",
    usdc_address="",
    setup_complete=1,
):
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
            setup_complete
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

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
            setup_complete = excluded.setup_complete
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
        ),
    )

    conn.commit()
    conn.close()


# =========================================================
# JOBS / ORDERS
# =========================================================

def create_job(client_telegram_id, client_name=""):
    now = datetime.utcnow().isoformat()

    conn = get_connection()

    cursor = conn.execute(
        """
        INSERT INTO jobs (
            client_telegram_id,
            client_name,
            status,
            answers,
            quoted_price,
            currency,
            deadline,
            proposal_text,
            notes,
            created_at,
            updated_at,
            paused
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            client_telegram_id,
            client_name,
            "NEW",
            "{}",
            0,
            "USD",
            "",
            "",
            "",
            now,
            now,
            0,
        ),
    )

    conn.commit()

    job_id = cursor.lastrowid

    conn.close()

    return job_id


def get_job(job_id):
    conn = get_connection()

    row = conn.execute(
        """
        SELECT *
        FROM jobs
        WHERE id = ?
        """,
        (job_id,),
    ).fetchone()

    conn.close()

    return row


def get_client_jobs(client_telegram_id):
    conn = get_connection()

    rows = conn.execute(
        """
        SELECT *
        FROM jobs
        WHERE client_telegram_id = ?
        ORDER BY id DESC
        """,
        (client_telegram_id,),
    ).fetchall()

    conn.close()

    return rows


def get_client_job(client_telegram_id, job_id):
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


def get_latest_client_job(client_telegram_id):
    conn = get_connection()

    row = conn.execute(
        """
        SELECT *
        FROM jobs
        WHERE client_telegram_id = ?
        AND status NOT IN ('CLOSED', 'DELIVERED')
        ORDER BY id DESC
        LIMIT 1
        """,
        (client_telegram_id,),
    ).fetchone()

    conn.close()

    return row


# Backward-compatible helper.
# Existing code can still call this, but it now simply
# returns the latest active order.
def get_open_job(client_telegram_id):
    return get_latest_client_job(client_telegram_id)


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


def save_job_answers(job_id, answers):
    now = datetime.utcnow().isoformat()

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
            now,
            job_id,
        ),
    )

    conn.commit()
    conn.close()


def save_proposal(job_id, price, proposal_text):
    now = datetime.utcnow().isoformat()

    conn = get_connection()

    conn.execute(
        """
        UPDATE jobs
        SET
            quoted_price = ?,
            proposal_text = ?,
            status = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            price,
            proposal_text,
            "QUOTED",
            now,
            job_id,
        ),
    )

    conn.commit()
    conn.close()


def set_job_status(job_id, status):
    now = datetime.utcnow().isoformat()

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
            now,
            job_id,
        ),
    )

    conn.commit()
    conn.close()


def set_job_paused(job_id, paused):
    now = datetime.utcnow().isoformat()

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
            now,
            job_id,
        ),
    )

    conn.commit()
    conn.close()


def update_job_status_and_notes(
    job_id,
    status=None,
    notes=None,
):
    now = datetime.utcnow().isoformat()

    conn = get_connection()

    if status is not None and notes is not None:

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
                now,
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
                now,
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
                now,
                job_id,
            ),
        )

    conn.commit()
    conn.close()