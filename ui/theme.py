"""
SpendWise Centralized Theme & Styling Module
Provides palette constants, typography definitions, custom widget styling,
and complete QSS stylesheets for Light and Dark themes.
Adheres strictly to the private-bank / fine stationery aesthetic.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget


@dataclass(frozen=True)
class ThemeColors:
    # Core Branding
    NAVY: str = "#0F1B2D"
    NAVY_LIGHT: str = "#18273E"
    NAVY_HOVER: str = "#203350"
    GOLD: str = "#B8934A"
    GOLD_HOVER: str = "#C9A45B"
    GOLD_PRESSED: str = "#9E7B38"
    GOLD_LIGHT: str = "#F6F1E6"

    # Status & Semantics
    INCOME: str = "#2F7D5B"
    INCOME_LIGHT: str = "#EBF5F0"
    EXPENSE: str = "#9B2C2C"
    EXPENSE_LIGHT: str = "#FDF2F2"
    WARNING: str = "#D97706"
    WARNING_LIGHT: str = "#FEF3C7"
    INFO: str = "#2563EB"

    # Backgrounds & Cards (Variable by Theme)
    BG_LIGHT: str = "#FAF7F0"
    CARD_LIGHT: str = "#FFFFFF"
    BORDER_LIGHT: str = "#E7E1D3"
    TEXT_PRIMARY_LIGHT: str = "#0F1B2D"
    TEXT_SECONDARY_LIGHT: str = "#6B7280"
    ROW_ALT_LIGHT: str = "#FBF9F5"

    BG_DARK: str = "#0B1220"
    CARD_DARK: str = "#141F33"
    BORDER_DARK: str = "#1E2D4A"
    TEXT_PRIMARY_DARK: str = "#F9FAFB"
    TEXT_SECONDARY_DARK: str = "#9CA3AF"
    ROW_ALT_DARK: str = "#111A2B"


COLORS = ThemeColors()


class ThemeManager:
    """Manages active theme state and returns stylesheets and fonts."""

    _current_theme = "light"

    @classmethod
    def set_theme(cls, theme: str) -> None:
        cls._current_theme = "dark" if theme.lower() == "dark" else "light"

    @classmethod
    def is_dark(cls) -> bool:
        return cls._current_theme == "dark"

    @classmethod
    def get_bg_color(cls) -> str:
        return COLORS.BG_DARK if cls.is_dark() else COLORS.BG_LIGHT

    @classmethod
    def get_card_color(cls) -> str:
        return COLORS.CARD_DARK if cls.is_dark() else COLORS.CARD_LIGHT

    @classmethod
    def get_border_color(cls) -> str:
        return COLORS.BORDER_DARK if cls.is_dark() else COLORS.BORDER_LIGHT

    @classmethod
    def get_text_primary(cls) -> str:
        return COLORS.TEXT_PRIMARY_DARK if cls.is_dark() else COLORS.TEXT_PRIMARY_LIGHT

    @classmethod
    def get_text_secondary(cls) -> str:
        return COLORS.TEXT_SECONDARY_DARK if cls.is_dark() else COLORS.TEXT_SECONDARY_LIGHT

    @classmethod
    def get_row_alt(cls) -> str:
        return COLORS.ROW_ALT_DARK if cls.is_dark() else COLORS.ROW_ALT_LIGHT

    # -------------------------------------------------------------
    # Typography Helpers
    # -------------------------------------------------------------

    @staticmethod
    def font_serif(size: int = 14, bold: bool = False) -> QFont:
        font = QFont("Georgia")
        font.setFamilies(["Georgia", "Playfair Display", "Times New Roman", "serif"])
        font.setPointSize(size)
        font.setBold(bold)
        return font

    @staticmethod
    def font_sans(size: int = 10, bold: bool = False) -> QFont:
        font = QFont()
        font.setFamilies(["-apple-system", "SF Pro Text", "Helvetica Neue", "Segoe UI", "Inter", "Arial", "sans-serif"])
        font.setPointSize(size)
        font.setBold(bold)
        return font

    # -------------------------------------------------------------
    # Shadow Effect
    # -------------------------------------------------------------

    @classmethod
    def create_card_shadow(cls, parent: QWidget) -> QGraphicsDropShadowEffect:
        shadow = QGraphicsDropShadowEffect(parent)
        if cls.is_dark():
            shadow.setColor(QColor(0, 0, 0, 70))
            shadow.setBlurRadius(18)
            shadow.setOffset(0, 3)
        else:
            shadow.setColor(QColor(15, 27, 45, 14))
            shadow.setBlurRadius(20)
            shadow.setOffset(0, 4)
        return shadow

    # -------------------------------------------------------------
    # Global Application QSS
    # -------------------------------------------------------------

    @classmethod
    def get_stylesheet(cls) -> str:
        bg = cls.get_bg_color()
        card = cls.get_card_color()
        border = cls.get_border_color()
        text_primary = cls.get_text_primary()
        text_secondary = cls.get_text_secondary()
        row_alt = cls.get_row_alt()
        dark = cls.is_dark()

        return f"""
        /* ---------------- Global Reset ---------------- */
        QWidget {{
            font-family: 'Inter', 'Segoe UI', -apple-system, sans-serif;
            font-size: 13px;
            color: {text_primary};
        }}

        QMainWindow, QDialog {{
            background-color: {bg};
        }}

        QStackedWidget {{
            background-color: transparent;
        }}

        /* ---------------- Scrollbars ---------------- */
        QScrollBar:vertical {{
            border: none;
            background: transparent;
            width: 8px;
            margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background: {border};
            min-height: 24px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {COLORS.GOLD};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}

        QScrollBar:horizontal {{
            border: none;
            background: transparent;
            height: 8px;
            margin: 0px;
        }}
        QScrollBar::handle:horizontal {{
            background: {border};
            min-width: 24px;
            border-radius: 4px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {COLORS.GOLD};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}

        /* ---------------- Inputs & Controls ---------------- */
        QLineEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox {{
            background-color: {card};
            color: {text_primary};
            border: 1px solid {border};
            border-radius: 6px;
            padding: 7px 12px;
            font-size: 13px;
            selection-background-color: {COLORS.GOLD};
            selection-color: #FFFFFF;
        }}

        QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
            border: 1.5px solid {COLORS.GOLD};
            background-color: {card};
        }}

        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 26px;
            border-left-width: 0px;
            border-top-right-radius: 6px;
            border-bottom-right-radius: 6px;
        }}

        QComboBox QAbstractItemView {{
            background-color: {card};
            color: {text_primary};
            border: 1px solid {border};
            selection-background-color: {COLORS.GOLD_LIGHT if not dark else COLORS.NAVY_LIGHT};
            selection-color: {COLORS.GOLD if not dark else '#FFFFFF'};
            padding: 4px;
        }}

        /* ---------------- Buttons ---------------- */
        QPushButton {{
            font-weight: 500;
            border-radius: 6px;
            padding: 8px 16px;
            font-size: 13px;
        }}

        /* Gold Primary Button */
        QPushButton.primary-btn {{
            background-color: {COLORS.GOLD};
            color: #FFFFFF;
            border: none;
            font-weight: 600;
        }}
        QPushButton.primary-btn:hover {{
            background-color: {COLORS.GOLD_HOVER};
        }}
        QPushButton.primary-btn:pressed {{
            background-color: {COLORS.GOLD_PRESSED};
        }}

        /* Outlined Secondary Button */
        QPushButton.secondary-btn {{
            background-color: transparent;
            color: {text_primary};
            border: 1px solid {border};
        }}
        QPushButton.secondary-btn:hover {{
            border-color: {COLORS.GOLD};
            color: {COLORS.GOLD};
            background-color: {COLORS.GOLD_LIGHT if not dark else COLORS.NAVY_LIGHT};
        }}

        /* Danger Button */
        QPushButton.danger-btn {{
            background-color: transparent;
            color: {COLORS.EXPENSE};
            border: 1px solid {COLORS.EXPENSE};
        }}
        QPushButton.danger-btn:hover {{
            background-color: {COLORS.EXPENSE};
            color: #FFFFFF;
        }}

        /* ---------------- Tables ---------------- */
        QTableView {{
            background-color: {card};
            color: {text_primary};
            border: 1px solid {border};
            border-radius: 8px;
            gridline-color: transparent;
            selection-background-color: {COLORS.GOLD_LIGHT if not dark else COLORS.NAVY_LIGHT};
            selection-color: {text_primary};
            alternate-background-color: {row_alt};
        }}

        QHeaderView::section {{
            background-color: {COLORS.BG_LIGHT if not dark else COLORS.BG_DARK};
            color: {text_secondary};
            font-weight: 600;
            font-size: 11px;
            text-transform: uppercase;
            padding: 10px 8px;
            border: none;
            border-bottom: 1.5px solid {border};
        }}

        QTableCornerButton::section {{
            background-color: {COLORS.BG_LIGHT if not dark else COLORS.BG_DARK};
            border: none;
        }}

        /* ---------------- Progress Bars ---------------- */
        QProgressBar {{
            background-color: {border};
            border: none;
            border-radius: 5px;
            text-align: center;
            height: 10px;
        }}
        QProgressBar::chunk {{
            background-color: {COLORS.GOLD};
            border-radius: 5px;
        }}

        /* ---------------- Tab / Stacked ---------------- */
        QTabWidget::pane {{
            border: none;
            background: transparent;
        }}
        """
