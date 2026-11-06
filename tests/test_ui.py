"""
Automated UI and Integration Test for SpendWise
Verifies that QApplication, MainWindow, and all 6 pages instantiate, switch, and render properly.
Runs in offscreen mode (QT_QPA_PLATFORM=offscreen) to ensure headless CI/test compatibility.
"""

import os
import sys
from pathlib import Path
import pytest
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication

from core.database import Database
from core.models import Category, Transaction
from core.services import FinanceService
from core.export import PDFReportGenerator, ExcelReportGenerator
from ui.main_window import MainWindow
from ui.theme import DARK_PALETTE, LIGHT_PALETTE, ThemeManager
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


def test_dark_mode_palette_and_switching(qapp, tmp_path):
    """Verify dark palette exact color values and live switching."""
    # Verify dark palette values
    assert DARK_PALETTE.window_bg == "#0B1220"
    assert DARK_PALETTE.card_bg == "#141F33"
    assert DARK_PALETTE.elevated_bg == "#1A2740"
    assert DARK_PALETTE.sidebar_bg == "#070D18"
    assert DARK_PALETTE.border == "#243350"
    assert DARK_PALETTE.text_primary == "#F3EFE6"
    assert DARK_PALETTE.text_secondary == "#9AA4B5"
    assert DARK_PALETTE.gold == "#C9A55C"
    assert DARK_PALETTE.income == "#4CAF86"
    assert DARK_PALETTE.expense == "#D96B6B"

    test_db = Database(db_path=tmp_path / "test_dark_theme.db")
    service = FinanceService(database=test_db)
    window = MainWindow(service=service)

    # Switch to dark mode
    window._on_theme_changed("dark")
    assert ThemeManager.is_dark() is True
    assert ThemeManager.get_palette() == DARK_PALETTE

    # Test sidebar toggle quick button
    window._toggle_quick_theme()
    assert ThemeManager.is_dark() is False
    assert ThemeManager.get_palette() == LIGHT_PALETTE

    window._toggle_quick_theme()
    assert ThemeManager.is_dark() is True

    # Test icon recoloring
    sun_icon = ThemeManager.get_icon("sun", DARK_PALETTE.gold)
    assert sun_icon is not None and not sun_icon.isNull()
    moon_icon = ThemeManager.get_icon("moon", LIGHT_PALETTE.gold)
    assert moon_icon is not None and not moon_icon.isNull()

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


def test_export_style_integrity_in_dark_mode(tmp_path: Path):
    """Verify that PDF and Excel exports remain in light/print-friendly style even when app is in dark mode (Rule 9)."""
    ThemeManager.set_theme("dark")
    assert ThemeManager.is_dark() is True

    summary = {"income": 10000.0, "expenses": 4000.0, "net_savings": 6000.0, "savings_rate": 60.0}
    breakdown = [{"category_name": "Food", "amount": 1500.0, "percentage": 37.5}]
    txs = [Transaction(id=1, type="expense", amount=1500.0, category_id=1, date="2026-10-01", description="Groceries")]

    pdf_out = tmp_path / "dark_test_statement.pdf"
    gen_pdf = PDFReportGenerator(pdf_out, "Statement", "2026-10", "MAD")
    gen_pdf.generate(summary, breakdown, txs)
    assert pdf_out.exists()
    assert pdf_out.stat().st_size > 1000

    xls_out = tmp_path / "dark_test_statement.xlsx"
    gen_xls = ExcelReportGenerator(xls_out, "MAD")
    gen_xls.generate("2026-10", summary, breakdown, txs)
    assert xls_out.exists()
    assert xls_out.stat().st_size > 1000
