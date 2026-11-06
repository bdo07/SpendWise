"""
SpendWise Toast Notification Widget
Displays non-intrusive alert messages for budget warnings, errors, and success confirmations.
"""

from __future__ import annotations
from typing import Optional
from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QTimer, Qt
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from ui.theme import COLORS, ThemeManager


class Toast(QFrame):
    """Floating notification toast with smooth auto-dismiss."""

    def __init__(
        self,
        message: str,
        title: str = "",
        level: str = "info",  # 'info', 'success', 'warning', 'critical', 'exceeded'
        parent: Optional[QWidget] = None,
        duration_ms: int = 4500,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ToastWidget")
        self.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)

        self._setup_ui(title, message, level)
        self._setup_animation()

        if duration_ms > 0:
            QTimer.singleShot(duration_ms, self.fade_out)

    def _setup_ui(self, title: str, message: str, level: str) -> None:
        # Determine accent color and background
        if level in ("critical", "exceeded"):
            accent = COLORS.EXPENSE
            bg = COLORS.EXPENSE_LIGHT if not ThemeManager.is_dark() else "#2D1515"
        elif level == "warning":
            accent = COLORS.WARNING
            bg = COLORS.WARNING_LIGHT if not ThemeManager.is_dark() else "#2B210F"
        elif level == "success":
            accent = COLORS.INCOME
            bg = COLORS.INCOME_LIGHT if not ThemeManager.is_dark() else "#0F261C"
        else:
            accent = COLORS.GOLD
            bg = ThemeManager.get_card_color()

        self.setStyleSheet(f"""
            QFrame#ToastWidget {{
                background-color: {bg};
                border: 1px solid {accent};
                border-left: 5px solid {accent};
                border-radius: 8px;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        content_layout = QVBoxLayout()
        content_layout.setSpacing(2)

        if title:
            lbl_title = QLabel(title)
            lbl_title.setFont(ThemeManager.font_sans(size=10, bold=True))
            lbl_title.setStyleSheet(f"color: {accent};")
            content_layout.addWidget(lbl_title)

        lbl_msg = QLabel(message)
        lbl_msg.setFont(ThemeManager.font_sans(size=9))
        lbl_msg.setStyleSheet(f"color: {ThemeManager.get_text_primary()};")
        lbl_msg.setWordWrap(True)
        content_layout.addWidget(lbl_msg)

        layout.addLayout(content_layout)

        # Close button
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(20, 20)
        btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                font-size: 11px;
                color: #6B7280;
            }
            QPushButton:hover {
                color: #0F1B2D;
            }
        """)
        btn_close.clicked.connect(self.fade_out)
        layout.addWidget(btn_close)

        self.setGraphicsEffect(ThemeManager.create_card_shadow(self))

    def _setup_animation(self) -> None:
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(0.0)

        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(250)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.start()

    def fade_out(self) -> None:
        """Fade out and close widget."""
        self.anim_out = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim_out.setDuration(250)
        self.anim_out.setStartValue(1.0)
        self.anim_out.setEndValue(0.0)
        self.anim_out.finished.connect(self.close)
        self.anim_out.start()


def show_toast(
    parent: QWidget,
    message: str,
    title: str = "",
    level: str = "info",
    duration_ms: int = 4000,
) -> Toast:
    """Convenience helper to display a toast near top-right of parent."""
    toast = Toast(message=message, title=title, level=level, parent=parent, duration_ms=duration_ms)
    toast.setFixedWidth(min(380, parent.width() - 40))
    toast.adjustSize()

    # Position at top right
    x = parent.width() - toast.width() - 24
    y = 24
    toast.move(x, y)
    toast.show()
    return toast

