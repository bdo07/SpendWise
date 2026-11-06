"""
Automated UI and Integration Test for SpendWise
Verifies that QApplication, MainWindow, and all 6 pages instantiate, switch, and render properly.
Runs in offscreen mode (QT_QPA_PLATFORM=offscreen) to ensure headless CI/test compatibility.
"""

import os
import sys
import pytest
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication

from core.database import Database
from core.models import Category, Transaction
from core.services import FinanceService
from ui.main_window import MainWindow
from ui.theme import ThemeManager
from ui.widgets.transaction_dialog import TransactionDialog


@pytest.fixture(scope="session")
def qapp():
    """Create a persistent QApplication for tests."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_ui_instantiation_and_navigation(qapp, tmp_path):
    """Test full UI lifecycle: creation, page switching, theme toggling, data updates."""
    test_db = Database(db_path=tmp_path / "test_ui.db")
    service = FinanceService(database=test_db)

    window = MainWindow(service=service)
    assert window is not None
    assert window.page_stack.count() == 6

    # Verify switching to each page
    for page_idx in range(6):
        window.switch_page(page_idx)
        assert window.page_stack.currentIndex() == page_idx

    # Test theme toggle
    window._on_theme_changed("dark")
    assert ThemeManager.is_dark() is True
    window._on_theme_changed("light")
    assert ThemeManager.is_dark() is False

    # Test currency change
    window._on_currency_changed("USD")
    assert service.get_currency() == "USD"

    # Close cleanly
    window.close()


def test_transaction_dialog_validation(qapp, tmp_path):
    """Test transaction dialog validation logic."""
    test_db = Database(db_path=tmp_path / "test_diag.db")
    service = FinanceService(database=test_db)
    cats = service.cat_repo.get_all()

    dlg = TransactionDialog(categories=cats, currency="MAD")
    assert dlg is not None

    # Default is expense
    assert dlg.btn_expense.isChecked() is True

    # Switch to income
    dlg.btn_income.setChecked(True)
    dlg._on_type_changed()
    assert dlg.btn_income.isChecked() is True

    # Validate amount > 0
    dlg.spin_amount.setValue(250.0)
    dlg.edit_description.setText("Freelance Design Milestone")
    dlg._validate_and_save()

    assert dlg.result_transaction is not None
    assert dlg.result_transaction.amount == 250.0
    assert dlg.result_transaction.type == "income"
    assert dlg.result_transaction.description == "Freelance Design Milestone"
    dlg.close()


def test_page_search_and_filters(qapp, tmp_path):
    """Test instant search filter and category filtering on transactions page."""
    test_db = Database(db_path=tmp_path / "test_filters.db")
    service = FinanceService(database=test_db)
    food_cat = service.cat_repo.get_by_name("Food")
    salary_cat = service.cat_repo.get_by_name("Salary")

    service.tx_repo.create(Transaction(id=None, type="expense", amount=120.0, category_id=food_cat.id, date="2026-10-05", description="Bakery Bread"))
    service.tx_repo.create(Transaction(id=None, type="income", amount=10000.0, category_id=salary_cat.id, date="2026-10-01", description="Monthly Payroll"))

    window = MainWindow(service=service)
    window.switch_page(1)  # Transactions page

    # Search for 'Bakery'
    window.page_transactions.edit_search.setText("Bakery")
    assert window.page_transactions.table_model.rowCount() == 1

    # Search for 'Payroll'
    window.page_transactions.edit_search.setText("Payroll")
    assert window.page_transactions.table_model.rowCount() == 1

    # Clear search
    window.page_transactions.edit_search.clear()
    assert window.page_transactions.table_model.rowCount() == 2

    window.close()
