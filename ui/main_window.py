"""
SpendWise Main Window
Private-Bank styled main window featuring:
- Midnight navy sidebar with gold active indicators and vector icons
- QStackedWidget page transitions
- Global keyboard shortcuts:
  - Ctrl+N (Cmd+N): New Transaction
  - Ctrl+F (Cmd+F): Focus Search in Transactions
  - Ctrl+E (Cmd+E): Go to Reports
- Startup recurring transactions processing
- Real-time theme switching (Light / Dark)
- Responsive layout (min 1100x700)
"""

from __future__ import annotations
import os
from typing import List, Optional
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from core.models import Transaction
from core.services import FinanceService
from ui.pages.budgets import BudgetsPage
from ui.pages.dashboard import DashboardPage
from ui.pages.reports import ReportsPage
from ui.pages.settings import SettingsPage
from ui.pages.statistics import StatisticsPage
from ui.pages.transactions import TransactionsPage
from ui.theme import COLORS, ThemeManager
from ui.widgets.toast import show_toast
from ui.widgets.transaction_dialog import TransactionDialog


ASSETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets"))
ICONS_DIR = os.path.join(ASSETS_DIR, "icons")


class SidebarButton(QPushButton):
    """Custom sidebar navigation button with gold indicator when active."""

    def __init__(self, text: str, icon_name: str, index: int, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.index = index
        self.setText(f"  {text}")
        self.setCheckable(True)
        self.setFixedHeight(46)
        self.setFont(ThemeManager.font_sans(size=10, bold=True))
        self.setCursor(Qt.PointingHandCursor)

        icon_path = os.path.join(ICONS_DIR, f"{icon_name}.svg")
        if os.path.exists(icon_path):
            self.setIcon(QIcon(icon_path))
            self.setIconSize(QSize(18, 18))

        self.update_style(False)

    def update_style(self, active: bool) -> None:
        if active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS.NAVY_LIGHT};
                    color: #FFFFFF;
                    border: none;
                    border-left: 4px solid {COLORS.GOLD};
                    text-align: left;
                    padding-left: 20px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: #A0ABC0;
                    border: none;
                    border-left: 4px solid transparent;
                    text-align: left;
                    padding-left: 20px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS.NAVY_HOVER};
                    color: #FFFFFF;
                }}
            """)


class MainWindow(QMainWindow):
    """SpendWise Application Main Window."""

    def __init__(self, service: FinanceService) -> None:
        super().__init__()
        self.service = service
        self.setWindowTitle("SpendWise – Expense & Wealth Manager")
        self.setMinimumSize(1100, 720)
        self.resize(1280, 800)

        # Set initial theme
        current_theme = self.service.get_theme()
        ThemeManager.set_theme(current_theme)

        self._setup_ui()
        self._setup_shortcuts()
        self._process_startup_tasks()

    def _setup_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Left Sidebar
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(240)
        self.sidebar.setStyleSheet(f"background-color: {COLORS.NAVY}; border-right: 1px solid #18273E;")

        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 24, 0, 20)
        sidebar_layout.setSpacing(6)

        # Brand / Logo Header
        brand_box = QWidget()
        bb_layout = QVBoxLayout(brand_box)
        bb_layout.setContentsMargins(24, 0, 24, 18)
        bb_layout.setSpacing(2)

        lbl_brand = QLabel("SPENDWISE")
        lbl_brand.setFont(ThemeManager.font_serif(size=18, bold=True))
        lbl_brand.setStyleSheet(f"color: #FFFFFF; letter-spacing: 1.5px;")

        lbl_tagline = QLabel("PRIVATE EXPENSE MANAGER")
        lbl_tagline.setFont(ThemeManager.font_sans(size=7, bold=True))
        lbl_tagline.setStyleSheet(f"color: {COLORS.GOLD}; letter-spacing: 1px;")

        bb_layout.addWidget(lbl_brand)
        bb_layout.addWidget(lbl_tagline)
        sidebar_layout.addWidget(brand_box)

        # Divider line
        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet(f"background-color: {COLORS.NAVY_LIGHT}; max-height: 1px; border: none; margin: 0 16px 12px 16px;")
        sidebar_layout.addWidget(div)

        # Navigation Buttons
        self.nav_buttons: List[SidebarButton] = []
        nav_items = [
            ("Dashboard", "dashboard", 0),
            ("Transactions", "transactions", 1),
            ("Budgets & Goals", "budgets", 2),
            ("Analytics & Trends", "statistics", 3),
            ("Statements & Reports", "reports", 4),
            ("System Settings", "settings", 5),
        ]

        for label, icon_name, idx in nav_items:
            btn = SidebarButton(label, icon_name, idx, self.sidebar)
            btn.clicked.connect(lambda _, index=idx: self.switch_page(index))
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        sidebar_layout.addStretch()

        # Sidebar Footer
        footer_box = QWidget()
        fb_layout = QVBoxLayout(footer_box)
        fb_layout.setContentsMargins(24, 12, 24, 0)
        fb_layout.setSpacing(4)

        lbl_user = QLabel("Valued Client")
        lbl_user.setFont(ThemeManager.font_sans(size=9, bold=True))
        lbl_user.setStyleSheet("color: #FFFFFF;")

        lbl_status = QLabel(f"Base: {self.service.get_currency()} • v1.0.0")
        lbl_status.setFont(ThemeManager.font_sans(size=8))
        lbl_status.setStyleSheet("color: #A0ABC0;")

        fb_layout.addWidget(lbl_user)
        fb_layout.addWidget(lbl_status)
        sidebar_layout.addWidget(footer_box)

        root_layout.addWidget(self.sidebar)

        # 2. Page Stack (QStackedWidget)
        self.page_stack = QStackedWidget()

        self.page_dashboard = DashboardPage(self.service, self)
        self.page_transactions = TransactionsPage(self.service, self)
        self.page_budgets = BudgetsPage(self.service, self)
        self.page_statistics = StatisticsPage(self.service, self)
        self.page_reports = ReportsPage(self.service, self)
        self.page_settings = SettingsPage(self.service, self)

        # Connect inter-page signals
        self.page_dashboard.request_new_transaction.connect(self._open_new_transaction_dialog)
        self.page_transactions.data_changed.connect(self._on_global_data_changed)
        self.page_budgets.data_changed.connect(self._on_global_data_changed)
        self.page_settings.data_changed.connect(self._on_global_data_changed)
        self.page_settings.theme_changed.connect(self._on_theme_changed)
        self.page_settings.currency_changed.connect(self._on_currency_changed)

        self.page_stack.addWidget(self.page_dashboard)
        self.page_stack.addWidget(self.page_transactions)
        self.page_stack.addWidget(self.page_budgets)
        self.page_stack.addWidget(self.page_statistics)
        self.page_stack.addWidget(self.page_reports)
        self.page_stack.addWidget(self.page_settings)

        root_layout.addWidget(self.page_stack, stretch=1)

        # Set initial page
        self.switch_page(0)
        self._apply_global_theme()

    def _setup_shortcuts(self) -> None:
        """Register Ctrl+N, Ctrl+F, Ctrl+E shortcuts."""
        # Ctrl+N (or Cmd+N): New Transaction
        sc_new = QShortcut(QKeySequence.New, self)
        sc_new.activated.connect(self._open_new_transaction_dialog)

        # Ctrl+F (or Cmd+F): Focus search in transactions
        sc_find = QShortcut(QKeySequence.Find, self)
        sc_find.activated.connect(self._shortcut_search)

        # Ctrl+E (or Cmd+E): Switch to reports
        sc_export = QShortcut(QKeySequence("Ctrl+E"), self)
        sc_export.activated.connect(lambda: self.switch_page(4))

    def _process_startup_tasks(self) -> None:
        """Auto-generate recurring transactions for current month on app start."""
        count = self.service.process_recurring_for_month()
        if count > 0:
            show_toast(
                self,
                f"Auto-generated {count} recurring transaction(s) for this month.",
                "Recurring Rules Processed",
                level="info",
                duration_ms=5000,
            )
            self._on_global_data_changed()

    def switch_page(self, index: int) -> None:
        """Switch stacked page and update active sidebar styling."""
        if 0 <= index < self.page_stack.count():
            self.page_stack.setCurrentIndex(index)
            for i, btn in enumerate(self.nav_buttons):
                btn.update_style(i == index)

            # Refresh page data when switched to
            current_widget = self.page_stack.currentWidget()
            if hasattr(current_widget, "reload_data"):
                current_widget.reload_data()
            elif hasattr(current_widget, "refresh_data"):
                current_widget.refresh_data()
            elif hasattr(current_widget, "update_preview"):
                current_widget.update_preview()

    def _shortcut_search(self) -> None:
        """Switch to Transactions page and focus search field."""
        self.switch_page(1)
        self.page_transactions.focus_search()

    def _open_new_transaction_dialog(self) -> None:
        """Open transaction dialog from anywhere in the app."""
        cats = self.service.cat_repo.get_all()
        dlg = TransactionDialog(categories=cats, currency=self.service.get_currency(), parent=self)
        if dlg.exec():
            tx = dlg.result_transaction
            if tx:
                self.service.tx_repo.create(tx)
                self._on_global_data_changed()
                show_toast(self, "Transaction added to ledger.", "Recorded", level="success")

    def _on_global_data_changed(self) -> None:
        """Refresh active page data and dashboard when database state changes."""
        self.page_dashboard.refresh_data()
        self.page_transactions.reload_data()
        self.page_budgets.reload_data()
        self.page_statistics.reload_data()
        self.page_reports.update_preview()

    def _on_theme_changed(self, theme_name: str) -> None:
        """Apply theme change dynamically across the application."""
        ThemeManager.set_theme(theme_name)
        self._apply_global_theme()

        self.page_dashboard.apply_theme()
        self.page_transactions.apply_theme()
        self.page_budgets.apply_theme()
        self.page_statistics.apply_theme()
        self.page_reports.apply_theme()
        self.page_settings.apply_theme()

        # Update sidebar active style
        curr_idx = self.page_stack.currentIndex()
        for i, btn in enumerate(self.nav_buttons):
            btn.update_style(i == curr_idx)

    def _on_currency_changed(self, currency_code: str) -> None:
        """Update currency throughout the app."""
        self.service.set_currency(currency_code)
        self._on_global_data_changed()

    def _apply_global_theme(self) -> None:
        """Apply the global stylesheet to the QApplication."""
        qss = ThemeManager.get_stylesheet()
        app = QApplication.instance()
        if app:
            app.setStyleSheet(qss)
