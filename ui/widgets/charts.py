"""
SpendWise Chart Components
Custom chart widgets built with PySide6.QtCharts, styled for the classic private-bank palette.
Includes:
- CategoryDonutChart: Elegant donut chart with category distribution
- MonthlyBarChart: Grouped bar chart comparing Income vs Expenses over 12 months
- CumulativeLineChart: Spline chart showing running net wealth over time

All charts dynamically re-theme their backgrounds, axes, grid lines, labels, legend, and series live.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtCharts import (
    QBarCategoryAxis,
    QBarSeries,
    QBarSet,
    QChart,
    QChartView,
    QLineSeries,
    QPieSeries,
    QPieSlice,
    QSplineSeries,
    QValueAxis,
)
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget
from ui.theme import ThemeManager


CHART_PALETTE = [
    "#D97706",  # Gold / Amber
    "#2563EB",  # Blue
    "#7C3AED",  # Violet
    "#059669",  # Emerald
    "#DB2777",  # Rose
    "#EA580C",  # Orange
    "#4F46E5",  # Indigo
    "#DC2626",  # Red
    "#0D9488",  # Teal
    "#6B7280",  # Gray
]


class BaseChartView(QChartView):
    """QChartView configured with anti-aliasing and transparent card background."""

    def __init__(self, chart: QChart, parent: Optional[QWidget] = None) -> None:
        super().__init__(chart, parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setStyleSheet("background: transparent; border: none;")


class CategoryDonutChart(QFrame):
    """Donut chart showing category breakdown with central hole."""

    def __init__(self, title: str = "Expenses by Category", is_mini: bool = False, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.is_mini = is_mini
        self.chart_title = title
        self._last_breakdown: List[Dict[str, Any]] = []
        self._last_currency: str = "MAD"
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        if not self.is_mini and self.chart_title:
            self.lbl_title = QLabel(self.chart_title)
            self.lbl_title.setFont(ThemeManager.font_serif(size=14, bold=True))
            layout.addWidget(self.lbl_title)
        else:
            self.lbl_title = None

        self.chart = QChart()
        self.chart.setBackgroundVisible(False)
        self.chart.setAnimationOptions(QChart.SeriesAnimations)
        self.chart.layout().setContentsMargins(0, 0, 0, 0)

        # Legend configuration
        legend = self.chart.legend()
        legend.setFont(ThemeManager.font_sans(size=9))
        if self.is_mini:
            legend.setAlignment(Qt.AlignBottom)
            legend.setFont(ThemeManager.font_sans(size=8))
        else:
            legend.setAlignment(Qt.AlignRight)

        self.chart_view = BaseChartView(self.chart, self)
        layout.addWidget(self.chart_view)

        self.apply_theme()

    def set_data(self, breakdown: List[Dict[str, Any]], currency: str = "MAD") -> None:
        """Populate donut slices."""
        self._last_breakdown = breakdown
        self._last_currency = currency

        p = ThemeManager.get_palette()
        self.chart.removeAllSeries()
        series = QPieSeries()
        series.setHoleSize(0.55 if self.is_mini else 0.50)

        if not breakdown:
            slice_empty = series.append("No Data", 1.0)
            slice_empty.setColor(QColor(p.border))
            slice_empty.setBorderColor(QColor(p.border))
            self.chart.addSeries(series)
            self.chart.legend().setVisible(False)
            return

        self.chart.legend().setVisible(True)
        self.chart.legend().setLabelColor(QColor(p.text_primary))

        for idx, item in enumerate(breakdown[:8]):  # Top 8
            amt = item["amount"]
            name = item["category_name"]
            pct = item["percentage"]
            label = f"{name} ({pct:.0f}%)" if not self.is_mini else name

            pie_slice = series.append(label, amt)
            color_hex = item.get("color") or CHART_PALETTE[idx % len(CHART_PALETTE)]
            pie_slice.setColor(QColor(color_hex))
            pie_slice.setBorderColor(QColor(p.card_bg))
            pie_slice.setBorderWidth(2)

            # Highlight slice slightly when hovered
            pie_slice.hovered.connect(lambda state, s=pie_slice: s.setExploded(state))

        self.chart.addSeries(series)

    def apply_theme(self) -> None:
        """Update styling and refresh slices border and legend colors live."""
        p = ThemeManager.get_palette()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {p.card_bg};
                border: 1px solid {p.border};
                border-radius: 12px;
            }}
        """)
        if self.lbl_title:
            self.lbl_title.setStyleSheet(f"color: {p.text_primary};")
        self.chart.legend().setLabelColor(QColor(p.text_primary))
        self.setGraphicsEffect(ThemeManager.create_card_shadow(self))

        # Re-render slices with new border color if data exists
        if self._last_breakdown:
            self.set_data(self._last_breakdown, self._last_currency)


class MonthlyBarChart(QFrame):
    """Bar chart comparing Income vs Expenses over the past months."""

    def __init__(self, title: str = "Monthly Cash Flow (Income vs Expenses)", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.chart_title = title
        self._last_history: List[Dict[str, Any]] = []
        self._last_currency: str = "MAD"
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        self.lbl_title = QLabel(self.chart_title)
        self.lbl_title.setFont(ThemeManager.font_serif(size=14, bold=True))
        layout.addWidget(self.lbl_title)

        self.chart = QChart()
        self.chart.setBackgroundVisible(False)
        self.chart.setAnimationOptions(QChart.SeriesAnimations)
        self.chart.layout().setContentsMargins(0, 0, 0, 0)

        legend = self.chart.legend()
        legend.setAlignment(Qt.AlignTop)
        legend.setFont(ThemeManager.font_sans(size=9))

        self.chart_view = BaseChartView(self.chart, self)
        layout.addWidget(self.chart_view)

        self.apply_theme()

    def set_data(self, history: List[Dict[str, Any]], currency: str = "MAD") -> None:
        """Render monthly grouped bars."""
        self._last_history = history
        self._last_currency = currency

        p = ThemeManager.get_palette()
        self.chart.removeAllSeries()
        for ax in self.chart.axes():
            self.chart.removeAxis(ax)

        if not history:
            return

        set_income = QBarSet("Income")
        set_income.setColor(QColor(p.income))
        set_income.setBorderColor(QColor(p.income))

        set_expense = QBarSet("Expenses")
        set_expense.setColor(QColor(p.expense))
        set_expense.setBorderColor(QColor(p.expense))

        categories = []
        max_val = 1000.0

        for item in history:
            categories.append(item["month"])
            inc = item["income"]
            exp = item["expenses"]
            set_income.append(inc)
            set_expense.append(exp)
            max_val = max(max_val, inc, exp)

        series = QBarSeries()
        series.append(set_income)
        series.append(set_expense)
        series.setBarWidth(0.7)
        self.chart.addSeries(series)

        # X Axis
        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        axis_x.setLabelsFont(ThemeManager.font_sans(size=8))
        axis_x.setLabelsColor(QColor(p.text_secondary))
        axis_x.setLinePen(QPen(QColor(p.border)))
        self.chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)

        # Y Axis
        axis_y = QValueAxis()
        axis_y.setRange(0, max_val * 1.15)
        axis_y.setLabelFormat("%.0f")
        axis_y.setLabelsFont(ThemeManager.font_sans(size=8))
        axis_y.setLabelsColor(QColor(p.text_secondary))
        axis_y.setLinePen(QPen(QColor(p.border)))
        axis_y.setGridLineColor(QColor(p.border_subtle))
        self.chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)

        self.chart.legend().setLabelColor(QColor(p.text_primary))

    def apply_theme(self) -> None:
        """Update styling and refresh axes, bars, and labels live."""
        p = ThemeManager.get_palette()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {p.card_bg};
                border: 1px solid {p.border};
                border-radius: 12px;
            }}
        """)
        self.lbl_title.setStyleSheet(f"color: {p.text_primary};")
        self.chart.legend().setLabelColor(QColor(p.text_primary))
        self.setGraphicsEffect(ThemeManager.create_card_shadow(self))

        if self._last_history:
            self.set_data(self._last_history, self._last_currency)


class CumulativeLineChart(QFrame):
    """Spline curve chart showing cumulative net wealth."""

    def __init__(self, title: str = "Cumulative Net Balance", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.chart_title = title
        self._last_series: List[Dict[str, Any]] = []
        self._last_currency: str = "MAD"
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        self.lbl_title = QLabel(self.chart_title)
        self.lbl_title.setFont(ThemeManager.font_serif(size=14, bold=True))
        layout.addWidget(self.lbl_title)

        self.chart = QChart()
        self.chart.setBackgroundVisible(False)
        self.chart.setAnimationOptions(QChart.SeriesAnimations)
        self.chart.layout().setContentsMargins(0, 0, 0, 0)
        self.chart.legend().setVisible(False)

        self.chart_view = BaseChartView(self.chart, self)
        layout.addWidget(self.chart_view)

        self.apply_theme()

    def set_data(self, cumulative_series: List[Dict[str, Any]], currency: str = "MAD") -> None:
        """Render cumulative net line."""
        self._last_series = cumulative_series
        self._last_currency = currency

        p = ThemeManager.get_palette()
        self.chart.removeAllSeries()
        for ax in self.chart.axes():
            self.chart.removeAxis(ax)

        if not cumulative_series:
            return

        series = QSplineSeries()
        pen = QPen(QColor(p.gold))
        pen.setWidth(3)
        series.setPen(pen)

        categories = []
        min_val = 0.0
        max_val = 1000.0

        for idx, item in enumerate(cumulative_series):
            categories.append(item["month"])
            val = item["cumulative_balance"]
            series.append(idx, val)
            min_val = min(min_val, val)
            max_val = max(max_val, val)

        self.chart.addSeries(series)

        # X Axis
        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        axis_x.setLabelsFont(ThemeManager.font_sans(size=8))
        axis_x.setLabelsColor(QColor(p.text_secondary))
        axis_x.setLinePen(QPen(QColor(p.border)))
        self.chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)

        # Y Axis
        axis_y = QValueAxis()
        margin = max(abs(min_val), abs(max_val)) * 0.15 + 100
        axis_y.setRange(min_val - margin, max_val + margin)
        axis_y.setLabelFormat("%.0f")
        axis_y.setLabelsFont(ThemeManager.font_sans(size=8))
        axis_y.setLabelsColor(QColor(p.text_secondary))
        axis_y.setLinePen(QPen(QColor(p.border)))
        axis_y.setGridLineColor(QColor(p.border_subtle))
        self.chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)

    def apply_theme(self) -> None:
        """Update styling and refresh line curve, axes, and labels live."""
        p = ThemeManager.get_palette()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {p.card_bg};
                border: 1px solid {p.border};
                border-radius: 12px;
            }}
        """)
        self.lbl_title.setStyleSheet(f"color: {p.text_primary};")
        self.setGraphicsEffect(ThemeManager.create_card_shadow(self))

        if self._last_series:
            self.set_data(self._last_series, self._last_currency)
