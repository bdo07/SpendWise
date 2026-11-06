"""
SpendWise – Expense & Wealth Manager
Main application entry point.

Run with:
    python main.py
"""

from __future__ import annotations
import sys
import os
from pathlib import Path

# Ensure root directory is on Python path
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from core.database import db
from core.services import FinanceService
from ui.main_window import MainWindow
from ui.theme import ThemeManager


def main() -> None:
    # Ensure correct Qt application attributes
    QApplication.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings, True)

    app = QApplication(sys.argv)
    app.setApplicationName("SpendWise")
    app.setOrganizationName("SpendWise Private Wealth")

    # Set default application font
    default_font = ThemeManager.font_sans(size=10)
    app.setFont(default_font)

    # Initialize database & default seed
    db.init_db()

    # Initialize business services
    service = FinanceService(database=db)

    # Apply saved theme (Light or Dark)
    saved_theme = service.get_theme()
    ThemeManager.set_theme(saved_theme)
    app.setStyleSheet(ThemeManager.get_stylesheet())

    # Create & display main window
    window = MainWindow(service=service)

    # App icon if available
    icon_path = CURRENT_DIR / "assets" / "icons" / "wallet.svg"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
