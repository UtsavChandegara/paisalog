import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "paisalog.db"


def get_db_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def create_tables():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            amount REAL NOT NULL,
            type TEXT NOT NULL,
            category TEXT NOT NULL,
            mode TEXT NOT NULL DEFAULT 'cash',
            note TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_balance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,
            cash_opening REAL,
            cash_closing REAL,
            online_opening REAL,
            online_closing REAL,
            note TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS people (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Insert default categories if the table is empty
    cursor.execute("SELECT COUNT(*) FROM categories")
    if cursor.fetchone()[0] == 0:
        default_categories = [
            ("Food",), ("Transport",), ("Shopping",), ("Rent",),
            ("Stationary",), ("Medical",), ("Entertainment",),
            ("Recharge",), ("Education",), ("Other",)
        ]
        cursor.executemany(
            "INSERT INTO categories (name) VALUES (?)", default_categories
        )

    migrate_transactions_table(cursor)
    migrate_daily_balance_table(cursor)

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS social_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            amount REAL NOT NULL,
            direction TEXT NOT NULL,
            person_name TEXT NOT NULL,
            mode TEXT NOT NULL DEFAULT 'cash',
            reason TEXT, -- for backward compatibility
            note TEXT,
            is_settled INTEGER NOT NULL DEFAULT 0,
            settled_at TEXT,
            source TEXT NOT NULL DEFAULT 'manual',
            category TEXT NOT NULL DEFAULT 'Other',
            group_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    migrate_social_ledger_table(cursor)

    connection.commit()
    connection.close()


def get_table_columns(cursor, table_name):
    rows = cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
    return [row["name"] for row in rows]


def migrate_transactions_table(cursor):
    columns = get_table_columns(cursor, "transactions")

    if "mode" not in columns:
        cursor.execute(
            """
            ALTER TABLE transactions
            ADD COLUMN mode TEXT NOT NULL DEFAULT 'cash'
            """
        )

    if "others_share" not in columns:
        cursor.execute(
            """
            ALTER TABLE transactions
            ADD COLUMN others_share REAL NOT NULL DEFAULT 0
            """
        )

    if "others_person" not in columns:
        cursor.execute(
            """
            ALTER TABLE transactions
            ADD COLUMN others_person TEXT NOT NULL DEFAULT ''
            """
        )


def migrate_social_ledger_table(cursor):
    columns = get_table_columns(cursor, "social_ledger")

    if "mode" not in columns:
        cursor.execute(
            """
            ALTER TABLE social_ledger
            ADD COLUMN mode TEXT NOT NULL DEFAULT 'cash'
            """
        )

    if "source" not in columns:
        cursor.execute(
            """
            ALTER TABLE social_ledger
            ADD COLUMN source TEXT NOT NULL DEFAULT 'manual'
            """
        )

    if "category" not in columns:
        cursor.execute(
            """
            ALTER TABLE social_ledger
            ADD COLUMN category TEXT NOT NULL DEFAULT 'Other'
            """
        )

    if "note" not in columns:
        cursor.execute(
            """
            ALTER TABLE social_ledger
            ADD COLUMN note TEXT
            """
        )

    if "group_id" not in columns:
        cursor.execute(
            """
            ALTER TABLE social_ledger
            ADD COLUMN group_id TEXT
            """
        )

    if "created_at" not in columns:
        cursor.execute(
            """
            ALTER TABLE social_ledger
            ADD COLUMN created_at TIMESTAMP DEFAULT '2026-01-01 00:00:00'
            """
        )


def migrate_daily_balance_table(cursor):
    columns = get_table_columns(cursor, "daily_balance")

    if "opening_balance" not in columns and "closing_balance" not in columns:
        return

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_balance_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,
            cash_opening REAL,
            cash_closing REAL,
            online_opening REAL,
            online_closing REAL,
            note TEXT
        )
        """
    )

    cursor.execute(
        """
        INSERT INTO daily_balance_new (
            id,
            date,
            cash_opening,
            cash_closing,
            online_opening,
            online_closing,
            note
        )
        SELECT
            id,
            date,
            opening_balance,
            closing_balance,
            0,
            0,
            note
        FROM daily_balance
        """
    )

    cursor.execute("DROP TABLE daily_balance")
    cursor.execute("ALTER TABLE daily_balance_new RENAME TO daily_balance")


create_tables()
