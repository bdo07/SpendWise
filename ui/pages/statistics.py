"""
SpendWise Statistics & Analytics Page
Visual analytics dashboard featuring:
- Donut / Pie chart of spending by category
- Grouped Bar chart of Income vs Expenses (Last 12 months)
- Spline Line chart of cumulative balance progression
- Key financial ratios and insights
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from core.services import FinanceService
from ui.theme import COLORS, ThemeManager
from ui.widgets.charts import (
    CategoryDonutChart,
    CumulativeLineChart,
    MonthlyBarChart,
)
from ui.widgets.stat_card import StatCard


class StatisticsPage(QWidget):
    """Deep visual analytics of income, expenses, and wealth accumulation."""

    def __init__(self, service: FinanceService, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.service = service
        self.current_month = datetime.now().strftime("%Y-%m")

        self._setup_ui()
        self.reload_data()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        self.container_layout = QVBoxLayout(container)
        self.container_layout.setContentsMargins(32, 28, 32, 32)
        self.container_layout.setSpacing(24)

        # 1. Header Row
        header_layout = QHBoxLayout()
        title_layout = QVBoxLayout()
        self.lbl_title = QLabel("Financial Analytics & Trends")
        self.lbl_title.setFont(ThemeManager.font_serif(size=22, bold=True))
        self.lbl_subtitle = QLabel("Visual breakdown of spending composition, cash flow dynamics, and capital accumulation")
        self.lbl_subtitle.setFont(ThemeManager.font_sans(size=11))
        self.lbl_subtitle.setStyleSheet(f"color: {ThemeManager.get_text_secondary()};")
        title_layout.addWidget(self.lbl_title)
        title_layout.addWidget(self.lbl_subtitle)
        header_layout.addLayout(title_layout)

        header_layout.addStretch()

        # Month Selector
        self.combo_month = QComboBox()
        self.combo_month.setFixedWidth(160)
        self.combo_month.setFixedHeight(38)
        self._populate_months()
        self.combo_month.currentTextChanged.connect(self._on_month_changed)
        header_layout.addWidget(self.combo_month)

        self.container_layout.addLayout(header_layout)

        # 2. Key Metrics Row
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(16)
        self.card_top_category = StatCard("Top Expense Category", "—", "Highest spending category")
        self.card_avg_expense = StatCard("12-Month Avg Expense", "0.00 MAD", "Monthly average burn rate")
        self.card_net_accumulated = StatCard("12-Month Net Capital", "0.00 MAD", "Total net savings over period")
        kpi_row.addWidget(self.card_top_category)
        kpi_row.addWidget(self.card_avg_expense)
        kpi_row.addWidget(self.card_net_accumulated)
        self.container_layout.addLayout(kpi_row)

        # 3. Middle Row: Category Donut Chart & Monthly Cash Flow Bar Chart
        mid_layout = QHBoxLayout()
        mid_layout.setSpacing(20)

        # Category Donut Chart
        self.category_chart = CategoryDonutChart("Expenses by Category", is_mini=False)
        self.category_chart.setMinimumHeight(340)
        mid_layout.addWidget(self.category_chart, stretch=2)

        # Cash Flow Bar Chart
        self.cashflow_chart = MonthlyBarChart("Income vs Expenses (Last 12 Months)")
        self.cashflow_chart.setMinimumHeight(340)
        mid_layout.addWidget(self.cashflow_chart, stretch=3)

        self.container_layout.addLayout(mid_layout)

        # 4. Bottom Row: Cumulative Balance Line Chart
        self.cumulative_chart = CumulativeLineChart("Cumulative Net Balance (Wealth Trajectory)")
        self.cumulative_chart.setMinimumHeight(300)
        self.container_layout.addWidget(self.cumulative_chart)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)
        self.apply_theme()

    def _populate_months(self) -> None:
        self.combo_month.blockSignals(True)
        self.combo_month.clear()
        available = self.service.tx_repo.get_available_months()
        curr = datetime.now().strftime("%Y-%m")
        if curr not in available:
            available.insert(0, curr)

        for m in available:
            dt = datetime.strptime(m, "%Y-%m")
            self.combo_month.addItem(dt.strftime("%B %Y"), m)

        idx = self.combo_month.findData(self.current_month)
        if idx >= 0:
            self.combo_month.setCurrentIndex(idx)
        self.combo_month.blockSignals(False)

    def _on_month_changed(self) -> None:
        m = self.combo_month.currentData()
        if m:
            self.current_month = m
            self.reload_data()

    def reload_data(self) -> None:
        """Fetch fresh analytics data and update all charts and KPI cards."""
        currency = self.service.get_currency()

        # 1. Category Breakdown Donut
        breakdown = self.service.get_category_breakdown(self.current_month, type_="expense")
        self.category_chart.set_data(breakdown, currency)

        if breakdown:
            top_cat = breakdown[0]
            self.card_top_category.update_data(
                top_cat["category_name"],
                subtitle=f"{top_cat['amount']:,.2f} {currency} ({top_cat['percentage']:.1f}%)",
                value_color=COLORS.EXPENSE,
            )
        else:
            self.card_top_category.update_data("None", subtitle="No expenses recorded", value_color=COLORS.GOLD)

        # 2. 12-Month Bar Chart
        history = self.service.get_monthly_history(limit_months=12)
        self.cashflow_chart.set_data(history, currency)

        if history:
            total_exp = sum(h["expenses"] for h in history)
            avg_exp = total_exp / len(history)
            net_accum = sum(h["net"] for h in history)

            self.card_avg_expense.update_data(f"{avg_exp:,.2f} {currency}", subtitle=f"Calculated across {len(history)} months")
            net_col = COLORS.INCOME if net_accum >= 0 else COLORS.EXPENSE
            sign = "+" if net_accum >= 0 else ""
            self.card_net_accumulated.update_data(f"{sign}{net_accum:,.2f} {currency}", value_color=net_col)

        # 3. Cumulative Balance Series
        series = self.service.get_cumulative_balance_series(limit_months=12)
        self.cumulative_chart.set_data(series, currency)

    def apply_theme(self) -> None:
        self.lbl_title.setStyleSheet(f"color: {ThemeManager.get_text_primary()};")
        self.lbl_subtitle.setStyleSheet(f"color: {ThemeManager.get_text_secondary()};")
        self.card_top_category.apply_theme()
        self.card_avg_expense.apply_theme()
        self.card_net_accumulated.apply_theme()
        self.category_chart.apply_theme()
        self.cashflow_chart.apply_theme()
        self.cumulative_chart.apply_theme()

