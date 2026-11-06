"""
SpendWise Centralized Theme & Styling Module
Provides dual palettes (LIGHT & DARK), system theme detection, dynamic QSS generation,
font definitions, and shadow/border styling for the private-bank aesthetic.
"""

from __future__ import annotations
import os
import sys
from dataclasses import dataclass
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QIcon, QPixmap, QPainter
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget


@dataclass(frozen=True)
class Palette:
    """Complete color specification for a theme."""
    name: str
    is_dark: bool

    # Backgrounds & Surfaces
    window_bg: str          # Main background
    card_bg: str            # Standard cards & panels
    elevated_bg: str        # Modals, dialogs, popups, dropdowns
    sidebar_bg: str         # Left navigation sidebar
    sidebar_active: str     # Active sidebar button background
    sidebar_hover: str      # Hover sidebar button background
    sidebar_border: str     # Sidebar dividing border

    # Borders & Dividers
    border: str             # Card borders, input borders
    border_subtle: str      # Dividers, subtle lines

    # Text Colors
    text_primary: str       # High-contrast headings and text
    text_secondary: str     # Muted text, captions, subtitles
    sidebar_text: str       # Unselected sidebar text
    sidebar_text_active: str# Active sidebar text

    # Brand & Semantic Accents
    gold: str               # Primary brand gold
    gold_hover: str         # Primary button hover
    gold_pressed: str       # Primary button pressed
    gold_surface: str       # Faint gold highlight (~15% opacity)

    income: str             # Green for positive cash flow
    income_surface: str     # Faint green container background
    expense: str            # Burgundy/red for expenses
    expense_surface: str    # Faint expense container background
    warning: str            # Amber for budget warnings (70-90%)
    warning_surface: str    # Faint warning container background
    info: str               # Informational blue

    # Table styling
    row_alt: str            # Table alternating row color
    table_header_bg: str    # Table header background


# Light Palette (Fine Stationery / Private Bank)
LIGHT_PALETTE = Palette(
    name="light",
    is_dark=False,
    window_bg="#FAF7F0",
    card_bg="#FFFFFF",
    elevated_bg="#FFFFFF",
    sidebar_bg="#0F1B2D",
    sidebar_active="#18273E",
    sidebar_hover="#203350",
    sidebar_border="#18273E",
    border="#E7E1D3",
    border_subtle="#EFE9DE",
    text_primary="#0F1B2D",
    text_secondary="#6B7280",
    sidebar_text="#A0ABC0",
    sidebar_text_active="#FFFFFF",
    gold="#B8934A",
    gold_hover="#C9A45B",
    gold_pressed="#9E7B38",
    gold_surface="rgba(184, 147, 74, 0.12)",
    income="#2F7D5B",
    income_surface="#EBF5F0",
    expense="#9B2C2C",
    expense_surface="#FDF2F2",
    warning="#D97706",
    warning_surface="#FEF3C7",
    info="#2563EB",
    row_alt="#FBF9F5",
    table_header_bg="#FAF7F0",
)

# Dark Palette (Midnight Executive / Velvet Contrast)
DARK_PALETTE = Palette(
    name="dark",
    is_dark=True,
    window_bg="#0B1220",
    card_bg="#141F33",
    elevated_bg="#1A2740",
    sidebar_bg="#070D18",
    sidebar_active="#132038",
    sidebar_hover="#0F1B30",
    sidebar_border="#243350",
    border="#243350",
    border_subtle="#1B2840",
    text_primary="#F3EFE6",
    text_secondary="#9AA4B5",
    sidebar_text="#8C98AC",
    sidebar_text_active="#F3EFE6",
    gold="#C9A55C",
    gold_hover="#D8B56D",
    gold_pressed="#B38F46",
    gold_surface="rgba(201, 165, 92, 0.16)",
    income="#4CAF86",
    income_surface="#112920",
    expense="#D96B6B",
    expense_surface="#2E1719",
    warning="#E5A93C",
    warning_surface="#2B210F",
    info="#3B82F6",
    row_alt="#111A2C",
    table_header_bg="#0D1627",
)


class ThemeManager:
    """Manages application theme state, palettes, OS synchronization, and QSS."""

    _mode: str = "system"  # 'light', 'dark', or 'system'
    _active_palette: Palette = LIGHT_PALETTE

    @classmethod
    def init(cls, saved_mode: str = "system") -> None:
        """Initialize the theme manager with user preference."""
        cls.set_theme(saved_mode)

    @classmethod
    def set_theme(cls, mode: str) -> None:
        """Set active theme mode: 'light', 'dark', or 'system'."""
        mode = mode.lower()
        if mode not in ("light", "dark", "system"):
            mode = "system"
        cls._mode = mode

        if mode == "system":
            cls._active_palette = DARK_PALETTE if cls.is_system_dark() else LIGHT_PALETTE
        elif mode == "dark":
            cls._active_palette = DARK_PALETTE
        else:
            cls._active_palette = LIGHT_PALETTE

    @classmethod
    def get_mode(cls) -> str:
        """Return user selected mode: 'light', 'dark', or 'system'."""
        return cls._mode

    @classmethod
    def get_palette(cls) -> Palette:
        """Return the currently active theme palette."""
        return cls._active_palette

    @classmethod
    def is_dark(cls) -> bool:
        """Check if active resolved palette is dark."""
        return cls._active_palette.is_dark

    @classmethod
    def is_system_dark(cls) -> bool:
        """Detect whether host operating system is in dark mode."""
        try:
            # Qt 6.5+ ColorScheme check
            app = QGuiApplication.instance()
            if app:
                hints = app.styleHints()
                if hasattr(hints, "colorScheme"):
                    return hints.colorScheme() == Qt.ColorScheme.Dark

            # macOS fallback check
            if sys.platform == "darwin":
                import subprocess
                res = subprocess.run(
                    ["defaults", "read", "-g", "AppleInterfaceStyle"],
                    capture_output=True,
                    text=True,
                    timeout=1.0,
                )
                return "Dark" in res.stdout
        except Exception:
            pass
        return False

    # -------------------------------------------------------------
    # Typography Helpers
    # -------------------------------------------------------------

    @staticmethod
    def font_serif(size: int = 14, bold: bool = False) -> QFont:
        font = QFont("Georgia")
        font.setFamilies(["Georgia", "Times New Roman", "serif"])
        font.setPointSize(size)
        font.setBold(bold)
        return font

    @staticmethod
    def font_sans(size: int = 10, bold: bool = False) -> QFont:
        font = QFont("Helvetica Neue")
        font.setFamilies(["Helvetica Neue", "Arial", "sans-serif"])
        font.setPointSize(size)
        font.setBold(bold)
        return font

    # -------------------------------------------------------------
    # Shadow / Border Effect
    # -------------------------------------------------------------

    @classmethod
    def create_card_shadow(cls, parent: QWidget) -> Optional[QGraphicsDropShadowEffect]:
        """
        Creates card elevation.
        In light mode: soft subtle drop shadow.
        In dark mode: subtle faint glow rather than muddy dark shadow (Rule 8).
        """
        shadow = QGraphicsDropShadowEffect(parent)
        if cls.is_dark():
            # In dark mode: very faint glow / border enhancement
            shadow.setColor(QColor(0, 0, 0, 110))
            shadow.setBlurRadius(14)
            shadow.setOffset(0, 2)
        else:
            shadow.setColor(QColor(15, 27, 45, 14))
            shadow.setBlurRadius(20)
            shadow.setOffset(0, 4)
        return shadow

    # -------------------------------------------------------------
    # Icon Helper (Recolors SVGs dynamically per theme)
    # -------------------------------------------------------------

    @classmethod
    def get_icon(cls, icon_name: str, color: Optional[str] = None) -> QIcon:
        """
        Load an SVG icon from assets and recolor its stroke/fill dynamically.
        Guarantees no black icons on dark backgrounds (Rule 6).
        """
        icons_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "icons"))
        icon_path = os.path.join(icons_dir, f"{icon_name}.svg")

        if not os.path.exists(icon_path):
            return QIcon()

        if color is None:
            color = cls._active_palette.sidebar_text

        try:
            with open(icon_path, "r", encoding="utf-8") as f:
                svg_data = f.read()

            # Replace currentColor or stroke colors with the target color
            recolored_svg = svg_data.replace('stroke="currentColor"', f'stroke="{color}"')
            recolored_svg = recolored_svg.replace('stroke="#B8934A"', f'stroke="{color}"')
            recolored_svg = recolored_svg.replace('stroke="#000000"', f'stroke="{color}"')
            recolored_svg = recolored_svg.replace('fill="#B8934A"', f'fill="{color}"')

            # Render to QPixmap via QSvgRenderer
            from PySide6.QtSvg import QSvgRenderer
            renderer = QSvgRenderer(recolored_svg.encode("utf-8"))
            pixmap = QPixmap(24, 24)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()

            return QIcon(pixmap)
        except Exception:
            return QIcon(icon_path)

    # -------------------------------------------------------------
    # Global Application QSS
    # -------------------------------------------------------------

    @classmethod
    def get_stylesheet(cls) -> str:
        """Generate comprehensive application stylesheet matching the active palette."""
        p = cls._active_palette

        return f"""
        /* ---------------- Global Reset ---------------- */
        QWidget {{
            font-family: 'Helvetica Neue', Arial, sans-serif;
            font-size: 13px;
            color: {p.text_primary};
        }}

        QMainWindow, QDialog, QMessageBox {{
            background-color: {p.window_bg};
            color: {p.text_primary};
        }}

        QDialog {{
            background-color: {p.elevated_bg};
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
            background: {p.border};
            min-height: 24px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {p.gold};
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
            background: {p.border};
            min-width: 24px;
            border-radius: 4px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {p.gold};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}

        /* ---------------- Inputs & Controls ---------------- */
        QLineEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox {{
            background-color: {p.card_bg};
            color: {p.text_primary};
            border: 1px solid {p.border};
            border-radius: 6px;
            padding: 7px 12px;
            font-size: 13px;
            selection-background-color: {p.gold};
            selection-color: #FFFFFF;
        }}

        QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
            border: 1.5px solid {p.gold};
            background-color: {p.card_bg};
        }}

        QLineEdit:disabled, QComboBox:disabled, QDateEdit:disabled, QSpinBox:disabled {{
            background-color: {p.border_subtle};
            color: {p.text_secondary};
            border-color: {p.border};
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
            background-color: {p.elevated_bg};
            color: {p.text_primary};
            border: 1px solid {p.border};
            border-radius: 6px;
            selection-background-color: {p.gold_surface};
            selection-color: {p.gold};
            padding: 6px;
            outline: none;
        }}

        /* ---------------- Calendar Popup ---------------- */
        QCalendarWidget QWidget#qt_calendar_navigationbar {{
            background-color: {p.elevated_bg};
            border-bottom: 1px solid {p.border};
        }}
        QCalendarWidget QToolButton {{
            color: {p.text_primary};
            background-color: transparent;
            font-weight: 600;
            border-radius: 4px;
            padding: 4px 8px;
        }}
        QCalendarWidget QToolButton:hover {{
            background-color: {p.gold_surface};
            color: {p.gold};
        }}
        QCalendarWidget QMenu {{
            background-color: {p.elevated_bg};
            color: {p.text_primary};
            border: 1px solid {p.border};
        }}
        QCalendarWidget QSpinBox {{
            background-color: {p.card_bg};
            color: {p.text_primary};
            border: 1px solid {p.border};
        }}
        QCalendarWidget QTableView {{
            background-color: {p.elevated_bg};
            color: {p.text_primary};
            selection-background-color: {p.gold};
            selection-color: #FFFFFF;
            border: none;
        }}
        QCalendarWidget QTableView QHeaderView::section {{
            background-color: {p.window_bg};
            color: {p.text_secondary};
            font-size: 11px;
            border: none;
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
            background-color: {p.gold};
            color: #FFFFFF;
            border: none;
            font-weight: 600;
        }}
        QPushButton.primary-btn:hover {{
            background-color: {p.gold_hover};
        }}
        QPushButton.primary-btn:pressed {{
            background-color: {p.gold_pressed};
        }}
        QPushButton.primary-btn:disabled {{
            background-color: {p.border};
            color: {p.text_secondary};
        }}

        /* Outlined Secondary Button */
        QPushButton.secondary-btn {{
            background-color: transparent;
            color: {p.text_primary};
            border: 1px solid {p.border};
        }}
        QPushButton.secondary-btn:hover {{
            border-color: {p.gold};
            color: {p.gold};
            background-color: {p.gold_surface};
        }}
        QPushButton.secondary-btn:pressed {{
            background-color: {p.border_subtle};
        }}

        /* Danger Button */
        QPushButton.danger-btn {{
            background-color: transparent;
            color: {p.expense};
            border: 1px solid {p.expense};
        }}
        QPushButton.danger-btn:hover {{
            background-color: {p.expense};
            color: #FFFFFF;
        }}

        /* ---------------- Tables ---------------- */
        QTableView {{
            background-color: {p.card_bg};
            color: {p.text_primary};
            border: 1px solid {p.border};
            border-radius: 8px;
            gridline-color: transparent;
            selection-background-color: {p.gold_surface};
            selection-color: {p.text_primary};
            alternate-background-color: {p.row_alt};
            outline: none;
        }}

        QHeaderView::section {{
            background-color: {p.table_header_bg};
            color: {p.text_secondary};
            font-weight: 600;
            font-size: 11px;
            text-transform: uppercase;
            padding: 10px 8px;
            border: none;
            border-bottom: 1.5px solid {p.border};
        }}

        QTableCornerButton::section {{
            background-color: {p.table_header_bg};
            border: none;
        }}

        /* ---------------- Progress Bars ---------------- */
        QProgressBar {{
            background-color: {p.border};
            border: none;
            border-radius: 5px;
            text-align: center;
            height: 10px;
        }}
        QProgressBar::chunk {{
            background-color: {p.gold};
            border-radius: 5px;
        }}

        /* ---------------- Tooltips ---------------- */
        QToolTip {{
            background-color: {p.elevated_bg};
            color: {p.text_primary};
            border: 1px solid {p.border};
            border-radius: 5px;
            padding: 6px 10px;
            font-size: 12px;
        }}

        /* ---------------- Menus ---------------- */
        QMenu {{
            background-color: {p.elevated_bg};
            color: {p.text_primary};
            border: 1px solid {p.border};
            border-radius: 6px;
            padding: 4px;
        }}
        QMenu::item {{
            padding: 6px 20px;
            border-radius: 4px;
        }}
        QMenu::item:selected {{
            background-color: {p.gold_surface};
            color: {p.gold};
        }}

        /* ---------------- Radio & Checkboxes ---------------- */
        QRadioButton, QCheckBox {{
            color: {p.text_primary};
            spacing: 8px;
        }}
        QRadioButton::indicator, QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 1.5px solid {p.border};
            background-color: {p.card_bg};
            border-radius: 8px;
        }}
        QCheckBox::indicator {{
            border-radius: 4px;
        }}
        QRadioButton::indicator:checked, QCheckBox::indicator:checked {{
            border-color: {p.gold};
            background-color: {p.gold};
        }}

        /* ---------------- Tab / Stacked ---------------- */
        QTabWidget::pane {{
            border: none;
            background: transparent;
        }}
        """

    # Backwards compatibility getters
    @classmethod
    def get_bg_color(cls) -> str:
        return cls._active_palette.window_bg

    @classmethod
    def get_card_color(cls) -> str:
        return cls._active_palette.card_bg

    @classmethod
    def get_border_color(cls) -> str:
        return cls._active_palette.border

    @classmethod
    def get_text_primary(cls) -> str:
        return cls._active_palette.text_primary

    @classmethod
    def get_text_secondary(cls) -> str:
        return cls._active_palette.text_secondary

    @classmethod
    def get_row_alt(cls) -> str:
        return cls._active_palette.row_alt


# Static alias for backwards compatibility
COLORS = LIGHT_PALETTE
