"""
SpendWise Chart Components
Custom chart widgets built with PySide6.QtCharts, styled for the classic private-bank palette.
Includes:
- CategoryDonutChart: Elegant donut chart with category distribution
- MonthlyBarChart: Grouped bar chart comparing Income vs Expenses over 12 months
- CumulativeLineChart: Spline chart showing running net wealth over time
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
from ui.theme import COLORS, ThemeManager


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
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        if not self.is_mini and self.chart_title:
            lbl_title = QLabel(self.chart_title)
            lbl_title.setFont(ThemeManager.font_serif(size=14, bold=True))
            lbl_title.setStyleSheet(f"color: {ThemeManager.get_text_primary()};")
            layout.addWidget(lbl_title)

        self.chart = QChart()
        self.chart.setBackgroundVisible(False)
        self.chart.setAnimationOptions(QChart.SeriesAnimations)
        self.chart.layout().setContentsMargins(0, 0, 0, 0)

        # Legend configuration
        legend = self.chart.legend()
        legend.setFont(ThemeManager.font_sans(size=9))
        legend.setLabelColor(QColor(ThemeManager.get_text_primary()))
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
        self.chart.removeAllSeries()
        series = QPieSeries()
        series.setHoleSize(0.55 if self.is_mini else 0.50)

        if not breakdown:
            slice_empty = series.append("No Data", 1.0)
            slice_empty.setColor(QColor(ThemeManager.get_border_color()))
            slice_empty.setBorderColor(QColor(ThemeManager.get_border_color()))
            self.chart.addSeries(series)
            self.chart.legend().setVisible(False)
            return

        self.chart.legend().setVisible(True)

        for idx, item in enumerate(breakdown[:8]):  # Top 8
            amt = item["amount"]
            name = item["category_name"]
            pct = item["percentage"]
            label = f"{name} ({pct:.0f}%)" if not self.is_mini else name

            pie_slice = series.append(label, amt)
            color_hex = item.get("color") or CHART_PALETTE[idx % len(CHART_PALETTE)]
            pie_slice.setColor(QColor(color_hex))
            pie_slice.setBorderColor(QColor(ThemeManager.get_card_color()))
            pie_slice.setBorderWidth(2)

            # Tooltip
            pie_slice.setToolTip(f"{name}: {amt:,.2f} {currency} ({pct:.1f}%)")

        self.chart.addSeries(series)

    def apply_theme(self) -> None:
        card_bg = ThemeManager.get_card_color()
        border = ThemeManager.get_border_color()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {card_bg};
                border: 1px solid {border};
                border-radius: 12px;
            }}
        """)
        self.chart.legend().setLabelColor(QColor(ThemeManager.get_text_primary()))
        self.setGraphicsEffect(ThemeManager.create_card_shadow(self))


class MonthlyBarChart(QFrame):
    """Bar chart comparing Income vs Expenses over the past months."""

    def __init__(self, title: str = "Monthly Cash Flow (Income vs Expenses)", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.chart_title = title
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        lbl_title = QLabel(self.chart_title)
        lbl_title.setFont(ThemeManager.font_serif(size=14, bold=True))
        lbl_title.setStyleSheet(f"color: {ThemeManager.get_text_primary()};")
        layout.addWidget(lbl_title)

        self.chart = QChart()
        self.chart.setBackgroundVisible(False)
        self.chart.setAnimationOptions(QChart.SeriesAnimations)
        self.chart.layout().setContentsMargins(0, 0, 0, 0)

        legend = self.chart.legend()
        legend.setAlignment(Qt.AlignTop)
        legend.setFont(ThemeManager.font_sans(size=9))
        legend.setLabelColor(QColor(ThemeManager.get_text_primary()))

        self.chart_view = BaseChartView(self.chart, self)
        layout.addWidget(self.chart_view)

        self.apply_theme()

    def set_data(self, history: List[Dict[str, Any]], currency: str = "MAD") -> None:
        """Render monthly grouped bars."""
        self.chart.removeAllSeries()
        # Remove old axes
        for ax in self.chart.axes():
            self.chart.removeAxis(ax)

        if not history:
            return

        set_income = QBarSet("Income")
        set_income.setColor(QColor(COLORS.INCOME))
        set_income.setBorderColor(QColor(COLORS.INCOME))

        set_expense = QBarSet("Expenses")
        set_expense.setColor(QColor(COLORS.EXPENSE))
        set_expense.setBorderColor(QColor(COLORS.EXPENSE))

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
        axis_x.setLabelsColor(QColor(ThemeManager.get_text_secondary()))
        axis_x.setLinePen(QPen(QColor(ThemeManager.get_border_color())))
        self.chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)

        # Y Axis
        axis_y = QValueAxis()
        axis_y.setRange(0, max_val * 1.15)
        axis_y.setLabelFormat("%.0f")
        axis_y.setLabelsFont(ThemeManager.font_sans(size=8))
        axis_y.setLabelsColor(QColor(ThemeManager.get_text_secondary()))
        axis_y.setLinePen(QPen(QColor(ThemeManager.get_border_color())))
        axis_y.setGridLineColor(QColor(ThemeManager.get_border_color()))
        self.chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)

    def apply_theme(self) -> None:
        card_bg = ThemeManager.get_card_color()
        border = ThemeManager.get_border_color()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {card_bg};
                border: 1px solid {border};
                border-radius: 12px;
            }}
        """)
        self.chart.legend().setLabelColor(QColor(ThemeManager.get_text_primary()))
        self.setGraphicsEffect(ThemeManager.create_card_shadow(self))


class CumulativeLineChart(QFrame):
    """Spline curve chart showing cumulative net wealth."""

    def __init__(self, title: str = "Cumulative Net Balance", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.chart_title = title
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        lbl_title = QLabel(self.chart_title)
        lbl_title.setFont(ThemeManager.font_serif(size=14, bold=True))
        lbl_title.setStyleSheet(f"color: {ThemeManager.get_text_primary()};")
        layout.addWidget(lbl_title)

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
        self.chart.removeAllSeries()
        for ax in self.chart.axes():
            self.chart.removeAxis(ax)

        if not cumulative_series:
            return

        series = QSplineSeries()
        pen = QPen(QColor(COLORS.GOLD))
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
        axis_x.setLabelsColor(QColor(ThemeManager.get_text_secondary()))
        axis_x.setLinePen(QPen(QColor(ThemeManager.get_border_color())))
        self.chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)

        # Y Axis
        axis_y = QValueAxis()
        margin = max(abs(min_val), abs(max_val)) * 0.15 + 100
        axis_y.setRange(min_val - margin, max_val + margin)
        axis_y.setLabelFormat("%.0f")
        axis_y.setLabelsFont(ThemeManager.font_sans(size=8))
        axis_y.setLabelsColor(QColor(ThemeManager.get_text_secondary()))
        axis_y.setLinePen(QPen(QColor(ThemeManager.get_border_color())))
        axis_y.setGridLineColor(QColor(ThemeManager.get_border_color()))
        self.chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)

    def apply_theme(self) -> None:
        card_bg = ThemeManager.get_card_color()
        border = ThemeManager.get_border_color()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {card_bg};
                border: 1px solid {border};
                border-radius: 12px;
            }}
        """)
        self.setGraphicsEffect(ThemeManager.create_card_shadow(self))
