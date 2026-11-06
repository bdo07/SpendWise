"""
SpendWise Main Window
Private-Bank styled main window featuring:
- Midnight navy / deep obsidian sidebar with gold active indicators and recolored SVG vector icons
- QStackedWidget page transitions
- Theme toggle in sidebar footer (Sun/Moon button) + Settings page integration
- System theme detection (follows OS) with live runtime updates without app restart
- Smooth ~150ms theme transition
- Global keyboard shortcuts:
  - Ctrl+N (Cmd+N): New Transaction
  - Ctrl+F (Cmd+F): Focus Search in Transactions
  - Ctrl+E (Cmd+E): Go to Reports
- Startup recurring transactions processing
- Responsive layout (min 1100x720)
"""

from __future__ import annotations
import os
from typing import List, Optional
from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSize, Qt
from PySide6.QtGui import QAction, QGuiApplication, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsOpacityEffect,
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
from ui.theme import ThemeManager
from ui.widgets.toast import show_toast
from ui.widgets.transaction_dialog import TransactionDialog


class SidebarButton(QPushButton):
    """Custom sidebar navigation button with gold indicator and theme-colored icon."""

    def __init__(self, text: str, icon_name: str, index: int, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.index = index
        self.icon_name = icon_name
        self.setText(f"  {text}")
        self.setCheckable(True)
        self.setFixedHeight(46)
        self.setFont(ThemeManager.font_sans(size=10, bold=True))
        self.setCursor(Qt.PointingHandCursor)
        self.update_style(False)

    def update_style(self, active: bool) -> None:
        p = ThemeManager.get_palette()
        icon_color = p.gold if active else p.sidebar_text
        self.setIcon(ThemeManager.get_icon(self.icon_name, icon_color))
        self.setIconSize(QSize(18, 18))

        if active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {p.sidebar_active};
                    color: {p.sidebar_text_active};
                    border: none;
                    border-left: 4px solid {p.gold};
                    text-align: left;
                    padding-left: 20px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {p.sidebar_text};
                    border: none;
                    border-left: 4px solid transparent;
                    text-align: left;
                    padding-left: 20px;
                }}
                QPushButton:hover {{
                    background-color: {p.sidebar_hover};
                    color: {p.sidebar_text_active};
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

        # Initialize ThemeManager with saved preference ('system', 'light', or 'dark')
        saved_theme = self.service.get_theme()
        ThemeManager.init(saved_theme)

        self._setup_ui()
        self._setup_shortcuts()
        self._setup_system_theme_listener()
        self._process_startup_tasks()

    def _setup_ui(self) -> None:
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        root_layout = QHBoxLayout(self.central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        p = ThemeManager.get_palette()

        # 1. Left Sidebar
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(240)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 24, 0, 16)
        sidebar_layout.setSpacing(6)

        # Brand / Logo Header
        brand_box = QWidget()
        bb_layout = QVBoxLayout(brand_box)
        bb_layout.setContentsMargins(24, 0, 24, 18)
        bb_layout.setSpacing(2)

        self.lbl_brand = QLabel("SPENDWISE")
        self.lbl_brand.setFont(ThemeManager.font_serif(size=18, bold=True))

        self.lbl_tagline = QLabel("PRIVATE EXPENSE MANAGER")
        self.lbl_tagline.setFont(ThemeManager.font_sans(size=7, bold=True))

        bb_layout.addWidget(self.lbl_brand)
        bb_layout.addWidget(self.lbl_tagline)
        sidebar_layout.addWidget(brand_box)

        # Divider line
        self.sidebar_div = QFrame()
        self.sidebar_div.setFrameShape(QFrame.HLine)
        sidebar_layout.addWidget(self.sidebar_div)

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

        # Sidebar Footer with Sun/Moon Toggle Button (Rule 4)
        footer_box = QWidget()
        fb_layout = QVBoxLayout(footer_box)
        fb_layout.setContentsMargins(24, 12, 24, 8)
        fb_layout.setSpacing(8)

        # Theme quick toggle row
        toggle_row = QHBoxLayout()
        toggle_row.setContentsMargins(0, 0, 0, 0)
        toggle_row.setSpacing(8)

        self.btn_theme_toggle = QPushButton()
        self.btn_theme_toggle.setFixedSize(32, 32)
        self.btn_theme_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_theme_toggle.setToolTip("Toggle Theme (Light / Dark)")
        self.btn_theme_toggle.clicked.connect(self._toggle_quick_theme)
        toggle_row.addWidget(self.btn_theme_toggle)

        self.lbl_theme_mode = QLabel()
        self.lbl_theme_mode.setFont(ThemeManager.font_sans(size=8, bold=True))
        toggle_row.addWidget(self.lbl_theme_mode)
        toggle_row.addStretch()
        fb_layout.addLayout(toggle_row)

        self.lbl_user = QLabel("Valued Client")
        self.lbl_user.setFont(ThemeManager.font_sans(size=9, bold=True))

        self.lbl_status = QLabel(f"Base: {self.service.get_currency()} • v1.0.0")
        self.lbl_status.setFont(ThemeManager.font_sans(size=8))

        fb_layout.addWidget(self.lbl_user)
        fb_layout.addWidget(self.lbl_status)
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
        self._apply_theme_to_ui(animate=False)

    def _setup_shortcuts(self) -> None:
        """Register Ctrl+N, Ctrl+F, Ctrl+E shortcuts."""
        sc_new = QShortcut(QKeySequence.New, self)
        sc_new.activated.connect(self._open_new_transaction_dialog)

        sc_find = QShortcut(QKeySequence.Find, self)
        sc_find.activated.connect(self._shortcut_search)

        sc_export = QShortcut(QKeySequence("Ctrl+E"), self)
        sc_export.activated.connect(lambda: self.switch_page(4))

    def _setup_system_theme_listener(self) -> None:
        """Listen to OS color scheme changes if mode is 'system'."""
        app = QGuiApplication.instance()
        if app and hasattr(app, "styleHints"):
            hints = app.styleHints()
            if hasattr(hints, "colorSchemeChanged"):
                hints.colorSchemeChanged.connect(self._on_system_scheme_changed)

    def _on_system_scheme_changed(self) -> None:
        """Handle OS dark/light switch when in 'system' mode."""
        if ThemeManager.get_mode() == "system":
            self._on_theme_changed("system")

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

    def _toggle_quick_theme(self) -> None:
        """Toggle between Light and Dark mode from sidebar sun/moon button."""
        new_mode = "light" if ThemeManager.is_dark() else "dark"
        self._on_theme_changed(new_mode)

    def _on_theme_changed(self, mode: str) -> None:
        """Apply theme change dynamically across the application with smooth fade."""
        self.service.set_theme(mode)
        ThemeManager.set_theme(mode)
        self._apply_theme_to_ui(animate=True)

    def _apply_theme_to_ui(self, animate: bool = True) -> None:
        """Apply active theme to stylesheet, sidebar, and pages with ~150ms fade."""
        if animate:
            # Smooth fade transition (Rule 10: ~150ms)
            self._fade_anim = QGraphicsOpacityEffect(self.page_stack)
            self.page_stack.setGraphicsEffect(self._fade_anim)
            anim = QPropertyAnimation(self._fade_anim, b"opacity")
            anim.setDuration(150)
            anim.setStartValue(0.6)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.start()

        p = ThemeManager.get_palette()

        # Update application stylesheet
        app = QApplication.instance()
        if app:
            app.setStyleSheet(ThemeManager.get_stylesheet())

        # Update sidebar
        self.sidebar.setStyleSheet(f"background-color: {p.sidebar_bg}; border-right: 1px solid {p.sidebar_border};")
        self.lbl_brand.setStyleSheet(f"color: {p.sidebar_text_active}; letter-spacing: 1.5px;")
        self.lbl_tagline.setStyleSheet(f"color: {p.gold}; letter-spacing: 1px;")
        self.sidebar_div.setStyleSheet(f"background-color: {p.sidebar_border}; max-height: 1px; border: none; margin: 0 16px 12px 16px;")

        # Update Sun/Moon button and mode label
        is_dark = ThemeManager.is_dark()
        icon_name = "sun" if is_dark else "moon"
        self.btn_theme_toggle.setIcon(ThemeManager.get_icon(icon_name, p.gold))
        self.btn_theme_toggle.setIconSize(QSize(18, 18))
        self.btn_theme_toggle.setStyleSheet(f"""
            QPushButton {{
                background-color: {p.sidebar_active};
                border: 1px solid {p.sidebar_border};
                border-radius: 6px;
                padding: 4px;
            }}
            QPushButton:hover {{
                border-color: {p.gold};
                background-color: {p.sidebar_hover};
            }}
        """)

        mode_str = ThemeManager.get_mode().capitalize()
        self.lbl_theme_mode.setText(f"{mode_str} Mode")
        self.lbl_theme_mode.setStyleSheet(f"color: {p.sidebar_text};")

        self.lbl_user.setStyleSheet(f"color: {p.sidebar_text_active};")
        self.lbl_status.setStyleSheet(f"color: {p.sidebar_text};")

        # Update sidebar navigation buttons
        curr_idx = self.page_stack.currentIndex()
        for i, btn in enumerate(self.nav_buttons):
            btn.update_style(i == curr_idx)

        # Notify all pages to refresh styling & charts
        self.page_dashboard.apply_theme()
        self.page_transactions.apply_theme()
        self.page_budgets.apply_theme()
        self.page_statistics.apply_theme()
        self.page_reports.apply_theme()
        self.page_settings.apply_theme()

    def _on_currency_changed(self, currency_code: str) -> None:
        """Update currency throughout the app."""
        self.service.set_currency(currency_code)
        self.lbl_status.setText(f"Base: {currency_code} • v1.0.0")
        self._on_global_data_changed()
