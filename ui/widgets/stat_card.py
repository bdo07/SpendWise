"""
SpendWise StatCard Widget
Executive metric card for financial KPIs (Balance, Income, Expenses, Savings Rate).
Features serif typography, clean card container, and subtle drop shadow.
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
from ui.theme import COLORS, ThemeManager


class StatCard(QFrame):
    """Refined metric card displaying a single KPI."""

    def __init__(
        self,
        title: str,
        value: str = "0.00 MAD",
        subtitle: str = "",
        value_color: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("StatCard")
        self._title = title
        self._value = value
        self._subtitle = subtitle
        self._value_color = value_color or ThemeManager.get_text_primary()

        self._setup_ui()
        self.apply_theme()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(6)

        # Title / Label
        self.lbl_title = QLabel(self._title.upper())
        self.lbl_title.setFont(ThemeManager.font_sans(size=9, bold=True))
        self.lbl_title.setStyleSheet(f"color: {ThemeManager.get_text_secondary()}; letter-spacing: 0.5px;")
        layout.addWidget(self.lbl_title)

        # Big Value (Serif)
        self.lbl_value = QLabel(self._value)
        self.lbl_value.setFont(ThemeManager.font_serif(size=22, bold=True))
        self.lbl_value.setStyleSheet(f"color: {self._value_color};")
        layout.addWidget(self.lbl_value)

        # Subtitle / Trend
        self.lbl_subtitle = QLabel(self._subtitle)
        self.lbl_subtitle.setFont(ThemeManager.font_sans(size=10))
        self.lbl_subtitle.setStyleSheet(f"color: {ThemeManager.get_text_secondary()};")
        self.lbl_subtitle.setVisible(bool(self._subtitle))
        layout.addWidget(self.lbl_subtitle)

        # Apply soft shadow
        self.setGraphicsEffect(ThemeManager.create_card_shadow(self))

    def update_data(self, value: str, subtitle: Optional[str] = None, value_color: Optional[str] = None) -> None:
        """Update value and subtitle."""
        self._value = value
        self.lbl_value.setText(value)
        if value_color:
            self._value_color = value_color
            self.lbl_value.setStyleSheet(f"color: {value_color};")
        if subtitle is not None:
            self._subtitle = subtitle
            self.lbl_subtitle.setText(subtitle)
            self.lbl_subtitle.setVisible(bool(subtitle))

    def apply_theme(self) -> None:
        """Refresh styling on theme change."""
        card_bg = ThemeManager.get_card_color()
        border = ThemeManager.get_border_color()
        self.setStyleSheet(f"""
            QFrame#StatCard {{
                background-color: {card_bg};
                border: 1px solid {border};
                border-radius: 12px;
            }}
        """)
        self.lbl_title.setStyleSheet(f"color: {ThemeManager.get_text_secondary()}; letter-spacing: 0.5px;")
        self.lbl_value.setStyleSheet(f"color: {self._value_color};")
        self.lbl_subtitle.setStyleSheet(f"color: {ThemeManager.get_text_secondary()};")
        self.setGraphicsEffect(ThemeManager.create_card_shadow(self))
