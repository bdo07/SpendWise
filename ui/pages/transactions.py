"""
SpendWise Transactions Page
Full-featured transaction management:
- QTableView backed by a custom QAbstractTableModel
- Instant search filter (by description or category)
- Month, Category, and Type filters
- Add / Edit / Delete with confirmation dialog
- CSV Export
- Colored amounts (Income green, Expense burgundy)
"""

from __future__ import annotations
from datetime import datetime
from typing import Any, List, Optional
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)
from core.models import Category, Transaction
from core.services import FinanceService
from ui.theme import COLORS, ThemeManager
from ui.widgets.toast import show_toast
from ui.widgets.transaction_dialog import TransactionDialog


class TransactionTableModel(QAbstractTableModel):
    """Custom high-performance table model for transactions."""

    COLUMNS = ["Date", "Type", "Category", "Description", "Amount"]

    def __init__(self, transactions: List[Transaction], currency: str = "MAD", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.transactions = transactions
        self.currency = currency

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.transactions)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.COLUMNS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.COLUMNS[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or index.row() >= len(self.transactions):
            return None

        tx = self.transactions[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == 0:
                return tx.date
            elif col == 1:
                return tx.type.capitalize()
            elif col == 2:
                return tx.category_name or "General"
            elif col == 3:
                return tx.description or "—"
            elif col == 4:
                sign = "+" if tx.type == "income" else "-"
                return f"{sign}{tx.amount:,.2f} {self.currency}"

        elif role == Qt.TextAlignmentRole:
            if col == 4:
                return int(Qt.AlignRight | Qt.AlignVCenter)
            return int(Qt.AlignLeft | Qt.AlignVCenter)

        elif role == Qt.ForegroundRole:
            if col == 4:
                hex_color = COLORS.INCOME if tx.type == "income" else COLORS.EXPENSE
                return QColor(hex_color)
            elif col == 1:
                hex_color = COLORS.INCOME if tx.type == "income" else COLORS.EXPENSE
                return QColor(hex_color)
            return QColor(ThemeManager.get_text_primary())

        elif role == Qt.FontRole:
            if col in (1, 4):
                return ThemeManager.font_sans(size=9, bold=True)
            return ThemeManager.font_sans(size=9)

        return None

    def get_transaction(self, row: int) -> Optional[Transaction]:
        if 0 <= row < len(self.transactions):
            return self.transactions[row]
        return None

    def update_data(self, transactions: List[Transaction], currency: str = "MAD") -> None:
        self.beginResetModel()
        self.transactions = transactions
        self.currency = currency
        self.endResetModel()


class TransactionsPage(QWidget):
    """Transactions ledger and management interface."""

    data_changed = Signal()

    def __init__(self, service: FinanceService, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.service = service
        self._all_categories = self.service.cat_repo.get_all()

        self._setup_ui()
        self.reload_data()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 32)
        layout.setSpacing(18)

        # 1. Header Row
        header_layout = QHBoxLayout()
        title_layout = QVBoxLayout()
        self.lbl_title = QLabel("Transaction Ledger")
        self.lbl_title.setFont(ThemeManager.font_serif(size=22, bold=True))
        self.lbl_subtitle = QLabel("Complete record of personal income and expenses")
        self.lbl_subtitle.setFont(ThemeManager.font_sans(size=11))
        self.lbl_subtitle.setStyleSheet(f"color: {ThemeManager.get_text_secondary()};")
        title_layout.addWidget(self.lbl_title)
        title_layout.addWidget(self.lbl_subtitle)
        header_layout.addLayout(title_layout)

        header_layout.addStretch()

        # Action Buttons
        self.btn_export_csv = QPushButton("Export CSV")
        self.btn_export_csv.setProperty("class", "secondary-btn")
        self.btn_export_csv.setFixedHeight(38)
        self.btn_export_csv.clicked.connect(self._export_csv)
        header_layout.addWidget(self.btn_export_csv)

        self.btn_add = QPushButton("+ Add Transaction")
        self.btn_add.setProperty("class", "primary-btn")
        self.btn_add.setFixedHeight(38)
        self.btn_add.clicked.connect(self.add_transaction)
        header_layout.addWidget(self.btn_add)

        layout.addLayout(header_layout)

        # 2. Filter Bar (Search, Month, Category, Type)
        filter_card = QFrame()
        filter_card.setObjectName("FilterCard")
        f_layout = QHBoxLayout(filter_card)
        f_layout.setContentsMargins(14, 12, 14, 12)
        f_layout.setSpacing(12)

        # Search Bar
        self.edit_search = QLineEdit()
        self.edit_search.setPlaceholderText("Search description or category... (Ctrl+F)")
        self.edit_search.setFixedHeight(36)
        self.edit_search.textChanged.connect(self._apply_filters)
        f_layout.addWidget(self.edit_search, stretch=3)

        # Month Filter
        self.combo_month = QComboBox()
        self.combo_month.setFixedHeight(36)
        self.combo_month.addItem("All Months", "")
        for m in self.service.tx_repo.get_available_months():
            dt = datetime.strptime(m, "%Y-%m")
            self.combo_month.addItem(dt.strftime("%B %Y"), m)
        self.combo_month.currentIndexChanged.connect(self._apply_filters)
        f_layout.addWidget(self.combo_month, stretch=2)

        # Category Filter
        self.combo_category = QComboBox()
        self.combo_category.setFixedHeight(36)
        self.combo_category.addItem("All Categories", None)
        for c in self._all_categories:
            self.combo_category.addItem(c.name, c.id)
        self.combo_category.currentIndexChanged.connect(self._apply_filters)
        f_layout.addWidget(self.combo_category, stretch=2)

        # Type Filter
        self.combo_type = QComboBox()
        self.combo_type.setFixedHeight(36)
        self.combo_type.addItem("All Types", "")
        self.combo_type.addItem("Expenses Only", "expense")
        self.combo_type.addItem("Income Only", "income")
        self.combo_type.currentIndexChanged.connect(self._apply_filters)
        f_layout.addWidget(self.combo_type, stretch=2)

        # Reset button
        self.btn_reset_filters = QPushButton("Reset")
        self.btn_reset_filters.setProperty("class", "secondary-btn")
        self.btn_reset_filters.setFixedHeight(36)
        self.btn_reset_filters.clicked.connect(self._reset_filters)
        f_layout.addWidget(self.btn_reset_filters)

        filter_card.setGraphicsEffect(ThemeManager.create_card_shadow(filter_card))
        layout.addWidget(filter_card)

        # 3. Table View
        self.table_view = QTableView()
        self.table_model = TransactionTableModel([], self.service.get_currency(), self)
        self.table_view.setModel(self.table_model)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setSelectionMode(QTableView.SingleSelection)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.setShowGrid(False)

        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        layout.addWidget(self.table_view, stretch=1)

        # 4. Table Action Bar (Edit / Delete Selected)
        bottom_bar = QHBoxLayout()
        self.lbl_count = QLabel("0 transactions found")
        self.lbl_count.setFont(ThemeManager.font_sans(size=9))
        self.lbl_count.setStyleSheet(f"color: {ThemeManager.get_text_secondary()};")
        bottom_bar.addWidget(self.lbl_count)

        bottom_bar.addStretch()

        self.btn_edit = QPushButton("Edit Selected")
        self.btn_edit.setProperty("class", "secondary-btn")
        self.btn_edit.setFixedHeight(34)
        self.btn_edit.clicked.connect(self._edit_selected)
        bottom_bar.addWidget(self.btn_edit)

        self.btn_delete = QPushButton("Delete Selected")
        self.btn_delete.setProperty("class", "danger-btn")
        self.btn_delete.setFixedHeight(34)
        self.btn_delete.clicked.connect(self._delete_selected)
        bottom_bar.addWidget(self.btn_delete)

        layout.addLayout(bottom_bar)
        self.apply_theme()

    def focus_search(self) -> None:
        """Focus the search field (Ctrl+F shortcut)."""
        self.edit_search.setFocus()
        self.edit_search.selectAll()

    def _reset_filters(self) -> None:
        self.edit_search.clear()
        self.combo_month.setCurrentIndex(0)
        self.combo_category.setCurrentIndex(0)
        self.combo_type.setCurrentIndex(0)
        self._apply_filters()

    def reload_data(self) -> None:
        """Reload all data from database."""
        self._all_categories = self.service.cat_repo.get_all()

        # Update categories combo without resetting selection if possible
        cur_cat = self.combo_category.currentData()
        self.combo_category.blockSignals(True)
        self.combo_category.clear()
        self.combo_category.addItem("All Categories", None)
        for c in self._all_categories:
            self.combo_category.addItem(c.name, c.id)
        idx = self.combo_category.findData(cur_cat)
        if idx >= 0:
            self.combo_category.setCurrentIndex(idx)
        self.combo_category.blockSignals(False)

        self._apply_filters()

    def _apply_filters(self) -> None:
        """Query repository with current filter values."""
        search = self.edit_search.text().strip() or None
        month = self.combo_month.currentData() or None
        cat_id = self.combo_category.currentData()
        tx_type = self.combo_type.currentData() or None

        start_date = f"{month}-01" if month else None
        end_date = f"{month}-31" if month else None

        transactions = self.service.tx_repo.get_all(
            start_date=start_date,
            end_date=end_date,
            category_id=cat_id,
            type_=tx_type,
            search=search,
        )

        currency = self.service.get_currency()
        self.table_model.update_data(transactions, currency)
        self.lbl_count.setText(f"{len(transactions)} transaction(s) found")

    def add_transaction(self) -> None:
        """Open transaction dialog and persist new entry."""
        dlg = TransactionDialog(
            categories=self._all_categories,
            transaction=None,
            currency=self.service.get_currency(),
            parent=self,
        )
        if dlg.exec():
            new_tx = dlg.result_transaction
            if new_tx:
                self.service.tx_repo.create(new_tx)
                self.reload_data()
                self.data_changed.emit()
                show_toast(self, "Transaction successfully recorded.", "Success", level="success")

    def _edit_selected(self) -> None:
        """Open dialog for selected row."""
        selected_indexes = self.table_view.selectionModel().selectedRows()
        if not selected_indexes:
            QMessageBox.information(self, "Selection Required", "Please select a transaction to edit.")
            return

        row = selected_indexes[0].row()
        tx = self.table_model.get_transaction(row)
        if not tx:
            return

        dlg = TransactionDialog(
            categories=self._all_categories,
            transaction=tx,
            currency=self.service.get_currency(),
            parent=self,
        )
        if dlg.exec():
            updated = dlg.result_transaction
            if updated:
                self.service.tx_repo.update(updated)
                self.reload_data()
                self.data_changed.emit()
                show_toast(self, "Transaction updated successfully.", "Saved", level="success")

    def _delete_selected(self) -> None:
        """Prompt confirmation before deleting transaction."""
        selected_indexes = self.table_view.selectionModel().selectedRows()
        if not selected_indexes:
            QMessageBox.information(self, "Selection Required", "Please select a transaction to delete.")
            return

        row = selected_indexes[0].row()
        tx = self.table_model.get_transaction(row)
        if not tx:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to permanently delete this {tx.type} of {tx.amount:,.2f} {self.service.get_currency()}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes and tx.id is not None:
            self.service.tx_repo.delete(tx.id)
            self.reload_data()
            self.data_changed.emit()
            show_toast(self, "Transaction removed from ledger.", "Deleted", level="info")

    def _export_csv(self) -> None:
        """Export current filtered transactions to CSV."""
        txs = self.table_model.transactions
        if not txs:
            QMessageBox.information(self, "No Data", "There are no transactions to export.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Transactions to CSV",
            f"SpendWise_Transactions_{datetime.now().strftime('%Y%m%d')}.csv",
            "CSV Files (*.csv)",
        )
        if path:
            try:
                self.service.export_transactions_to_csv(path, txs)
                show_toast(self, f"Exported {len(txs)} transactions to CSV.", "Export Complete", level="success")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export CSV: {e}")

    def apply_theme(self) -> None:
        """Refresh container styling."""
        card_bg = ThemeManager.get_card_color()
        border = ThemeManager.get_border_color()

        self.setStyleSheet(f"""
            QFrame#FilterCard {{
                background-color: {card_bg};
                border: 1px solid {border};
                border-radius: 10px;
            }}
        """)
        self.lbl_title.setStyleSheet(f"color: {ThemeManager.get_text_primary()};")
        self.lbl_subtitle.setStyleSheet(f"color: {ThemeManager.get_text_secondary()};")

