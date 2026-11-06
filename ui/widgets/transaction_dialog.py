"""
SpendWise Transaction Dialog
Dialog for adding or editing an expense or income transaction.
Features type toggling, real-time validation, date picker, and category selection.
"""

from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from core.models import Category, Transaction
from ui.theme import COLORS, ThemeManager


class TransactionDialog(QDialog):
    """Modal dialog for creating or updating a transaction."""

    def __init__(
        self,
        categories: List[Category],
        transaction: Optional[Transaction] = None,
        currency: str = "MAD",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.categories = categories
        self.transaction = transaction
        self.currency = currency
        self.result_transaction: Optional[Transaction] = None

        self.setWindowTitle("Edit Transaction" if transaction else "New Transaction")
        self.setFixedWidth(460)
        self.setModal(True)

        self._setup_ui()
        if transaction:
            self._populate_fields(transaction)
        else:
            self.date_edit.setDate(QDate.currentDate())
            self._on_type_changed()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        # Dialog Title
        title_text = "Edit Transaction" if self.transaction else "Record Transaction"
        lbl_title = QLabel(title_text)
        lbl_title.setFont(ThemeManager.font_serif(size=16, bold=True))
        lbl_title.setStyleSheet(f"color: {ThemeManager.get_text_primary()};")
        layout.addWidget(lbl_title)

        # Type Toggle (Expense / Income)
        type_layout = QHBoxLayout()
        type_layout.setSpacing(10)

        self.btn_expense = QPushButton("Expense")
        self.btn_expense.setCheckable(True)
        self.btn_expense.setChecked(True)
        self.btn_expense.setFixedHeight(36)

        self.btn_income = QPushButton("Income")
        self.btn_income.setCheckable(True)
        self.btn_income.setFixedHeight(36)

        self.type_group = QButtonGroup(self)
        self.type_group.addButton(self.btn_expense, 1)
        self.type_group.addButton(self.btn_income, 2)
        self.type_group.idClicked.connect(self._on_type_changed)

        type_layout.addWidget(self.btn_expense)
        type_layout.addWidget(self.btn_income)
        layout.addLayout(type_layout)

        # Form fields
        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignLeft)

        # Amount
        self.spin_amount = QDoubleSpinBox()
        self.spin_amount.setRange(0.01, 10_000_000.0)
        self.spin_amount.setDecimals(2)
        self.spin_amount.setSuffix(f" {self.currency}")
        self.spin_amount.setValue(100.0)
        self.spin_amount.setFixedHeight(36)
        form.addRow("Amount *", self.spin_amount)

        # Category
        self.combo_category = QComboBox()
        self.combo_category.setFixedHeight(36)
        form.addRow("Category *", self.combo_category)

        # Date
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setFixedHeight(36)
        form.addRow("Date *", self.date_edit)

        # Description
        self.edit_description = QLineEdit()
        self.edit_description.setPlaceholderText("e.g. Weekly grocery shopping")
        self.edit_description.setFixedHeight(36)
        form.addRow("Description", self.edit_description)

        layout.addLayout(form)

        # Validation error label
        self.lbl_error = QLabel("")
        self.lbl_error.setFont(ThemeManager.font_sans(size=9))
        self.lbl_error.setStyleSheet(f"color: {COLORS.EXPENSE};")
        self.lbl_error.setVisible(False)
        layout.addWidget(self.lbl_error)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setProperty("class", "secondary-btn")
        self.btn_cancel.setFixedHeight(36)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("Save Transaction")
        self.btn_save.setProperty("class", "primary-btn")
        self.btn_save.setFixedHeight(36)
        self.btn_save.clicked.connect(self._validate_and_save)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

        self._refresh_type_styles()

    def _on_type_changed(self) -> None:
        """Filter category combo box based on selected type (expense/income)."""
        selected_type = "expense" if self.btn_expense.isChecked() else "income"
        self._refresh_type_styles()

        self.combo_category.clear()
        filtered = [c for c in self.categories if c.type == selected_type]
        if not filtered:
            filtered = self.categories  # fallback

        for cat in filtered:
            self.combo_category.addItem(f"● {cat.name}", cat.id)

    def _refresh_type_styles(self) -> None:
        if self.btn_expense.isChecked():
            self.btn_expense.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS.EXPENSE};
                    color: #FFFFFF;
                    font-weight: 600;
                    border: none;
                    border-radius: 6px;
                }}
            """)
            self.btn_income.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {ThemeManager.get_text_secondary()};
                    border: 1px solid {ThemeManager.get_border_color()};
                    border-radius: 6px;
                }}
            """)
        else:
            self.btn_income.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS.INCOME};
                    color: #FFFFFF;
                    font-weight: 600;
                    border: none;
                    border-radius: 6px;
                }}
            """)
            self.btn_expense.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {ThemeManager.get_text_secondary()};
                    border: 1px solid {ThemeManager.get_border_color()};
                    border-radius: 6px;
                }}
            """)

    def _populate_fields(self, tx: Transaction) -> None:
        """Fill inputs from existing transaction."""
        if tx.type == "income":
            self.btn_income.setChecked(True)
        else:
            self.btn_expense.setChecked(True)

        self._on_type_changed()

        self.spin_amount.setValue(tx.amount)
        qdate = QDate.fromString(tx.date, "yyyy-MM-dd")
        if qdate.isValid():
            self.date_edit.setDate(qdate)
        self.edit_description.setText(tx.description)

        # Select category
        for idx in range(self.combo_category.count()):
            if self.combo_category.itemData(idx) == tx.category_id:
                self.combo_category.setCurrentIndex(idx)
                break

    def _validate_and_save(self) -> None:
        """Validate input values and construct Transaction object."""
        amount = self.spin_amount.value()
        if amount <= 0:
            self.lbl_error.setText("Amount must be greater than 0.")
            self.lbl_error.setVisible(True)
            return

        cat_id = self.combo_category.currentData()
        if cat_id is None:
            self.lbl_error.setText("Please select a category.")
            self.lbl_error.setVisible(True)
            return

        tx_type = "expense" if self.btn_expense.isChecked() else "income"
        date_str = self.date_edit.date().toString("yyyy-MM-dd")
        desc = self.edit_description.text().strip()

        self.result_transaction = Transaction(
            id=self.transaction.id if self.transaction else None,
            type=tx_type,
            amount=amount,
            category_id=cat_id,
            date=date_str,
            description=desc,
        )
        self.accept()

