"""
SpendWise Services Module
Encapsulates all domain logic: budget calculations, threshold alerts, statistics,
recurring transaction generation, CSV import/export, and currency formatting.
The UI layer interacts exclusively with services and repositories.
"""

from __future__ import annotations
import csv
import io
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Tuple

from core.database import Database, db
from core.models import (
    Budget,
    BudgetStatus,
    Category,
    Goal,
    MonthlySummary,
    Recurring,
    Transaction,
)
from core.repositories import (
    BudgetRepository,
    CategoryRepository,
    GoalRepository,
    RecurringRepository,
    SettingsRepository,
    TransactionRepository,
)


class FinanceService:
    """Core financial logic and analytics service."""

    def __init__(self, database: Database = db) -> None:
        self.db = database
        self.cat_repo = CategoryRepository(database)
        self.tx_repo = TransactionRepository(database)
        self.budget_repo = BudgetRepository(database)
        self.rec_repo = RecurringRepository(database)
        self.goal_repo = GoalRepository(database)
        self.settings_repo = SettingsRepository(database)

    # ---------------------------------------------------------
    # Settings & Currency
    # ---------------------------------------------------------

    def get_currency(self) -> str:
        """Get the configured active currency (default MAD)."""
        return self.settings_repo.get("currency", "MAD")

    def set_currency(self, currency_code: str) -> None:
        """Set the active currency."""
        self.settings_repo.set("currency", currency_code.strip().upper())

    def get_theme(self) -> str:
        """Get current theme ('light' or 'dark')."""
        return self.settings_repo.get("theme", "light")

    def set_theme(self, theme_name: str) -> None:
        """Set active theme ('light' or 'dark')."""
        self.settings_repo.set("theme", theme_name.strip().lower())

    def format_amount(self, amount: float, include_currency: bool = True) -> str:
        """Format a numeric amount with thousand separators and 2 decimal places."""
        formatted = f"{amount:,.2f}"
        if include_currency:
            currency = self.get_currency()
            return f"{formatted} {currency}"
        return formatted

    # ---------------------------------------------------------
    # Monthly Summary & KPIs
    # ---------------------------------------------------------

    def get_monthly_summary(self, month: str) -> MonthlySummary:
        """Calculate income, expenses, net savings, and savings rate for a given 'YYYY-MM'."""
        income, expenses = self.tx_repo.get_monthly_totals(month)
        net = income - expenses

        # Savings rate = (income - expenses) / income * 100 if income > 0 else 0.0
        # If income is 0 or negative, savings rate is 0.0 (or negative if expenses > 0)
        savings_rate = (net / income * 100.0) if income > 0 else 0.0

        transactions = self.tx_repo.get_all(
            start_date=f"{month}-01",
            end_date=f"{month}-31",
        )

        return MonthlySummary(
            month=month,
            income=income,
            expenses=expenses,
            net_savings=net,
            savings_rate=round(savings_rate, 1),
            transaction_count=len(transactions),
        )

    # ---------------------------------------------------------
    # Budget Calculations & Alerts
    # ---------------------------------------------------------

    def get_budget_statuses(self, month: str) -> List[BudgetStatus]:
        """Compute spent amount, remaining, percentage, and alert level for all budgets in a month."""
        budgets = self.budget_repo.get_all_for_month(month)
        statuses: List[BudgetStatus] = []

        for b in budgets:
            if b.category_id is None:
                # Global budget: sum of all expenses in month
                spent = self.tx_repo.get_spent_by_category_for_month(month, category_id=None)
            else:
                spent = self.tx_repo.get_spent_by_category_for_month(month, category_id=b.category_id)

            percentage = (spent / b.amount * 100.0) if b.amount > 0 else 0.0
            remaining = b.amount - spent

            # Determine alert level
            if percentage >= 100.0:
                alert_level = "exceeded"
            elif percentage >= 90.0:
                alert_level = "critical"
            elif percentage >= 70.0:
                alert_level = "warning"
            else:
                alert_level = "normal"

            statuses.append(
                BudgetStatus(
                    budget=b,
                    spent=spent,
                    percentage=round(percentage, 1),
                    remaining=remaining,
                    alert_level=alert_level,
                )
            )

        return statuses

    def get_overall_budget_status(self, month: str) -> Optional[BudgetStatus]:
        """Fetch status for global budget if set, or compute auto-budget from category sum."""
        global_b = self.budget_repo.get_global_for_month(month)
        if global_b:
            spent = self.tx_repo.get_spent_by_category_for_month(month, category_id=None)
            percentage = (spent / global_b.amount * 100.0) if global_b.amount > 0 else 0.0
            remaining = global_b.amount - spent
            if percentage >= 100.0:
                alert_level = "exceeded"
            elif percentage >= 90.0:
                alert_level = "critical"
            elif percentage >= 70.0:
                alert_level = "warning"
            else:
                alert_level = "normal"
            return BudgetStatus(
                budget=global_b,
                spent=spent,
                percentage=round(percentage, 1),
                remaining=remaining,
                alert_level=alert_level,
            )
        return None

    def get_active_budget_alerts(self, month: str) -> List[Dict[str, Any]]:
        """
        Return structured alerts for budgets at 70%, 90%, and 100%+.
        Used for dashboard banners and toast notifications.
        """
        statuses = self.get_budget_statuses(month)
        alerts: List[Dict[str, Any]] = []

        for st in statuses:
            name = st.budget.category_name or "Overall Budget"
            currency = self.get_currency()
            if st.alert_level == "exceeded":
                alerts.append({
                    "level": "exceeded",
                    "title": f"Budget Exceeded: {name}",
                    "message": f"Spent {st.spent:,.2f} {currency} of {st.budget.amount:,.2f} {currency} ({st.percentage:.1f}%). Limit exceeded by {abs(st.remaining):,.2f} {currency}!",
                    "percentage": st.percentage,
                    "category_id": st.budget.category_id,
                })
            elif st.alert_level == "critical":
                alerts.append({
                    "level": "critical",
                    "title": f"Critical Budget Warning: {name}",
                    "message": f"{name} spending has reached {st.percentage:.1f}% ({st.spent:,.2f} / {st.budget.amount:,.2f} {currency}). Only {st.remaining:,.2f} {currency} left.",
                    "percentage": st.percentage,
                    "category_id": st.budget.category_id,
                })
            elif st.alert_level == "warning":
                alerts.append({
                    "level": "warning",
                    "title": f"Budget Alert: {name}",
                    "message": f"{name} spending has reached {st.percentage:.1f}% of your monthly limit.",
                    "percentage": st.percentage,
                    "category_id": st.budget.category_id,
                })

        return alerts

    # ---------------------------------------------------------
    # Recurring Transactions Generator
    # ---------------------------------------------------------

    def process_recurring_for_month(self, month: Optional[str] = None) -> int:
        """
        Auto-generate transactions from active recurring rules for the target month (defaults to current month).
        Idempotent: will not create duplicates if already generated.
        Returns count of newly generated transactions.
        """
        if not month:
            month = datetime.now().strftime("%Y-%m")

        year_str, month_str = month.split("-")
        year, m_num = int(year_str), int(month_str)

        # Get number of days in this month
        import calendar
        _, max_days = calendar.monthrange(year, m_num)

        active_recs = self.rec_repo.get_all(active_only=True)
        created_count = 0

        for rec in active_recs:
            day = min(rec.day_of_month, max_days)
            tx_date = f"{year:04d}-{m_num:02d}-{day:02d}"
            desc = f"[Recurring] {rec.description}".strip()

            # Check if this recurring transaction was already generated for this month
            existing = self.tx_repo.get_all(
                start_date=f"{month}-01",
                end_date=f"{month}-{max_days:02d}",
                category_id=rec.category_id,
                type_=rec.type,
                search=rec.description,
            )

            # Look for exact match in date and amount
            is_already_created = any(
                t.date == tx_date and abs(t.amount - rec.amount) < 0.001 for t in existing
            )

            if not is_already_created:
                new_tx = Transaction(
                    id=None,
                    type=rec.type,
                    amount=rec.amount,
                    category_id=rec.category_id,
                    date=tx_date,
                    description=desc,
                )
                self.tx_repo.create(new_tx)
                created_count += 1

        return created_count

    # ---------------------------------------------------------
    # Statistics & Historical Data
    # ---------------------------------------------------------

    def get_category_breakdown(self, month: str, type_: str = "expense") -> List[Dict[str, Any]]:
        """Return expense/income distribution by category for charts."""
        return self.tx_repo.get_category_breakdown(month, type_)

    def get_monthly_history(self, limit_months: int = 12) -> List[Dict[str, Any]]:
        """Return monthly income vs expense history for the last N months."""
        return self.tx_repo.get_monthly_history(limit_months)

    def get_cumulative_balance_series(self, limit_months: int = 12) -> List[Dict[str, Any]]:
        """Compute cumulative running balance month by month."""
        history = self.tx_repo.get_monthly_history(limit_months)
        running_balance = 0.0
        results: List[Dict[str, Any]] = []

        for item in history:
            running_balance += item["net"]
            results.append({
                "month": item["month"],
                "income": item["income"],
                "expenses": item["expenses"],
                "net": item["net"],
                "cumulative_balance": running_balance,
            })

        return results

    # ---------------------------------------------------------
    # CSV Import / Export
    # ---------------------------------------------------------

    def import_transactions_from_csv(self, file_path: str) -> Tuple[int, List[str]]:
        """
        Import transactions from a CSV file.
        Accepts columns: Date, Type, Category, Amount, Description.
        Returns: (imported_count, list_of_error_strings).
        """
        imported_count = 0
        errors: List[str] = []

        with open(file_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                return 0, ["CSV file is empty or headers are missing."]

            # Normalize header names (lowercase, stripped)
            field_map = {name.strip().lower(): name for name in reader.fieldnames}

            def get_val(row: dict, *candidates: str) -> str:
                for c in candidates:
                    if c in field_map:
                        return row.get(field_map[c], "").strip()
                return ""

            # Cache categories for quick lookup
            cats = {c.name.lower(): c for c in self.cat_repo.get_all()}

            tx_batch: List[Transaction] = []

            for row_idx, row in enumerate(reader, start=2):
                date_str = get_val(row, "date", "date (yyyy-mm-dd)")
                type_str = get_val(row, "type").lower()
                cat_str = get_val(row, "category", "category name")
                amount_str = get_val(row, "amount", "total")
                desc_str = get_val(row, "description", "note", "memo")

                if not date_str or not amount_str:
                    errors.append(f"Row {row_idx}: Missing required Date or Amount.")
                    continue

                # Parse & normalize date
                norm_date = self._parse_date_string(date_str)
                if not norm_date:
                    errors.append(f"Row {row_idx}: Invalid date format '{date_str}'. Use YYYY-MM-DD.")
                    continue

                # Parse type
                if type_str not in ("income", "expense"):
                    # Guess by amount sign or default to expense
                    try:
                        val = float(amount_str)
                        type_str = "income" if val > 0 else "expense"
                        amount_str = str(abs(val))
                    except ValueError:
                        type_str = "expense"

                # Parse amount
                try:
                    clean_amt_str = amount_str.replace(",", "").replace("$", "").replace("MAD", "").strip()
                    amount = abs(float(clean_amt_str))
                    if amount <= 0:
                        errors.append(f"Row {row_idx}: Amount must be positive.")
                        continue
                except ValueError:
                    errors.append(f"Row {row_idx}: Cannot parse amount '{amount_str}'.")
                    continue

                # Match or create category
                cat_key = cat_str.lower() if cat_str else "other"
                if cat_key in cats:
                    category = cats[cat_key]
                else:
                    # Create new category on the fly
                    new_cat = Category(
                        id=None,
                        name=cat_str or "Other",
                        type=type_str,
                        color="#6B7280",
                        icon="tag",
                    )
                    category = self.cat_repo.create(new_cat)
                    cats[cat_key] = category

                tx = Transaction(
                    id=None,
                    type=type_str,
                    amount=amount,
                    category_id=category.id,  # type: ignore
                    date=norm_date,
                    description=desc_str,
                )
                tx_batch.append(tx)

            if tx_batch:
                imported_count = self.tx_repo.create_many(tx_batch)

        return imported_count, errors

    def _parse_date_string(self, raw_date: str) -> Optional[str]:
        """Attempt to parse common date formats to 'YYYY-MM-DD'."""
        formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%Y/%m/%d",
            "%d-%m-%Y",
            "%Y.%m.%d",
        ]
        raw = raw_date.strip()
        for fmt in formats:
            try:
                dt = datetime.strptime(raw, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                pass
        return None

    def export_transactions_to_csv(self, file_path: str, transactions: List[Transaction]) -> None:
        """Export a list of transactions to CSV format."""
        with open(file_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Date", "Type", "Category", "Amount", "Currency", "Description"])
            currency = self.get_currency()
            for t in transactions:
                writer.writerow([
                    t.id,
                    t.date,
                    t.type,
                    t.category_name,
                    f"{t.amount:.2f}",
                    currency,
                    t.description,
                ])
