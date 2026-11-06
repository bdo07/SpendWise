"""
SpendWise StatCard Widget
Executive metric card for financial KPIs (Balance, Income, Expenses, Savings Rate).
Features serif typography, clean card container, dynamic role-based color updates, and theme elevation.
"""

from __future__ import annotations
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)
from ui.theme import ThemeManager


class StatCard(QFrame):
    """Refined metric card displaying a single KPI."""

    def __init__(
        self,
        title: str,
        value: str = "0.00 MAD",
        subtitle: str = "",
        value_role: str = "primary",  # 'primary', 'income', 'expense', 'gold'
        value_color: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("StatCard")
        self._title = title
        self._value = value
        self._subtitle = subtitle
        self._value_role = value_role
        self._value_color = value_color or self._resolve_color(value_role)

        self._setup_ui()
        self.apply_theme()

    def _resolve_color(self, role: str) -> str:
        p = ThemeManager.get_palette()
        if role == "income":
            return p.income
        elif role == "expense":
            return p.expense
        elif role == "gold":
            return p.gold
        return p.text_primary

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(6)

        # Title / Label
        self.lbl_title = QLabel(self._title.upper())
        self.lbl_title.setFont(ThemeManager.font_sans(size=9, bold=True))
        layout.addWidget(self.lbl_title)

        # Big Value (Serif)
        self.lbl_value = QLabel(self._value)
        self.lbl_value.setFont(ThemeManager.font_serif(size=22, bold=True))
        layout.addWidget(self.lbl_value)

        # Subtitle / Trend
        self.lbl_subtitle = QLabel(self._subtitle)
        self.lbl_subtitle.setFont(ThemeManager.font_sans(size=10))
        self.lbl_subtitle.setVisible(bool(self._subtitle))
        layout.addWidget(self.lbl_subtitle)

    def update_data(
        self,
        value: str,
        subtitle: Optional[str] = None,
        value_color: Optional[str] = None,
        value_role: Optional[str] = None,
    ) -> None:
        """Update value, subtitle, and dynamic role."""
        self._value = value
        self.lbl_value.setText(value)
        if value_role:
            self._value_role = value_role
            self._value_color = self._resolve_color(value_role)
            self.lbl_value.setStyleSheet(f"color: {self._value_color};")
        elif value_color:
            self._value_color = value_color
            self.lbl_value.setStyleSheet(f"color: {value_color};")

        if subtitle is not None:
            self._subtitle = subtitle
            self.lbl_subtitle.setText(subtitle)
            self.lbl_subtitle.setVisible(bool(subtitle))

    def apply_theme(self) -> None:
        """Refresh styling on theme change."""
        p = ThemeManager.get_palette()
        self.setStyleSheet(f"""
            QFrame#StatCard {{
                background-color: {p.card_bg};
                border: 1px solid {p.border};
                border-radius: 12px;
            }}
        """)
        self.lbl_title.setStyleSheet(f"color: {p.text_secondary}; letter-spacing: 0.5px;")

        # Re-resolve color if role was set
        if self._value_role:
            self._value_color = self._resolve_color(self._value_role)
        self.lbl_value.setStyleSheet(f"color: {self._value_color};")
        self.lbl_subtitle.setStyleSheet(f"color: {p.text_secondary};")

        # Elevation
        self.setGraphicsEffect(ThemeManager.create_card_shadow(self))
