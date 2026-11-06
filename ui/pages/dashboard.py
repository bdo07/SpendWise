"""
SpendWise Dashboard Page
Executive summary showing:
- Month selector
- 4 Metric cards (Net Balance, Total Income, Total Expenses, Savings Rate)
- Active Budget Warning Banner
- Overall Budget Progress Card
- Mini Donut Chart of Category Expenses
- Recent 5 Transactions table
- Quick Record Transaction button
"""

from __future__ import annotations
from datetime import datetime
from typing import Callable, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from core.models import BudgetStatus, MonthlySummary
from core.services import FinanceService
from ui.theme import COLORS, ThemeManager
from ui.widgets.budget_bar import BudgetBar
from ui.widgets.charts import CategoryDonutChart
from ui.widgets.stat_card import StatCard


class DashboardPage(QWidget):
    """Main dashboard page."""

    request_new_transaction = Signal()

    def __init__(self, service: FinanceService, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.service = service
        self.current_month = datetime.now().strftime("%Y-%m")

        self._setup_ui()
        self.refresh_data()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Scrollable container for smaller screens
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        self.container_layout = QVBoxLayout(container)
        self.container_layout.setContentsMargins(32, 28, 32, 32)
        self.container_layout.setSpacing(24)

        # 1. Header Bar: Greeting + Month Selector + "+ Record" Button
        header_layout = QHBoxLayout()

        title_layout = QVBoxLayout()
        self.lbl_welcome = QLabel("Financial Overview")
        self.lbl_welcome.setFont(ThemeManager.font_serif(size=22, bold=True))
        self.lbl_subtitle = QLabel("Your personal executive summary and spending pace")
        self.lbl_subtitle.setFont(ThemeManager.font_sans(size=11))
        self.lbl_subtitle.setStyleSheet(f"color: {ThemeManager.get_text_secondary()};")
        title_layout.addWidget(self.lbl_welcome)
        title_layout.addWidget(self.lbl_subtitle)
        header_layout.addLayout(title_layout)

        header_layout.addStretch()

        # Month Picker
        self.combo_month = QComboBox()
        self.combo_month.setFixedWidth(160)
        self.combo_month.setFixedHeight(38)
        self._populate_months()
        self.combo_month.currentTextChanged.connect(self._on_month_changed)
        header_layout.addWidget(self.combo_month)

        # Quick Add Button
        self.btn_add_tx = QPushButton("+ New Transaction")
        self.btn_add_tx.setProperty("class", "primary-btn")
        self.btn_add_tx.setFixedHeight(38)
        self.btn_add_tx.clicked.connect(self.request_new_transaction.emit)
        header_layout.addWidget(self.btn_add_tx)

        self.container_layout.addLayout(header_layout)

        # 2. Alert Banner Container (Dynamic, hidden when all budgets healthy)
        self.alert_banner = QFrame()
        self.alert_banner.setObjectName("AlertBanner")
        self.alert_banner_layout = QHBoxLayout(self.alert_banner)
        self.alert_banner_layout.setContentsMargins(16, 12, 16, 12)
        self.lbl_alert_text = QLabel()
        self.lbl_alert_text.setFont(ThemeManager.font_sans(size=10, bold=True))
        self.lbl_alert_text.setWordWrap(True)
        self.alert_banner_layout.addWidget(self.lbl_alert_text)
        self.alert_banner.setVisible(False)
        self.container_layout.addWidget(self.alert_banner)

        # 3. KPI Cards Grid (4 Cards: Balance, Income, Expenses, Savings Rate)
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(16)

        self.card_balance = StatCard("Net Monthly Savings", "0.00 MAD", "Income minus expenses", value_role="income")
        self.card_income = StatCard("Total Income", "0.00 MAD", "Received this month", value_role="income")
        self.card_expenses = StatCard("Total Expenses", "0.00 MAD", "Spent this month", value_role="expense")
        self.card_savings_rate = StatCard("Savings Rate", "0.0%", "Of total income saved", value_role="gold")

        kpi_layout.addWidget(self.card_balance)
        kpi_layout.addWidget(self.card_income)
        kpi_layout.addWidget(self.card_expenses)
        kpi_layout.addWidget(self.card_savings_rate)
        self.container_layout.addLayout(kpi_layout)

        # 4. Middle Section: Overall Budget Bar + Category Donut Chart
        mid_layout = QHBoxLayout()
        mid_layout.setSpacing(20)

        # Overall Budget Card Container
        self.budget_container = QFrame()
        self.budget_container.setObjectName("Card")
        b_layout = QVBoxLayout(self.budget_container)
        b_layout.setContentsMargins(20, 18, 20, 18)
        b_layout.setSpacing(12)

        lbl_b_title = QLabel("Monthly Budget Consumption")
        lbl_b_title.setFont(ThemeManager.font_serif(size=14, bold=True))
        lbl_b_title.setStyleSheet(f"color: {ThemeManager.get_text_primary()};")
        b_layout.addWidget(lbl_b_title)

        self.overall_budget_bar = BudgetBar("Overall Monthly Budget", 0.0, 1.0, "MAD")
        b_layout.addWidget(self.overall_budget_bar)

        self.lbl_budget_note = QLabel("Set your monthly limit in the Budgets tab to track your spending threshold.")
        self.lbl_budget_note.setFont(ThemeManager.font_sans(size=9))
        self.lbl_budget_note.setStyleSheet(f"color: {ThemeManager.get_text_secondary()};")
        self.lbl_budget_note.setWordWrap(True)
        b_layout.addWidget(self.lbl_budget_note)
        b_layout.addStretch()

        self.budget_container.setGraphicsEffect(ThemeManager.create_card_shadow(self.budget_container))
        mid_layout.addWidget(self.budget_container, stretch=3)

        # Donut Chart Card
        self.donut_chart = CategoryDonutChart("Expenses by Category", is_mini=True)
        self.donut_chart.setMinimumHeight(240)
        mid_layout.addWidget(self.donut_chart, stretch=2)

        self.container_layout.addLayout(mid_layout)

        # 5. Bottom Section: Recent Transactions Card
        recent_card = QFrame()
        recent_card.setObjectName("Card")
        rc_layout = QVBoxLayout(recent_card)
        rc_layout.setContentsMargins(20, 18, 20, 18)
        rc_layout.setSpacing(12)

        rc_header = QHBoxLayout()
        lbl_recent = QLabel("Recent Transactions")
        lbl_recent.setFont(ThemeManager.font_serif(size=14, bold=True))
        lbl_recent.setStyleSheet(f"color: {ThemeManager.get_text_primary()};")
        rc_header.addWidget(lbl_recent)
        rc_header.addStretch()

        lbl_recent_sub = QLabel("Latest activity across all accounts")
        lbl_recent_sub.setFont(ThemeManager.font_sans(size=10))
        lbl_recent_sub.setStyleSheet(f"color: {ThemeManager.get_text_secondary()};")
        rc_header.addWidget(lbl_recent_sub)
        rc_layout.addLayout(rc_header)

        # Recent Transactions Table (5 rows)
        self.table_recent = QTableWidget()
        self.table_recent.setColumnCount(4)
        self.table_recent.setHorizontalHeaderLabels(["Date", "Category", "Description", "Amount"])
        self.table_recent.verticalHeader().setVisible(False)
        self.table_recent.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_recent.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_recent.setShowGrid(False)
        self.table_recent.setFixedHeight(190)

        header = self.table_recent.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

        rc_layout.addWidget(self.table_recent)
        recent_card.setGraphicsEffect(ThemeManager.create_card_shadow(recent_card))
        self.container_layout.addWidget(recent_card)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        self.apply_theme()

    def _populate_months(self) -> None:
        """Fill month combobox with available database months and current month."""
        self.combo_month.blockSignals(True)
        self.combo_month.clear()
        available = self.service.tx_repo.get_available_months()
        curr = datetime.now().strftime("%Y-%m")
        if curr not in available:
            available.insert(0, curr)

        for m in available:
            dt = datetime.strptime(m, "%Y-%m")
            label = dt.strftime("%B %Y")
            self.combo_month.addItem(label, m)

        # Select current month
        idx = self.combo_month.findData(self.current_month)
        if idx >= 0:
            self.combo_month.setCurrentIndex(idx)
        self.combo_month.blockSignals(False)

    def _on_month_changed(self) -> None:
        m = self.combo_month.currentData()
        if m:
            self.current_month = m
            self.refresh_data()

    def refresh_data(self) -> None:
        """Fetch fresh metrics and update UI elements."""
        currency = self.service.get_currency()
        summary = self.service.get_monthly_summary(self.current_month)

        # Update KPI Cards
        p = ThemeManager.get_palette()
        net_prefix = "+" if summary.net_savings >= 0 else ""
        net_role = "income" if summary.net_savings >= 0 else "expense"
        self.card_balance.update_data(
            f"{net_prefix}{summary.net_savings:,.2f} {currency}",
            subtitle=f"{summary.transaction_count} transactions recorded",
            value_role=net_role,
        )
        self.card_income.update_data(f"+{summary.income:,.2f} {currency}", value_role="income")
        self.card_expenses.update_data(f"-{summary.expenses:,.2f} {currency}", value_role="expense")
        self.card_savings_rate.update_data(
            f"{summary.savings_rate:.1f}%",
            value_role="gold",
        )

        # Check Active Budget Alerts for Banner
        alerts = self.service.get_active_budget_alerts(self.current_month)
        if alerts:
            highest = alerts[0]
            level = highest["level"]
            self.lbl_alert_text.setText(f"⚠ {highest['title']}: {highest['message']}")
            if level in ("critical", "exceeded"):
                self.alert_banner.setStyleSheet(f"""
                    QFrame#AlertBanner {{
                        background-color: {p.expense_surface};
                        border: 1.5px solid {p.expense};
                        border-radius: 8px;
                    }}
                """)
                self.lbl_alert_text.setStyleSheet(f"color: {p.expense};")
            else:
                self.alert_banner.setStyleSheet(f"""
                    QFrame#AlertBanner {{
                        background-color: {p.warning_surface};
                        border: 1.5px solid {p.warning};
                        border-radius: 8px;
                    }}
                """)
                self.lbl_alert_text.setStyleSheet(f"color: {p.warning};")
            self.alert_banner.setVisible(True)
        else:
            self.alert_banner.setVisible(False)

        # Overall Budget Bar
        overall_status = self.service.get_overall_budget_status(self.current_month)
        if overall_status:
            self.overall_budget_bar.update_values(
                "Overall Monthly Limit",
                overall_status.spent,
                overall_status.budget.amount,
                currency,
            )
            self.lbl_budget_note.setText(
                f"You have used {overall_status.percentage:.1f}% of your {overall_status.budget.amount:,.2f} {currency} total budget."
            )
        else:
            exp_total = summary.expenses
            self.overall_budget_bar.update_values(
                "Overall Monthly Limit (Not Configured)",
                exp_total,
                max(exp_total, 1.0),
                currency,
            )
            self.lbl_budget_note.setText("No global budget configured for this month. Set one in the Budgets tab.")

        # Donut Chart
        breakdown = self.service.get_category_breakdown(self.current_month, type_="expense")
        self.donut_chart.set_data(breakdown, currency)

        # Recent Transactions
        recent = self.service.tx_repo.get_recent(limit=5)
        self.table_recent.setRowCount(len(recent))
        for row, tx in enumerate(recent):
            item_date = QTableWidgetItem(tx.date)
            item_date.setFont(ThemeManager.font_sans(size=9))
            self.table_recent.setItem(row, 0, item_date)

            item_cat = QTableWidgetItem(tx.category_name or "General")
            item_cat.setFont(ThemeManager.font_sans(size=9, bold=True))
            self.table_recent.setItem(row, 1, item_cat)

            item_desc = QTableWidgetItem(tx.description or "—")
            item_desc.setFont(ThemeManager.font_sans(size=9))
            self.table_recent.setItem(row, 2, item_desc)

            sign = "+" if tx.type == "income" else "-"
            color = p.income if tx.type == "income" else p.expense
            item_amt = QTableWidgetItem(f"{sign}{tx.amount:,.2f} {currency}")
            item_amt.setFont(ThemeManager.font_sans(size=9, bold=True))
            item_amt.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_amt.setForeground(QColor(color))
            self.table_recent.setItem(row, 3, item_amt)

    def apply_theme(self) -> None:
        """Refresh styling on theme toggle."""
        p = ThemeManager.get_palette()

        self.setStyleSheet(f"""
            QFrame#Card {{
                background-color: {p.card_bg};
                border: 1px solid {p.border};
                border-radius: 12px;
            }}
        """)
        self.lbl_welcome.setStyleSheet(f"color: {p.text_primary};")
        self.lbl_subtitle.setStyleSheet(f"color: {p.text_secondary};")

        self.card_balance.apply_theme()
        self.card_income.apply_theme()
        self.card_expenses.apply_theme()
        self.card_savings_rate.apply_theme()
        self.overall_budget_bar.apply_theme()
        self.donut_chart.apply_theme()
        self.refresh_data()
