"""
Unit tests for SpendWise core layer (database, repositories, services, and export).
Tested with Pytest in an isolated SQLite database.
"""

import os
import tempfile
from pathlib import Path
import pytest

from core.database import Database
from core.models import Budget, Category, Goal, Recurring, Transaction
from core.repositories import (
    BudgetRepository,
    CategoryRepository,
    GoalRepository,
    RecurringRepository,
    SettingsRepository,
    TransactionRepository,
)
from core.services import FinanceService
from core.export import PDFReportGenerator, ExcelReportGenerator


@pytest.fixture
def temp_db(tmp_path: Path) -> Database:
    """Create an isolated test database in a temporary directory."""
    db_file = tmp_path / "test_spendwise.db"
    return Database(db_path=db_file)


@pytest.fixture
def service(temp_db: Database) -> FinanceService:
    """Create a FinanceService backed by the isolated test database."""
    return FinanceService(database=temp_db)


def test_database_initialization_and_seed_data(temp_db: Database):
    """Test schema creation and default seeded categories and settings."""
    cat_repo = CategoryRepository(temp_db)
    cats = cat_repo.get_all()
    assert len(cats) >= 11
    names = [c.name for c in cats]
    assert "Food" in names
    assert "Transport" in names
    assert "Salary" in names

    settings_repo = SettingsRepository(temp_db)
    assert settings_repo.get("currency") == "MAD"
    assert settings_repo.get("theme") == "light"


def test_transaction_crud_and_monthly_totals(temp_db: Database, service: FinanceService):
    """Test creating, reading, updating and deleting transactions, plus monthly totals."""
    cat_repo = CategoryRepository(temp_db)
    food_cat = cat_repo.get_by_name("Food")
    salary_cat = cat_repo.get_by_name("Salary")
    assert food_cat is not None
    assert salary_cat is not None

    tx_repo = TransactionRepository(temp_db)

    # Add income transaction
    tx_income = Transaction(
        id=None,
        type="income",
        amount=15000.0,
        category_id=salary_cat.id,
        date="2026-10-01",
        description="October Monthly Salary",
    )
    tx_repo.create(tx_income)
    assert tx_income.id is not None

    # Add expense transaction
    tx_expense = Transaction(
        id=None,
        type="expense",
        amount=2500.0,
        category_id=food_cat.id,
        date="2026-10-05",
        description="Supermarket Groceries",
    )
    tx_repo.create(tx_expense)

    # Check monthly totals
    income, expense = tx_repo.get_monthly_totals("2026-10")
    assert income == 15000.0
    assert expense == 2500.0

    # Summary
    summary = service.get_monthly_summary("2026-10")
    assert summary.income == 15000.0
    assert summary.expenses == 2500.0
    assert summary.net_savings == 12500.0
    assert summary.savings_rate == 83.3


def test_budget_calculations_and_threshold_alerts(temp_db: Database, service: FinanceService):
    """Test budget calculation at <70%, 70-90%, 90-100%, and >100% thresholds."""
    cat_repo = CategoryRepository(temp_db)
    tx_repo = TransactionRepository(temp_db)
    budget_repo = BudgetRepository(temp_db)

    food_cat = cat_repo.get_by_name("Food")
    month = "2026-10"

    # Set budget of 1,000 MAD for Food
    budget = Budget(id=None, month=month, category_id=food_cat.id, amount=1000.0)
    budget_repo.set_budget(budget)

    # 1. Normal state (<70%): spend 500
    tx1 = Transaction(id=None, type="expense", amount=500.0, category_id=food_cat.id, date="2026-10-02")
    tx_repo.create(tx1)

    statuses = service.get_budget_statuses(month)
    food_st = next(s for s in statuses if s.budget.category_id == food_cat.id)
    assert food_st.spent == 500.0
    assert food_st.percentage == 50.0
    assert food_st.remaining == 500.0
    assert food_st.alert_level == "normal"
    assert len(service.get_active_budget_alerts(month)) == 0

    # 2. Warning state (70% - 90%): spend 250 more (total 750 / 1000 = 75%)
    tx2 = Transaction(id=None, type="expense", amount=250.0, category_id=food_cat.id, date="2026-10-08")
    tx_repo.create(tx2)

    statuses = service.get_budget_statuses(month)
    food_st = next(s for s in statuses if s.budget.category_id == food_cat.id)
    assert food_st.spent == 750.0
    assert food_st.percentage == 75.0
    assert food_st.alert_level == "warning"
    alerts = service.get_active_budget_alerts(month)
    assert len(alerts) == 1
    assert alerts[0]["level"] == "warning"

    # 3. Critical state (90% - 100%): spend 200 more (total 950 / 1000 = 95%)
    tx3 = Transaction(id=None, type="expense", amount=200.0, category_id=food_cat.id, date="2026-10-15")
    tx_repo.create(tx3)

    statuses = service.get_budget_statuses(month)
    food_st = next(s for s in statuses if s.budget.category_id == food_cat.id)
    assert food_st.spent == 950.0
    assert food_st.percentage == 95.0
    assert food_st.alert_level == "critical"
    alerts = service.get_active_budget_alerts(month)
    assert len(alerts) == 1
    assert alerts[0]["level"] == "critical"

    # 4. Exceeded state (>100%): spend 100 more (total 1050 / 1000 = 105%)
    tx4 = Transaction(id=None, type="expense", amount=100.0, category_id=food_cat.id, date="2026-10-20")
    tx_repo.create(tx4)

    statuses = service.get_budget_statuses(month)
    food_st = next(s for s in statuses if s.budget.category_id == food_cat.id)
    assert food_st.spent == 1050.0
    assert food_st.percentage == 105.0
    assert food_st.remaining == -50.0
    assert food_st.alert_level == "exceeded"
    alerts = service.get_active_budget_alerts(month)
    assert len(alerts) == 1
    assert alerts[0]["level"] == "exceeded"


def test_recurring_transactions_generation_and_idempotence(temp_db: Database, service: FinanceService):
    """Test recurring rule execution, date capping, and duplicate prevention."""
    cat_repo = CategoryRepository(temp_db)
    rec_repo = RecurringRepository(temp_db)
    tx_repo = TransactionRepository(temp_db)

    rent_cat = cat_repo.get_by_name("Rent")
    salary_cat = cat_repo.get_by_name("Salary")

    rec_repo.create(Recurring(id=None, type="expense", amount=4500.0, category_id=rent_cat.id, description="Apartment Rent", day_of_month=1, active=1))
    rec_repo.create(Recurring(id=None, type="income", amount=20000.0, category_id=salary_cat.id, description="Base Salary", day_of_month=28, active=1))

    # Process for February 2026
    count1 = service.process_recurring_for_month("2026-02")
    assert count1 == 2

    txs = tx_repo.get_all(start_date="2026-02-01", end_date="2026-02-28")
    assert len(txs) == 2
    assert any(t.amount == 4500.0 and t.date == "2026-02-01" for t in txs)
    assert any(t.amount == 20000.0 and t.date == "2026-02-28" for t in txs)

    # Calling process_recurring_for_month again must NOT duplicate
    count2 = service.process_recurring_for_month("2026-02")
    assert count2 == 0
    txs_after = tx_repo.get_all(start_date="2026-02-01", end_date="2026-02-28")
    assert len(txs_after) == 2


def test_csv_import_and_export(temp_db: Database, service: FinanceService, tmp_path: Path):
    """Test importing transactions from a CSV file and exporting back."""
    csv_file = tmp_path / "import_test.csv"
    csv_content = (
        "Date,Type,Category,Amount,Description\n"
        "2026-10-10,expense,Food,150.50,Dinner with colleagues\n"
        "2026-10-12,income,Freelance,3200.00,Client website contract\n"
        "2026-10-15,expense,Gym,400.00,Fitness pass\n"
    )
    csv_file.write_text(csv_content, encoding="utf-8")

    imported, errors = service.import_transactions_from_csv(str(csv_file))
    assert imported == 3
    assert len(errors) == 0

    gym_cat = CategoryRepository(temp_db).get_by_name("Gym")
    assert gym_cat is not None

    txs = TransactionRepository(temp_db).get_all(start_date="2026-10-10", end_date="2026-10-15")
    assert len(txs) == 3

    export_file = tmp_path / "export_test.csv"
    service.export_transactions_to_csv(str(export_file), txs)
    assert export_file.exists()
    content = export_file.read_text(encoding="utf-8")
    assert "Dinner with colleagues" in content
    assert "Client website contract" in content


def test_savings_goals(temp_db: Database):
    """Test savings goal progress and completion check."""
    goal_repo = GoalRepository(temp_db)
    goal = goal_repo.create(Goal(id=None, name="Emergency Fund", target_amount=50000.0, saved_amount=10000.0, deadline="2027-12-31"))
    assert goal.id is not None
    assert goal.progress_percentage == 20.0
    assert not goal.is_completed

    goal_repo.add_savings(goal.id, 40000.0)
    updated = goal_repo.get_by_id(goal.id)
    assert updated.saved_amount == 50000.0
    assert updated.progress_percentage == 100.0
    assert updated.is_completed


def test_pdf_and_excel_export_generation(temp_db: Database, service: FinanceService, tmp_path: Path):
    """Test that PDF and Excel exports run without errors and create valid non-empty files."""
    cat_repo = CategoryRepository(temp_db)
    tx_repo = TransactionRepository(temp_db)
    food_cat = cat_repo.get_by_name("Food")
    salary_cat = cat_repo.get_by_name("Salary")

    tx_repo.create(Transaction(id=None, type="income", amount=12000.0, category_id=salary_cat.id, date="2026-10-01", description="Salary"))
    tx_repo.create(Transaction(id=None, type="expense", amount=1800.0, category_id=food_cat.id, date="2026-10-04", description="Market"))

    summary = service.get_monthly_summary("2026-10").__dict__
    category_breakdown = service.get_category_breakdown("2026-10")
    txs = tx_repo.get_all()

    pdf_path = tmp_path / "statement.pdf"
    pdf_gen = PDFReportGenerator(pdf_path, title="Monthly Statement", period="2026-10", currency="MAD")
    pdf_gen.generate(summary, category_breakdown, txs)
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 1000

    xls_path = tmp_path / "statement.xlsx"
    xls_gen = ExcelReportGenerator(xls_path, currency="MAD")
    xls_gen.generate("2026-10", summary, category_breakdown, txs)
    assert xls_path.exists()
    assert xls_path.stat().st_size > 1000


def test_category_referential_integrity(temp_db: Database):
    """Test that deleting a category that has transactions is prevented."""
    cat_repo = CategoryRepository(temp_db)
    tx_repo = TransactionRepository(temp_db)

    cat = cat_repo.create(Category(id=None, name="TestDelete", type="expense", color="#123456", icon="tag"))
    assert cat_repo.has_transactions(cat.id) is False

    # Attach transaction
    tx_repo.create(Transaction(id=None, type="expense", amount=100.0, category_id=cat.id, date="2026-10-01"))
    assert cat_repo.has_transactions(cat.id) is True

    # Delete should fail gracefully
    deleted = cat_repo.delete(cat.id)
    assert deleted is False
    assert cat_repo.get_by_id(cat.id) is not None


def test_budget_copy_from_previous_month(temp_db: Database):
    """Test copying budgets from one month to another."""
    budget_repo = BudgetRepository(temp_db)
    cat_repo = CategoryRepository(temp_db)
    food_cat = cat_repo.get_by_name("Food")

    # Set up January budgets
    budget_repo.set_budget(Budget(id=None, month="2026-01", category_id=None, amount=12000.0))
    budget_repo.set_budget(Budget(id=None, month="2026-01", category_id=food_cat.id, amount=3000.0))

    # Copy to February
    count = budget_repo.copy_budgets_from_previous_month("2026-01", "2026-02")
    assert count == 2

    feb_budgets = budget_repo.get_all_for_month("2026-02")
    assert len(feb_budgets) == 2
    assert any(b.category_id is None and b.amount == 12000.0 for b in feb_budgets)
    assert any(b.category_id == food_cat.id and b.amount == 3000.0 for b in feb_budgets)
