"""
SpendWise BudgetProgressBar Widget
Custom progress bar for budget visualization with dynamic color coding:
- Green: < 70%
- Amber: 70% - 90%
- Burgundy/Red: > 90%
Displays category, spent / total, percentage, and remaining amount.
"""

from __future__ import annotations
from typing import Optional
from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, Property
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)
from ui.theme import COLORS, ThemeManager


class BudgetBar(QFrame):
    """Refined budget progress bar with thresholds and amount details."""

    def __init__(
        self,
        category_name: str,
        spent: float,
        limit: float,
        currency: str = "MAD",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("BudgetBar")
        self.category_name = category_name
        self.spent = spent
        self.limit = limit
        self.currency = currency

        self._setup_ui()
        self.update_values(category_name, spent, limit, currency)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        # Header Row: Category Name + Spent / Total
        top_layout = QHBoxLayout()
        self.lbl_name = QLabel(self.category_name)
        self.lbl_name.setFont(ThemeManager.font_sans(size=11, bold=True))

        self.lbl_amounts = QLabel()
        self.lbl_amounts.setFont(ThemeManager.font_sans(size=10))
        self.lbl_amounts.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        top_layout.addWidget(self.lbl_name)
        top_layout.addWidget(self.lbl_amounts)
        layout.addLayout(top_layout)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        layout.addWidget(self.progress_bar)

        # Bottom Row: Remaining Status + Percentage
        bottom_layout = QHBoxLayout()
        self.lbl_remaining = QLabel()
        self.lbl_remaining.setFont(ThemeManager.font_sans(size=9))

        self.lbl_percentage = QLabel()
        self.lbl_percentage.setFont(ThemeManager.font_sans(size=9, bold=True))
        self.lbl_percentage.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        bottom_layout.addWidget(self.lbl_remaining)
        bottom_layout.addWidget(self.lbl_percentage)
        layout.addLayout(bottom_layout)

        self.apply_theme()

    def update_values(self, category_name: str, spent: float, limit: float, currency: str = "MAD") -> None:
        """Update metrics and adjust bar color accordingly."""
        self.category_name = category_name
        self.spent = spent
        self.limit = limit
        self.currency = currency

        percentage = (spent / limit * 100.0) if limit > 0 else 0.0
        remaining = limit - spent

        self.lbl_name.setText(category_name)
        self.lbl_amounts.setText(f"{spent:,.2f} / {limit:,.2f} {currency}")
        self.lbl_percentage.setText(f"{percentage:.1f}%")

        # Color thresholds: Green < 70%, Amber 70-90%, Burgundy > 90%
        if percentage >= 90.0:
            fill_color = COLORS.EXPENSE
            text_color = COLORS.EXPENSE
            status_text = f"Exceeded by {abs(remaining):,.2f} {currency}" if remaining < 0 else f"Critical: only {remaining:,.2f} {currency} remaining"
        elif percentage >= 70.0:
            fill_color = COLORS.WARNING
            text_color = COLORS.WARNING
            status_text = f"Warning: {remaining:,.2f} {currency} remaining"
        else:
            fill_color = COLORS.INCOME
            text_color = COLORS.INCOME
            status_text = f"{remaining:,.2f} {currency} remaining"

        self.lbl_remaining.setText(status_text)
        self.lbl_remaining.setStyleSheet(f"color: {text_color};")
        self.lbl_percentage.setStyleSheet(f"color: {text_color};")

        # Cap visual progress bar at 100 for geometry
        self.progress_bar.setValue(min(100, int(percentage)))

        # Update bar chunk color
        border = ThemeManager.get_border_color()
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {border};
                border: none;
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {fill_color};
                border-radius: 4px;
            }}
        """)

    def apply_theme(self) -> None:
        """Refresh container styling."""
        card_bg = ThemeManager.get_card_color()
        border = ThemeManager.get_border_color()
        text_primary = ThemeManager.get_text_primary()
        self.setStyleSheet(f"""
            QFrame#BudgetBar {{
                background-color: {card_bg};
                border: 1px solid {border};
                border-radius: 8px;
            }}
        """)
        self.lbl_name.setStyleSheet(f"color: {text_primary};")
        self.lbl_amounts.setStyleSheet(f"color: {ThemeManager.get_text_secondary()};")
