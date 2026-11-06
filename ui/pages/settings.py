"""
SpendWise Settings Page
Configuration center for:
- Currency selection (MAD default, EUR, USD, GBP, etc.)
- Theme switching (Light / Dark)
- Category management (Add, Edit, Delete with validation)
- Recurring transaction rules management
- SQLite database backup & restore
- CSV bulk transaction import with background worker
"""

from __future__ import annotations
import os
from typing import List, Optional
from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from core.models import Category, Recurring
from core.services import FinanceService
from ui.theme import COLORS, ThemeManager
from ui.widgets.toast import show_toast


SUPPORTED_CURRENCIES = [
    ("MAD – Moroccan Dirham", "MAD"),
    ("USD – US Dollar ($)", "USD"),
    ("EUR – Euro (€)", "EUR"),
    ("GBP – British Pound (£)", "GBP"),
    ("AED – UAE Dirham", "AED"),
    ("SAR – Saudi Riyal", "SAR"),
    ("CAD – Canadian Dollar", "CAD"),
    ("CHF – Swiss Franc", "CHF"),
]


class CategoryDialog(QDialog):
    """Dialog to create or edit a category."""

    def __init__(self, category: Optional[Category] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.category = category
        self.result_category: Optional[Category] = None
        self.selected_color = category.color if category else "#B8934A"

        self.setWindowTitle("Edit Category" if category else "New Category")
        self.setFixedWidth(380)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        lbl_title = QLabel("Category Details")
        lbl_title.setFont(ThemeManager.font_serif(size=15, bold=True))
        layout.addWidget(lbl_title)

        form = QFormLayout()
        form.setSpacing(12)

        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("e.g. Travel, Groceries, Dividends")
        self.edit_name.setFixedHeight(36)
        form.addRow("Name *", self.edit_name)

        self.combo_type = QComboBox()
        self.combo_type.addItem("Expense", "expense")
        self.combo_type.addItem("Income", "income")
        self.combo_type.setFixedHeight(36)
        form.addRow("Type *", self.combo_type)

        # Color picker button
        color_row = QHBoxLayout()
        self.btn_color = QPushButton("Choose Color")
        self.btn_color.setFixedHeight(36)
        self._update_color_preview()
        self.btn_color.clicked.connect(self._pick_color)
        color_row.addWidget(self.btn_color)
        form.addRow("Color *", color_row)

        layout.addLayout(form)

        if self.category:
            self.edit_name.setText(self.category.name)
            idx = self.combo_type.findData(self.category.type)
            if idx >= 0:
                self.combo_type.setCurrentIndex(idx)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setProperty("class", "secondary-btn")
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton("Save Category")
        btn_save.setProperty("class", "primary-btn")
        btn_save.clicked.connect(self._save)

        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def _update_color_preview(self) -> None:
        self.btn_color.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.selected_color};
                color: #FFFFFF;
                border: 1px solid {ThemeManager.get_border_color()};
                border-radius: 6px;
                font-weight: 600;
            }}
        """)

    def _pick_color(self) -> None:
        color = QColorDialog.getColor(QColor(self.selected_color), self, "Select Category Color")
        if color.isValid():
            self.selected_color = color.name()
            self._update_color_preview()

    def _save(self) -> None:
        name = self.edit_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Category name cannot be empty.")
            return

        cat_type = self.combo_type.currentData()
        self.result_category = Category(
            id=self.category.id if self.category else None,
            name=name,
            type=cat_type,
            color=self.selected_color,
            icon="tag",
        )
        self.accept()


class RecurringDialog(QDialog):
    """Dialog to create or edit a recurring transaction rule."""

    def __init__(
        self,
        categories: List[Category],
        recurring: Optional[Recurring] = None,
        currency: str = "MAD",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.categories = categories
        self.recurring = recurring
        self.currency = currency
        self.result_recurring: Optional[Recurring] = None

        self.setWindowTitle("Edit Recurring Rule" if recurring else "New Recurring Rule")
        self.setFixedWidth(400)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        lbl_title = QLabel("Recurring Transaction Rule")
        lbl_title.setFont(ThemeManager.font_serif(size=15, bold=True))
        layout.addWidget(lbl_title)

        form = QFormLayout()
        form.setSpacing(12)

        self.combo_type = QComboBox()
        self.combo_type.addItem("Expense", "expense")
        self.combo_type.addItem("Income", "income")
        self.combo_type.setFixedHeight(36)
        self.combo_type.currentIndexChanged.connect(self._filter_categories)
        form.addRow("Type *", self.combo_type)

        self.spin_amount = QDoubleSpinBox()
        self.spin_amount.setRange(0.01, 10_000_000.0)
        self.spin_amount.setDecimals(2)
        self.spin_amount.setSuffix(f" {self.currency}")
        self.spin_amount.setValue(500.0)
        self.spin_amount.setFixedHeight(36)
        form.addRow("Amount *", self.spin_amount)

        self.combo_category = QComboBox()
        self.combo_category.setFixedHeight(36)
        form.addRow("Category *", self.combo_category)

        self.spin_day = QSpinBox()
        self.spin_day.setRange(1, 31)
        self.spin_day.setValue(1)
        self.spin_day.setPrefix("Day ")
        self.spin_day.setSuffix(" of month")
        self.spin_day.setFixedHeight(36)
        form.addRow("Execution Day *", self.spin_day)

        self.edit_desc = QLineEdit()
        self.edit_desc.setPlaceholderText("e.g. Monthly Fiber Internet")
        self.edit_desc.setFixedHeight(36)
        form.addRow("Description *", self.edit_desc)

        layout.addLayout(form)

        if self.recurring:
            idx = self.combo_type.findData(self.recurring.type)
            if idx >= 0:
                self.combo_type.setCurrentIndex(idx)
            self._filter_categories()
            self.spin_amount.setValue(self.recurring.amount)
            self.spin_day.setValue(self.recurring.day_of_month)
            self.edit_desc.setText(self.recurring.description)
            c_idx = self.combo_category.findData(self.recurring.category_id)
            if c_idx >= 0:
                self.combo_category.setCurrentIndex(c_idx)
        else:
            self._filter_categories()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setProperty("class", "secondary-btn")
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton("Save Rule")
        btn_save.setProperty("class", "primary-btn")
        btn_save.clicked.connect(self._save)

        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def _filter_categories(self) -> None:
        t = self.combo_type.currentData()
        self.combo_category.clear()
        filtered = [c for c in self.categories if c.type == t]
        for c in filtered:
            self.combo_category.addItem(c.name, c.id)

    def _save(self) -> None:
        desc = self.edit_desc.text().strip()
        if not desc:
            QMessageBox.warning(self, "Validation Error", "Description is required.")
            return

        cat_id = self.combo_category.currentData()
        if cat_id is None:
            QMessageBox.warning(self, "Validation Error", "Category is required.")
            return

        self.result_recurring = Recurring(
            id=self.recurring.id if self.recurring else None,
            type=self.combo_type.currentData(),
            amount=self.spin_amount.value(),
            category_id=cat_id,
            description=desc,
            day_of_month=self.spin_day.value(),
            active=self.recurring.active if self.recurring else 1,
        )
        self.accept()


class CSVImportWorker(QObject):
    """Background worker for parsing and inserting bulk transactions from CSV."""

    finished = Signal(int, list)  # count, errors

    def __init__(self, service: FinanceService, file_path: str) -> None:
        super().__init__()
        self.service = service
        self.file_path = file_path

    def run(self) -> None:
        try:
            count, errors = self.service.import_transactions_from_csv(self.file_path)
            self.finished.emit(count, errors)
        except Exception as e:
            self.finished.emit(0, [f"Critical import error: {e}"])


class SettingsPage(QWidget):
    """Settings, personalization, categories, recurring rules, and data operations."""

    theme_changed = Signal(str)
    currency_changed = Signal(str)
    data_changed = Signal()

    def __init__(self, service: FinanceService, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.service = service
        self.worker_thread: Optional[QThread] = None

        self._setup_ui()
        self.reload_data()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        self.container_layout = QVBoxLayout(container)
        self.container_layout.setContentsMargins(32, 28, 32, 32)
        self.container_layout.setSpacing(24)

        # 1. Header
        header_layout = QHBoxLayout()
        title_layout = QVBoxLayout()
        self.lbl_title = QLabel("System Settings & Preferences")
        self.lbl_title.setFont(ThemeManager.font_serif(size=22, bold=True))
        self.lbl_subtitle = QLabel("Personalize currency, interface appearance, transaction categories, and local backups")
        self.lbl_subtitle.setFont(ThemeManager.font_sans(size=11))
        self.lbl_subtitle.setStyleSheet(f"color: {ThemeManager.get_text_secondary()};")
        title_layout.addWidget(self.lbl_title)
        title_layout.addWidget(self.lbl_subtitle)
        header_layout.addLayout(title_layout)
        self.container_layout.addLayout(header_layout)

        # 2. General Preferences Card (Currency & Theme)
        pref_card = QFrame()
        pref_card.setObjectName("Card")
        p_layout = QVBoxLayout(pref_card)
        p_layout.setContentsMargins(20, 18, 20, 18)
        p_layout.setSpacing(16)

        lbl_pref = QLabel("General Preferences")
        lbl_pref.setFont(ThemeManager.font_serif(size=15, bold=True))
        p_layout.addWidget(lbl_pref)

        form_pref = QFormLayout()
        form_pref.setSpacing(14)

        # Currency
        self.combo_currency = QComboBox()
        self.combo_currency.setFixedHeight(36)
        for label, code in SUPPORTED_CURRENCIES:
            self.combo_currency.addItem(label, code)
        cur = self.service.get_currency()
        idx = self.combo_currency.findData(cur)
        if idx >= 0:
            self.combo_currency.setCurrentIndex(idx)
        self.combo_currency.currentIndexChanged.connect(self._on_currency_changed)
        form_pref.addRow("Active Currency", self.combo_currency)

        # Theme
        self.combo_theme = QComboBox()
        self.combo_theme.setFixedHeight(36)
        self.combo_theme.addItem("Light Theme (Cream & White Cards)", "light")
        self.combo_theme.addItem("Dark Theme (Midnight Navy & Slate)", "dark")
        theme_val = self.service.get_theme()
        t_idx = self.combo_theme.findData(theme_val)
        if t_idx >= 0:
            self.combo_theme.setCurrentIndex(t_idx)
        self.combo_theme.currentIndexChanged.connect(self._on_theme_changed)
        form_pref.addRow("Appearance Theme", self.combo_theme)

        p_layout.addLayout(form_pref)
        pref_card.setGraphicsEffect(ThemeManager.create_card_shadow(pref_card))
        self.container_layout.addWidget(pref_card)

        # 3. Categories Management Card
        cat_card = QFrame()
        cat_card.setObjectName("Card")
        c_layout = QVBoxLayout(cat_card)
        c_layout.setContentsMargins(20, 18, 20, 18)
        c_layout.setSpacing(14)

        c_header = QHBoxLayout()
        lbl_cats = QLabel("Transaction Categories")
        lbl_cats.setFont(ThemeManager.font_serif(size=15, bold=True))
        c_header.addWidget(lbl_cats)
        c_header.addStretch()

        self.btn_add_cat = QPushButton("+ Add Category")
        self.btn_add_cat.setProperty("class", "primary-btn")
        self.btn_add_cat.setFixedHeight(32)
        self.btn_add_cat.clicked.connect(self._add_category)
        c_header.addWidget(self.btn_add_cat)
        c_layout.addLayout(c_header)

        # Category Table
        self.table_cats = QTableWidget()
        self.table_cats.setColumnCount(4)
        self.table_cats.setHorizontalHeaderLabels(["Name", "Type", "Color", "Actions"])
        self.table_cats.verticalHeader().setVisible(False)
        self.table_cats.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_cats.setShowGrid(False)
        self.table_cats.setFixedHeight(220)

        header = self.table_cats.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

        c_layout.addWidget(self.table_cats)
        cat_card.setGraphicsEffect(ThemeManager.create_card_shadow(cat_card))
        self.container_layout.addWidget(cat_card)

        # 4. Recurring Transactions Rules Card
        rec_card = QFrame()
        rec_card.setObjectName("Card")
        r_layout = QVBoxLayout(rec_card)
        r_layout.setContentsMargins(20, 18, 20, 18)
        r_layout.setSpacing(14)

        r_header = QHBoxLayout()
        lbl_recs = QLabel("Recurring Monthly Transactions")
        lbl_recs.setFont(ThemeManager.font_serif(size=15, bold=True))
        r_header.addWidget(lbl_recs)
        r_header.addStretch()

        self.btn_add_rec = QPushButton("+ Add Recurring Rule")
        self.btn_add_rec.setProperty("class", "primary-btn")
        self.btn_add_rec.setFixedHeight(32)
        self.btn_add_rec.clicked.connect(self._add_recurring)
        r_header.addWidget(self.btn_add_rec)
        r_layout.addLayout(r_header)

        self.table_recs = QTableWidget()
        self.table_recs.setColumnCount(5)
        self.table_recs.setHorizontalHeaderLabels(["Description", "Category", "Amount", "Day", "Actions"])
        self.table_recs.verticalHeader().setVisible(False)
        self.table_recs.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_recs.setShowGrid(False)
        self.table_recs.setFixedHeight(180)

        r_head = self.table_recs.horizontalHeader()
        r_head.setSectionResizeMode(0, QHeaderView.Stretch)
        r_head.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        r_head.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        r_head.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        r_head.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        r_layout.addWidget(self.table_recs)
        rec_card.setGraphicsEffect(ThemeManager.create_card_shadow(rec_card))
        self.container_layout.addWidget(rec_card)

        # 5. Data Management (Backup, Restore, CSV Import)
        data_card = QFrame()
        data_card.setObjectName("Card")
        d_layout = QVBoxLayout(data_card)
        d_layout.setContentsMargins(20, 18, 20, 18)
        d_layout.setSpacing(14)

        lbl_data = QLabel("Data Management & Integrity")
        lbl_data.setFont(ThemeManager.font_serif(size=15, bold=True))
        d_layout.addWidget(lbl_data)

        lbl_data_desc = QLabel("Backup your local SQLite database, restore previous backups, or bulk-import bank transactions from CSV.")
        lbl_data_desc.setFont(ThemeManager.font_sans(size=10))
        lbl_data_desc.setStyleSheet(f"color: {ThemeManager.get_text_secondary()};")
        d_layout.addWidget(lbl_data_desc)

        btn_data_row = QHBoxLayout()
        btn_data_row.setSpacing(14)

        self.btn_backup = QPushButton("💾  Backup Database (.db)")
        self.btn_backup.setProperty("class", "secondary-btn")
        self.btn_backup.setFixedHeight(38)
        self.btn_backup.clicked.connect(self._backup_db)
        btn_data_row.addWidget(self.btn_backup)

        self.btn_restore = QPushButton("🔄  Restore Database (.db)")
        self.btn_restore.setProperty("class", "secondary-btn")
        self.btn_restore.setFixedHeight(38)
        self.btn_restore.clicked.connect(self._restore_db)
        btn_data_row.addWidget(self.btn_restore)

        self.btn_import_csv = QPushButton("📥  Import Transactions from CSV")
        self.btn_import_csv.setProperty("class", "primary-btn")
        self.btn_import_csv.setFixedHeight(38)
        self.btn_import_csv.clicked.connect(self._import_csv)
        btn_data_row.addWidget(self.btn_import_csv)

        btn_data_row.addStretch()
        d_layout.addLayout(btn_data_row)

        # Import progress bar
        self.import_progress = QProgressBar()
        self.import_progress.setRange(0, 0)
        self.import_progress.setFixedHeight(4)
        self.import_progress.setTextVisible(False)
        self.import_progress.setVisible(False)
        d_layout.addWidget(self.import_progress)

        data_card.setGraphicsEffect(ThemeManager.create_card_shadow(data_card))
        self.container_layout.addWidget(data_card)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        self.apply_theme()

    def reload_data(self) -> None:
        """Populate category and recurring tables."""
        currency = self.service.get_currency()

        # Categories
        cats = self.service.cat_repo.get_all()
        self.table_cats.setRowCount(len(cats))
        for row, c in enumerate(cats):
            item_name = QTableWidgetItem(c.name)
            item_name.setFont(ThemeManager.font_sans(size=9, bold=True))
            self.table_cats.setItem(row, 0, item_name)

            item_type = QTableWidgetItem(c.type.capitalize())
            item_type.setFont(ThemeManager.font_sans(size=9))
            item_type.setForeground(QColor(COLORS.INCOME if c.type == "income" else COLORS.EXPENSE))
            self.table_cats.setItem(row, 1, item_type)

            # Color pill
            pill = QLabel()
            pill.setFixedSize(24, 14)
            pill.setStyleSheet(f"background-color: {c.color}; border-radius: 3px;")
            pill_wrap = QWidget()
            pw_layout = QHBoxLayout(pill_wrap)
            pw_layout.setContentsMargins(6, 4, 6, 4)
            pw_layout.addWidget(pill)
            self.table_cats.setCellWidget(row, 2, pill_wrap)

            # Action: Edit & Delete
            act_wrap = QWidget()
            aw_layout = QHBoxLayout(act_wrap)
            aw_layout.setContentsMargins(4, 2, 4, 2)
            aw_layout.setSpacing(6)

            btn_edit = QPushButton("Edit")
            btn_edit.setProperty("class", "secondary-btn")
            btn_edit.setFixedHeight(24)
            btn_edit.clicked.connect(lambda _, cat=c: self._edit_category(cat))
            aw_layout.addWidget(btn_edit)

            btn_del = QPushButton("Delete")
            btn_del.setProperty("class", "danger-btn")
            btn_del.setFixedHeight(24)
            btn_del.clicked.connect(lambda _, cat_id=c.id: self._delete_category(cat_id))
            aw_layout.addWidget(btn_del)

            self.table_cats.setCellWidget(row, 3, act_wrap)

        # Recurring
        recs = self.service.rec_repo.get_all()
        self.table_recs.setRowCount(len(recs))
        for row, r in enumerate(recs):
            item_desc = QTableWidgetItem(r.description)
            item_desc.setFont(ThemeManager.font_sans(size=9, bold=True))
            self.table_recs.setItem(row, 0, item_desc)

            item_cat = QTableWidgetItem(r.category_name or "—")
            item_cat.setFont(ThemeManager.font_sans(size=9))
            self.table_recs.setItem(row, 1, item_cat)

            sign = "+" if r.type == "income" else "-"
            color = COLORS.INCOME if r.type == "income" else COLORS.EXPENSE
            item_amt = QTableWidgetItem(f"{sign}{r.amount:,.2f} {currency}")
            item_amt.setFont(ThemeManager.font_sans(size=9, bold=True))
            item_amt.setForeground(QColor(color))
            self.table_recs.setItem(row, 2, item_amt)

            item_day = QTableWidgetItem(f"Day {r.day_of_month}")
            item_day.setFont(ThemeManager.font_sans(size=9))
            self.table_recs.setItem(row, 3, item_day)

            # Delete button
            btn_del_r = QPushButton("Delete")
            btn_del_r.setProperty("class", "danger-btn")
            btn_del_r.setFixedHeight(24)
            btn_del_r.clicked.connect(lambda _, rid=r.id: self._delete_recurring(rid))
            rw = QWidget()
            rw_l = QHBoxLayout(rw)
            rw_l.setContentsMargins(4, 2, 4, 2)
            rw_l.addWidget(btn_del_r)
            self.table_recs.setCellWidget(row, 4, rw)

    def _on_currency_changed(self) -> None:
        code = self.combo_currency.currentData()
        if code:
            self.service.set_currency(code)
            self.currency_changed.emit(code)
            self.reload_data()
            show_toast(self, f"Active currency set to {code}.", "Settings Updated", level="success")

    def _on_theme_changed(self) -> None:
        theme = self.combo_theme.currentData()
        if theme:
            self.service.set_theme(theme)
            ThemeManager.set_theme(theme)
            self.theme_changed.emit(theme)
            self.apply_theme()
            show_toast(self, f"Switched to {theme.capitalize()} Theme.", "Appearance Updated", level="info")

    def _add_category(self) -> None:
        dlg = CategoryDialog(parent=self)
        if dlg.exec():
            c = dlg.result_category
            if c:
                try:
                    self.service.cat_repo.create(c)
                    self.reload_data()
                    self.data_changed.emit()
                    show_toast(self, f"Category '{c.name}' created.", "Created", level="success")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to create category: {e}")

    def _edit_category(self, cat: Category) -> None:
        dlg = CategoryDialog(category=cat, parent=self)
        if dlg.exec():
            c = dlg.result_category
            if c:
                try:
                    self.service.cat_repo.update(c)
                    self.reload_data()
                    self.data_changed.emit()
                    show_toast(self, f"Category '{c.name}' updated.", "Updated", level="success")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to update category: {e}")

    def _delete_category(self, cat_id: Optional[int]) -> None:
        if cat_id is None:
            return
        if self.service.cat_repo.has_transactions(cat_id):
            QMessageBox.warning(
                self,
                "Cannot Delete Category",
                "This category has recorded transactions associated with it. Please reassign or delete those transactions first.",
            )
            return

        reply = QMessageBox.question(self, "Confirm Delete", "Permanently remove this category?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.service.cat_repo.delete(cat_id)
            self.reload_data()
            self.data_changed.emit()
            show_toast(self, "Category deleted.", level="info")

    def _add_recurring(self) -> None:
        cats = self.service.cat_repo.get_all()
        dlg = RecurringDialog(categories=cats, currency=self.service.get_currency(), parent=self)
        if dlg.exec():
            r = dlg.result_recurring
            if r:
                self.service.rec_repo.create(r)
                self.reload_data()
                show_toast(self, "Recurring rule established.", "Success", level="success")

    def _delete_recurring(self, rec_id: Optional[int]) -> None:
        if rec_id is None:
            return
        reply = QMessageBox.question(self, "Confirm Delete", "Remove this recurring rule?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.service.rec_repo.delete(rec_id)
            self.reload_data()
            show_toast(self, "Recurring rule deleted.", level="info")

    def _backup_db(self) -> None:
        default_name = f"spendwise_backup_{os.getpid()}.db"
        dest, _ = QFileDialog.getSaveFileName(self, "Backup Database", default_name, "SQLite Database (*.db)")
        if dest:
            try:
                self.service.db.backup(dest)
                show_toast(self, f"Database saved to {os.path.basename(dest)}", "Backup Complete", level="success")
            except Exception as e:
                QMessageBox.critical(self, "Backup Failed", f"Could not create backup: {e}")

    def _restore_db(self) -> None:
        src, _ = QFileDialog.getOpenFileName(self, "Restore Database", "", "SQLite Database (*.db)")
        if src:
            reply = QMessageBox.warning(
                self,
                "Confirm Restore",
                "Restoring a database will overwrite all current SpendWise data. Are you sure you wish to continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                try:
                    self.service.db.restore(src)
                    self.reload_data()
                    self.data_changed.emit()
                    show_toast(self, "Database restored successfully.", "Restore Complete", level="success")
                except Exception as e:
                    QMessageBox.critical(self, "Restore Failed", f"Failed to restore database: {e}")

    def _import_csv(self) -> None:
        csv_file, _ = QFileDialog.getOpenFileName(self, "Import CSV Transactions", "", "CSV Files (*.csv)")
        if not csv_file:
            return

        self.import_progress.setVisible(True)
        self.btn_import_csv.setEnabled(False)

        self.worker_thread = QThread()
        self.worker = CSVImportWorker(self.service, csv_file)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._on_import_finished)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        self.worker_thread.start()

    def _on_import_finished(self, count: int, errors: list) -> None:
        self.import_progress.setVisible(False)
        self.btn_import_csv.setEnabled(True)

        if count > 0:
            self.reload_data()
            self.data_changed.emit()
            show_toast(self, f"Successfully imported {count} transactions from CSV.", "Import Successful", level="success")

        if errors:
            err_summary = "\n".join(errors[:8])
            if len(errors) > 8:
                err_summary += f"\n... and {len(errors) - 8} more errors."
            QMessageBox.warning(self, "Import Notice", f"Import finished with notices:\n\n{err_summary}")

    def apply_theme(self) -> None:
        card_bg = ThemeManager.get_card_color()
        border = ThemeManager.get_border_color()

        self.setStyleSheet(f"""
            QFrame#Card {{
                background-color: {card_bg};
                border: 1px solid {border};
                border-radius: 12px;
            }}
        """)
        self.lbl_title.setStyleSheet(f"color: {ThemeManager.get_text_primary()};")
        self.lbl_subtitle.setStyleSheet(f"color: {ThemeManager.get_text_secondary()};")
