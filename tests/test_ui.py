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
from core.services import FinanceService
from ui.main_window import MainWindow
from ui.theme import ThemeManager


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
