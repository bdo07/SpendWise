"""
SpendWise Database Management Module
Handles SQLite connection, schema creation, migrations, and seed data.
"""

from __future__ import annotations
import os
import shutil
import sqlite3
from pathlib import Path
from typing import Generator, Optional


DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "spendwise.db"

DEFAULT_CATEGORIES = [
    # Expense categories
    ("Food", "expense", "#D97706", "utensils"),
    ("Transport", "expense", "#2563EB", "car"),
    ("Rent", "expense", "#7C3AED", "home"),
    ("Bills", "expense", "#EA580C", "receipt"),
    ("Health", "expense", "#DC2626", "heartbeat"),
    ("Leisure", "expense", "#059669", "smile"),
    ("Shopping", "expense", "#DB2777", "shopping-bag"),
    ("Education", "expense", "#4F46E5", "book"),
    ("Other", "expense", "#6B7280", "tag"),
    # Income categories
    ("Salary", "income", "#16A34A", "briefcase"),
    ("Freelance", "income", "#0D9488", "laptop"),
]

DEFAULT_SETTINGS = {
    "currency": "MAD",
    "theme": "system",
    "user_name": "Valued Client",
    "app_version": "1.0.0",
}


class Database:
    """Manages SQLite database connections and migrations."""

    def __init__(self, db_path: Optional[str | Path] = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Create and return an SQLite connection with foreign keys and Row factory."""
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Initialize all database tables and indexes."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Categories table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
                    color TEXT NOT NULL,
                    icon TEXT NOT NULL
                );
            """)

            # Transactions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
                    amount REAL NOT NULL,
                    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
                    date TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
                );
            """)

            # Budgets table: category_id NULL represents global budget for that month
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS budgets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    month TEXT NOT NULL,
                    category_id INTEGER REFERENCES categories(id) ON DELETE CASCADE,
                    amount REAL NOT NULL
                );
            """)

            # Unique indexes for budgets to enforce 1 global and 1 per category per month
            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_budgets_global 
                ON budgets(month) WHERE category_id IS NULL;
            """)
            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_budgets_category 
                ON budgets(month, category_id) WHERE category_id IS NOT NULL;
            """)

            # Recurring transactions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recurring (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
                    amount REAL NOT NULL,
                    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
                    description TEXT DEFAULT '',
                    day_of_month INTEGER NOT NULL CHECK(day_of_month BETWEEN 1 AND 31),
                    active INTEGER NOT NULL DEFAULT 1
                );
            """)

            # Savings Goals table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS goals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    target_amount REAL NOT NULL,
                    saved_amount REAL NOT NULL DEFAULT 0,
                    deadline TEXT
                );
            """)

            # Key-Value Settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
            """)

            # Performance indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_transactions_date 
                ON transactions(date);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_transactions_category_id 
                ON transactions(category_id);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_budgets_month 
                ON budgets(month);
            """)

            conn.commit()

        self._seed_default_data()

    def _seed_default_data(self) -> None:
        """Seed categories and default settings if table is empty."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Seed categories
            for name, cat_type, color, icon in DEFAULT_CATEGORIES:
                cursor.execute(
                    "INSERT OR IGNORE INTO categories (name, type, color, icon) VALUES (?, ?, ?, ?)",
                    (name, cat_type, color, icon),
                )

            # Seed default settings
            for key, value in DEFAULT_SETTINGS.items():
                cursor.execute(
                    "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                    (key, value),
                )

            conn.commit()

    def backup(self, destination_path: str | Path) -> None:
        """Create a backup of the current database file."""
        dest = Path(destination_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        # Flush WAL to main file before backup
        with self.get_connection() as conn:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        shutil.copy2(self.db_path, dest)

    def restore(self, source_path: str | Path) -> None:
        """Restore database from an external SQLite file."""
        src = Path(source_path)
        if not src.exists():
            raise FileNotFoundError(f"Backup file not found: {source_path}")

        # Verify it's a valid SQLite file
        test_conn = sqlite3.connect(str(src))
        try:
            test_conn.execute("SELECT count(*) FROM sqlite_master;")
        finally:
            test_conn.close()

        # Overwrite current DB
        shutil.copy2(src, self.db_path)
        # Verify and re-init schema if needed
        self.init_db()


# Global default instance
db = Database()

