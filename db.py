import json
import sqlite3
from pathlib import Path


DB_PATH = Path("sovereign.db")


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS owners (
                telegram_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL DEFAULT '',
                niche TEXT NOT NULL DEFAULT '',
                services_text TEXT NOT NULL DEFAULT '',
                min_price REAL NOT NULL DEFAULT 150,
                max_price REAL NOT NULL DEFAULT 400,
                default_days INTEGER NOT NULL DEFAULT 7,
                tone TEXT NOT NULL DEFAULT 'professional',
                usdc_address TEXT,
                setup_complete INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_telegram_id INTEGER NOT NULL,
                client_name TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'NEW',
                answers TEXT NOT NULL DEFAULT '{}',
                quoted_price REAL,
                currency TEXT NOT NULL DEFAULT 'USD',
                deadline TEXT,
                proposal_text TEXT,
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                paused INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        conn.commit()


def get_owner(telegram_id: int):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM owners WHERE telegram_id = ?",
            (telegram_id,),
        ).fetchone()

    return row


def save_owner(
    telegram_id: int,
    name: str,
    services_text: str,
    min_price: float,
    max_price: float,
    default_days: int,
):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO owners (
                telegram_id,
                name,
                services_text,
                min_price,
                max_price,
                default_days,
                setup_complete
            )
            VALUES (?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(telegram_id)
            DO UPDATE SET
                name = excluded.name,
                services_text = excluded.services_text,
                min_price = excluded.min_price,
                max_price = excluded.max_price,
                default_days = excluded.default_days,
                setup_complete = 1
            """,
            (
                telegram_id,
                name,
                services_text,
                min_price,
                max_price,
                default_days,
            ),
        )

        conn.commit()