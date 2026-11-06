"""
SpendWise Repositories Module
Provides clean CRUD and query interfaces for all data models.
Strict separation of database interactions from application logic.
"""

from __future__ import annotations
import sqlite3
from typing import List, Optional, Tuple
from core.database import Database, db
from core.models import Budget, Category, Goal, Recurring, Transaction


class CategoryRepository:
    """Repository for categories."""

    def __init__(self, database: Database = db) -> None:
        self.db = database

    def get_all(self, type_: Optional[str] = None) -> List[Category]:
        """Fetch all categories, optionally filtered by type ('income' or 'expense')."""
        query = "SELECT id, name, type, color, icon FROM categories"
        params: list = []
        if type_:
            query += " WHERE type = ?"
            params.append(type_)
        query += " ORDER BY name ASC"

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [
                Category(
                    id=row["id"],
                    name=row["name"],
                    type=row["type"],
                    color=row["color"],
                    icon=row["icon"],
                )
                for row in cursor.fetchall()
            ]

    def get_by_id(self, category_id: int) -> Optional[Category]:
        """Fetch category by its primary key ID."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name, type, color, icon FROM categories WHERE id = ?",
                (category_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return Category(
                id=row["id"],
                name=row["name"],
                type=row["type"],
                color=row["color"],
                icon=row["icon"],
            )

    def get_by_name(self, name: str) -> Optional[Category]:
        """Fetch category by its unique name."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name, type, color, icon FROM categories WHERE LOWER(name) = LOWER(?)",
                (name.strip(),),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return Category(
                id=row["id"],
                name=row["name"],
                type=row["type"],
                color=row["color"],
                icon=row["icon"],
            )

    def create(self, category: Category) -> Category:
        """Create a new category."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO categories (name, type, color, icon) VALUES (?, ?, ?, ?)",
                (category.name.strip(), category.type, category.color, category.icon),
            )
            category.id = cursor.lastrowid
            conn.commit()
            return category

    def update(self, category: Category) -> bool:
        """Update category name, type, color, or icon."""
        if category.id is None:
            return False
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE categories SET name = ?, type = ?, color = ?, icon = ? WHERE id = ?",
                (category.name.strip(), category.type, category.color, category.icon, category.id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete(self, category_id: int) -> bool:
        """Delete category if no transactions or recurring rules reference it."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
                conn.commit()
                return cursor.rowcount > 0
            except sqlite3.IntegrityError:
                return False

    def has_transactions(self, category_id: int) -> bool:
        """Check if any transactions use this category."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM transactions WHERE category_id = ? LIMIT 1", (category_id,))
            return cursor.fetchone() is not None


class TransactionRepository:
    """Repository for transactions."""

    def __init__(self, database: Database = db) -> None:
        self.db = database

    def get_all(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        category_id: Optional[int] = None,
        type_: Optional[str] = None,
        search: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Transaction]:
        """Fetch transactions matching search, category, type, and date filters."""
        query = """
            SELECT t.id, t.type, t.amount, t.category_id, t.date, t.description, t.created_at,
                   c.name as category_name, c.color as category_color, c.icon as category_icon
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE 1=1
        """
        params: list = []

        if start_date:
            query += " AND t.date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND t.date <= ?"
            params.append(end_date)
        if category_id is not None:
            query += " AND t.category_id = ?"
            params.append(category_id)
        if type_:
            query += " AND t.type = ?"
            params.append(type_)
        if search:
            query += " AND (LOWER(t.description) LIKE ? OR LOWER(c.name) LIKE ?)"
            s_param = f"%{search.strip().lower()}%"
            params.extend([s_param, s_param])

        query += " ORDER BY t.date DESC, t.id DESC"

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
            if offset is not None:
                query += " OFFSET ?"
                params.append(offset)

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [
                Transaction(
                    id=row["id"],
                    type=row["type"],
                    amount=float(row["amount"]),
                    category_id=row["category_id"],
                    date=row["date"],
                    description=row["description"] or "",
                    created_at=row["created_at"],
                    category_name=row["category_name"] or "Unknown",
                    category_color=row["category_color"] or "#6B7280",
                    category_icon=row["category_icon"] or "tag",
                )
                for row in cursor.fetchall()
            ]

    def get_by_id(self, tx_id: int) -> Optional[Transaction]:
        """Fetch a single transaction by ID."""
        query = """
            SELECT t.id, t.type, t.amount, t.category_id, t.date, t.description, t.created_at,
                   c.name as category_name, c.color as category_color, c.icon as category_icon
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.id = ?
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (tx_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return Transaction(
                id=row["id"],
                type=row["type"],
                amount=float(row["amount"]),
                category_id=row["category_id"],
                date=row["date"],
                description=row["description"] or "",
                created_at=row["created_at"],
                category_name=row["category_name"],
                category_color=row["category_color"],
                category_icon=row["category_icon"],
            )

    def create(self, tx: Transaction) -> Transaction:
        """Insert a single transaction."""
        query = """
            INSERT INTO transactions (type, amount, category_id, date, description)
            VALUES (?, ?, ?, ?, ?)
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                query,
                (tx.type, tx.amount, tx.category_id, tx.date, tx.description.strip()),
            )
            tx.id = cursor.lastrowid
            conn.commit()
            return tx

    def create_many(self, tx_list: List[Transaction]) -> int:
        """Batch insert transactions in a single transaction."""
        query = """
            INSERT INTO transactions (type, amount, category_id, date, description)
            VALUES (?, ?, ?, ?, ?)
        """
        data = [
            (t.type, t.amount, t.category_id, t.date, t.description.strip())
            for t in tx_list
        ]
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, data)
            conn.commit()
            return cursor.rowcount

    def update(self, tx: Transaction) -> bool:
        """Update transaction fields."""
        if tx.id is None:
            return False
        query = """
            UPDATE transactions
            SET type = ?, amount = ?, category_id = ?, date = ?, description = ?
            WHERE id = ?
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                query,
                (tx.type, tx.amount, tx.category_id, tx.date, tx.description.strip(), tx.id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete(self, tx_id: int) -> bool:
        """Delete transaction by ID."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_monthly_totals(self, month: str) -> Tuple[float, float]:
        """Return (income, expense) totals for the specified 'YYYY-MM' month."""
        start_date = f"{month}-01"
        # Find next month prefix or compare date < YYYY-MM-32
        query = """
            SELECT 
                COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0.0) as total_income,
                COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0.0) as total_expense
            FROM transactions
            WHERE strftime('%Y-%m', date) = ?
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (month,))
            row = cursor.fetchone()
            if row:
                return float(row["total_income"]), float(row["total_expense"])
            return 0.0, 0.0

    def get_spent_by_category_for_month(self, month: str, category_id: Optional[int] = None) -> float:
        """Return total expense for month, optionally filtered by category."""
        query = """
            SELECT COALESCE(SUM(amount), 0.0) as total
            FROM transactions
            WHERE type = 'expense' AND strftime('%Y-%m', date) = ?
        """
        params: list = [month]
        if category_id is not None:
            query += " AND category_id = ?"
            params.append(category_id)

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            return float(row["total"]) if row else 0.0

    def get_category_breakdown(self, month: str, type_: str = "expense") -> List[dict]:
        """Return sum and percentage per category for a given month."""
        query = """
            SELECT c.id, c.name, c.color, c.icon, COALESCE(SUM(t.amount), 0.0) as total
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE t.type = ? AND strftime('%Y-%m', date) = ?
            GROUP BY c.id, c.name, c.color, c.icon
            ORDER BY total DESC
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (type_, month))
            rows = cursor.fetchall()
            total_sum = sum(float(r["total"]) for r in rows)
            results = []
            for r in rows:
                amt = float(r["total"])
                pct = (amt / total_sum * 100.0) if total_sum > 0 else 0.0
                results.append({
                    "category_id": r["id"],
                    "category_name": r["name"],
                    "color": r["color"],
                    "icon": r["icon"],
                    "amount": amt,
                    "percentage": round(pct, 1),
                })
            return results

    def get_monthly_history(self, limit_months: int = 12) -> List[dict]:
        """Return aggregated monthly totals for the last N months ordered chronologically."""
        query = """
            SELECT 
                strftime('%Y-%m', date) as month,
                COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0.0) as income,
                COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0.0) as expenses
            FROM transactions
            GROUP BY strftime('%Y-%m', date)
            ORDER BY month DESC
            LIMIT ?
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (limit_months,))
            rows = cursor.fetchall()
            results = []
            for r in reversed(rows):
                inc = float(r["income"])
                exp = float(r["expenses"])
                results.append({
                    "month": r["month"],
                    "income": inc,
                    "expenses": exp,
                    "net": inc - exp,
                })
            return results

    def get_recent(self, limit: int = 5) -> List[Transaction]:
        """Fetch the latest transactions for the dashboard."""
        return self.get_all(limit=limit)

    def get_available_months(self) -> List[str]:
        """Get distinct months present in transactions ordered latest to oldest."""
        query = "SELECT DISTINCT strftime('%Y-%m', date) as m FROM transactions ORDER BY m DESC"
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            months = [row["m"] for row in cursor.fetchall() if row["m"]]
            return months


class BudgetRepository:
    """Repository for monthly budgets."""

    def __init__(self, database: Database = db) -> None:
        self.db = database

    def get_all_for_month(self, month: str) -> List[Budget]:
        """Fetch all budgets for a given month (global and category-specific)."""
        query = """
            SELECT b.id, b.month, b.category_id, b.amount,
                   c.name as category_name, c.color as category_color
            FROM budgets b
            LEFT JOIN categories c ON b.category_id = c.id
            WHERE b.month = ?
            ORDER BY (b.category_id IS NOT NULL), c.name ASC
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (month,))
            return [
                Budget(
                    id=row["id"],
                    month=row["month"],
                    category_id=row["category_id"],
                    amount=float(row["amount"]),
                    category_name=row["category_name"] or "Overall Global Budget",
                    category_color=row["category_color"] or "#B8934A",
                )
                for row in cursor.fetchall()
            ]

    def get_global_for_month(self, month: str) -> Optional[Budget]:
        """Fetch global overall budget for a month."""
        query = "SELECT id, month, category_id, amount FROM budgets WHERE month = ? AND category_id IS NULL"
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (month,))
            row = cursor.fetchone()
            if not row:
                return None
            return Budget(
                id=row["id"],
                month=row["month"],
                category_id=None,
                amount=float(row["amount"]),
                category_name="Overall Global Budget",
                category_color="#B8934A",
            )

    def get_by_category_for_month(self, month: str, category_id: int) -> Optional[Budget]:
        """Fetch budget for a specific category in a month."""
        query = """
            SELECT b.id, b.month, b.category_id, b.amount, c.name as category_name, c.color as category_color
            FROM budgets b
            JOIN categories c ON b.category_id = c.id
            WHERE b.month = ? AND b.category_id = ?
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (month, category_id))
            row = cursor.fetchone()
            if not row:
                return None
            return Budget(
                id=row["id"],
                month=row["month"],
                category_id=row["category_id"],
                amount=float(row["amount"]),
                category_name=row["category_name"],
                category_color=row["category_color"],
            )

    def set_budget(self, budget: Budget) -> Budget:
        """Upsert budget for (month, category_id)."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if budget.category_id is None:
                cursor.execute(
                    """
                    INSERT INTO budgets (month, category_id, amount)
                    VALUES (?, NULL, ?)
                    ON CONFLICT(month) WHERE category_id IS NULL DO UPDATE SET amount = excluded.amount
                    """,
                    (budget.month, budget.amount),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO budgets (month, category_id, amount)
                    VALUES (?, ?, ?)
                    ON CONFLICT(month, category_id) WHERE category_id IS NOT NULL DO UPDATE SET amount = excluded.amount
                    """,
                    (budget.month, budget.category_id, budget.amount),
                )
            budget.id = cursor.lastrowid
            conn.commit()
            return budget

    def delete(self, budget_id: int) -> bool:
        """Delete budget entry."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM budgets WHERE id = ?", (budget_id,))
            conn.commit()
            return cursor.rowcount > 0

    def copy_budgets_from_previous_month(self, from_month: str, to_month: str) -> int:
        """Clone all budgets from previous month into current month if not already defined."""
        previous_budgets = self.get_all_for_month(from_month)
        count = 0
        for b in previous_budgets:
            new_b = Budget(id=None, month=to_month, category_id=b.category_id, amount=b.amount)
            self.set_budget(new_b)
            count += 1
        return count


class RecurringRepository:
    """Repository for recurring transactions."""

    def __init__(self, database: Database = db) -> None:
        self.db = database

    def get_all(self, active_only: bool = False) -> List[Recurring]:
        """Fetch recurring transactions."""
        query = """
            SELECT r.id, r.type, r.amount, r.category_id, r.description, r.day_of_month, r.active,
                   c.name as category_name
            FROM recurring r
            JOIN categories c ON r.category_id = c.id
        """
        params: list = []
        if active_only:
            query += " WHERE r.active = 1"
        query += " ORDER BY r.day_of_month ASC, r.id ASC"

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [
                Recurring(
                    id=row["id"],
                    type=row["type"],
                    amount=float(row["amount"]),
                    category_id=row["category_id"],
                    description=row["description"] or "",
                    day_of_month=row["day_of_month"],
                    active=row["active"],
                    category_name=row["category_name"],
                )
                for row in cursor.fetchall()
            ]

    def get_by_id(self, rec_id: int) -> Optional[Recurring]:
        """Fetch recurring transaction by ID."""
        query = """
            SELECT r.id, r.type, r.amount, r.category_id, r.description, r.day_of_month, r.active,
                   c.name as category_name
            FROM recurring r
            JOIN categories c ON r.category_id = c.id
            WHERE r.id = ?
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (rec_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return Recurring(
                id=row["id"],
                type=row["type"],
                amount=float(row["amount"]),
                category_id=row["category_id"],
                description=row["description"] or "",
                day_of_month=row["day_of_month"],
                active=row["active"],
                category_name=row["category_name"],
            )

    def create(self, rec: Recurring) -> Recurring:
        """Create new recurring transaction."""
        query = """
            INSERT INTO recurring (type, amount, category_id, description, day_of_month, active)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                query,
                (rec.type, rec.amount, rec.category_id, rec.description.strip(), rec.day_of_month, rec.active),
            )
            rec.id = cursor.lastrowid
            conn.commit()
            return rec

    def update(self, rec: Recurring) -> bool:
        """Update recurring transaction details."""
        if rec.id is None:
            return False
        query = """
            UPDATE recurring
            SET type = ?, amount = ?, category_id = ?, description = ?, day_of_month = ?, active = ?
            WHERE id = ?
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                query,
                (rec.type, rec.amount, rec.category_id, rec.description.strip(), rec.day_of_month, rec.active, rec.id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete(self, rec_id: int) -> bool:
        """Delete recurring transaction."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM recurring WHERE id = ?", (rec_id,))
            conn.commit()
            return cursor.rowcount > 0

    def toggle_active(self, rec_id: int, active: bool) -> bool:
        """Toggle active flag on recurring transaction."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE recurring SET active = ? WHERE id = ?", (1 if active else 0, rec_id))
            conn.commit()
            return cursor.rowcount > 0


class GoalRepository:
    """Repository for savings goals."""

    def __init__(self, database: Database = db) -> None:
        self.db = database

    def get_all(self) -> List[Goal]:
        """Fetch all savings goals."""
        query = "SELECT id, name, target_amount, saved_amount, deadline FROM goals ORDER BY id ASC"
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            return [
                Goal(
                    id=row["id"],
                    name=row["name"],
                    target_amount=float(row["target_amount"]),
                    saved_amount=float(row["saved_amount"]),
                    deadline=row["deadline"],
                )
                for row in cursor.fetchall()
            ]

    def get_by_id(self, goal_id: int) -> Optional[Goal]:
        """Fetch goal by ID."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, target_amount, saved_amount, deadline FROM goals WHERE id = ?", (goal_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return Goal(
                id=row["id"],
                name=row["name"],
                target_amount=float(row["target_amount"]),
                saved_amount=float(row["saved_amount"]),
                deadline=row["deadline"],
            )

    def create(self, goal: Goal) -> Goal:
        """Create new savings goal."""
        query = "INSERT INTO goals (name, target_amount, saved_amount, deadline) VALUES (?, ?, ?, ?)"
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                query,
                (goal.name.strip(), goal.target_amount, goal.saved_amount, goal.deadline),
            )
            goal.id = cursor.lastrowid
            conn.commit()
            return goal

    def update(self, goal: Goal) -> bool:
        """Update existing savings goal."""
        if goal.id is None:
            return False
        query = "UPDATE goals SET name = ?, target_amount = ?, saved_amount = ?, deadline = ? WHERE id = ?"
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                query,
                (goal.name.strip(), goal.target_amount, goal.saved_amount, goal.deadline, goal.id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def add_savings(self, goal_id: int, amount: float) -> bool:
        """Increment saved amount for goal."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE goals SET saved_amount = MAX(0.0, saved_amount + ?) WHERE id = ?",
                (amount, goal_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete(self, goal_id: int) -> bool:
        """Delete savings goal."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
            conn.commit()
            return cursor.rowcount > 0


class SettingsRepository:
    """Repository for key-value settings."""

    def __init__(self, database: Database = db) -> None:
        self.db = database

    def get(self, key: str, default: str = "") -> str:
        """Fetch setting value or return default."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default

    def set(self, key: str, value: str) -> None:
        """Set or update setting key-value pair."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, str(value)),
            )
            conn.commit()

    def get_all(self) -> dict[str, str]:
        """Fetch all settings as dictionary."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM settings")
            return {row["key"]: row["value"] for row in cursor.fetchall()}
