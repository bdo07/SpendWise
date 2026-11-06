"""
SpendWise Budgets & Goals Page
Manages:
- Monthly Global Budget & Per-Category Budgets
- Color-coded progress bars (Green <70%, Amber 70-90%, Red >90%)
- Quick budget editing dialog
- Copy from previous month button
- Savings goals with progress bars and contribution dialog
"""

from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from core.models import Budget, Category, Goal
from core.services import FinanceService
from ui.theme import COLORS, ThemeManager
from ui.widgets.budget_bar import BudgetBar
from ui.widgets.toast import show_toast


class BudgetEditDialog(QDialog):
    """Dialog to create or update a monthly budget."""

    def __init__(
        self,
        month: str,
        categories: List[Category],
        existing_budget: Optional[Budget] = None,
        currency: str = "MAD",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.month = month
        self.categories = categories
        self.existing_budget = existing_budget
        self.currency = currency
        self.result_budget: Optional[Budget] = None

        self.setWindowTitle("Set Monthly Budget")
        self.setFixedWidth(400)
        self.setModal(True)

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        lbl_title = QLabel("Configure Budget Limit")
        lbl_title.setFont(ThemeManager.font_serif(size=15, bold=True))
        lbl_title.setStyleSheet(f"color: {ThemeManager.get_text_primary()};")
        layout.addWidget(lbl_title)

        form = QFormLayout()
        form.setSpacing(12)

        # Target (Global or Category)
        self.combo_target = QComboBox()
        self.combo_target.setFixedHeight(36)
        self.combo_target.addItem("Overall Monthly Spending Limit (Global)", None)
        expense_cats = [c for c in self.categories if c.type == "expense"]
        for c in expense_cats:
            self.combo_target.addItem(f"Category: {c.name}", c.id)

        form.addRow("Scope *", self.combo_target)

        # Amount
        self.spin_amount = QDoubleSpinBox()
        self.spin_amount.setRange(10.0, 10_000_000.0)
        self.spin_amount.setDecimals(2)
        self.spin_amount.setSuffix(f" {self.currency}")
        self.spin_amount.setValue(5000.0)
        self.spin_amount.setFixedHeight(36)
        form.addRow("Limit *", self.spin_amount)

        layout.addLayout(form)

        if self.existing_budget:
            self.spin_amount.setValue(self.existing_budget.amount)
            if self.existing_budget.category_id is not None:
                idx = self.combo_target.findData(self.existing_budget.category_id)
                if idx >= 0:
                    self.combo_target.setCurrentIndex(idx)
                    self.combo_target.setEnabled(False)  # Lock scope when editing

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setProperty("class", "secondary-btn")
        self.btn_cancel.setFixedHeight(34)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("Save Budget")
        self.btn_save.setProperty("class", "primary-btn")
        self.btn_save.setFixedHeight(34)
        self.btn_save.clicked.connect(self._save)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

    def _save(self) -> None:
        cat_id = self.combo_target.currentData()
        amount = self.spin_amount.value()
        self.result_budget = Budget(
            id=self.existing_budget.id if self.existing_budget else None,
            month=self.month,
            category_id=cat_id,
            amount=amount,
        )
        self.accept()


class GoalDialog(QDialog):
    """Dialog to create or edit a savings goal."""

    def __init__(
        self,
        goal: Optional[Goal] = None,
        currency: str = "MAD",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.goal = goal
        self.currency = currency
        self.result_goal: Optional[Goal] = None

        self.setWindowTitle("Edit Savings Goal" if goal else "New Savings Goal")
        self.setFixedWidth(400)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        lbl_title = QLabel("Savings Goal Details")
        lbl_title.setFont(ThemeManager.font_serif(size=15, bold=True))
        layout.addWidget(lbl_title)

        form = QFormLayout()
        form.setSpacing(12)

        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("e.g. Dream Vacation or Emergency Fund")
        self.edit_name.setFixedHeight(36)
        form.addRow("Goal Name *", self.edit_name)

        self.spin_target = QDoubleSpinBox()
        self.spin_target.setRange(100.0, 10_000_000.0)
        self.spin_target.setDecimals(2)
        self.spin_target.setSuffix(f" {self.currency}")
        self.spin_target.setValue(20000.0)
        self.spin_target.setFixedHeight(36)
        form.addRow("Target Amount *", self.spin_target)

        self.spin_saved = QDoubleSpinBox()
        self.spin_saved.setRange(0.0, 10_000_000.0)
        self.spin_saved.setDecimals(2)
        self.spin_saved.setSuffix(f" {self.currency}")
        self.spin_saved.setValue(0.0)
        self.spin_saved.setFixedHeight(36)
        form.addRow("Current Savings", self.spin_saved)

        self.edit_deadline = QLineEdit()
        self.edit_deadline.setPlaceholderText("YYYY-MM-DD (Optional)")
        self.edit_deadline.setFixedHeight(36)
        form.addRow("Target Date", self.edit_deadline)

        layout.addLayout(form)

        if self.goal:
            self.edit_name.setText(self.goal.name)
            self.spin_target.setValue(self.goal.target_amount)
            self.spin_saved.setValue(self.goal.saved_amount)
            if self.goal.deadline:
                self.edit_deadline.setText(self.goal.deadline)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setProperty("class", "secondary-btn")
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton("Save Goal")
        btn_save.setProperty("class", "primary-btn")
        btn_save.clicked.connect(self._save)

        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def _save(self) -> None:
        name = self.edit_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Goal name is required.")
            return

        target = self.spin_target.value()
        saved = self.spin_saved.value()
        deadline = self.edit_deadline.text().strip() or None

        self.result_goal = Goal(
            id=self.goal.id if self.goal else None,
            name=name,
            target_amount=target,
            saved_amount=saved,
            deadline=deadline,
        )
        self.accept()


class BudgetsPage(QWidget):
    """Budgets & Savings Goals management view."""

    data_changed = Signal()

    def __init__(self, service: FinanceService, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.service = service
        self.current_month = datetime.now().strftime("%Y-%m")

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

        # 1. Header Row
        header_layout = QHBoxLayout()
        title_layout = QVBoxLayout()
        self.lbl_title = QLabel("Budgets & Savings Goals")
        self.lbl_title.setFont(ThemeManager.font_serif(size=22, bold=True))
        self.lbl_subtitle = QLabel("Set spending ceilings, monitor consumption thresholds, and grow reserves")
        self.lbl_subtitle.setFont(ThemeManager.font_sans(size=11))
        self.lbl_subtitle.setStyleSheet(f"color: {ThemeManager.get_text_secondary()};")
        title_layout.addWidget(self.lbl_title)
        title_layout.addWidget(self.lbl_subtitle)
        header_layout.addLayout(title_layout)

        header_layout.addStretch()

        # Month Selector
        self.combo_month = QComboBox()
        self.combo_month.setFixedWidth(160)
        self.combo_month.setFixedHeight(38)
        self._populate_months()
        self.combo_month.currentTextChanged.connect(self._on_month_changed)
        header_layout.addWidget(self.combo_month)

        # Copy Previous Month
        self.btn_copy_prev = QPushButton("Copy from Prior Month")
        self.btn_copy_prev.setProperty("class", "secondary-btn")
        self.btn_copy_prev.setFixedHeight(38)
        self.btn_copy_prev.clicked.connect(self._copy_previous_month)
        header_layout.addWidget(self.btn_copy_prev)

        # Set Budget Button
        self.btn_add_budget = QPushButton("+ Set Budget")
        self.btn_add_budget.setProperty("class", "primary-btn")
        self.btn_add_budget.setFixedHeight(38)
        self.btn_add_budget.clicked.connect(self._set_budget)
        header_layout.addWidget(self.btn_add_budget)

        self.container_layout.addLayout(header_layout)

        # 2. Section: Monthly Spending Budgets
        section_budgets = QFrame()
        section_budgets.setObjectName("Card")
        sb_layout = QVBoxLayout(section_budgets)
        sb_layout.setContentsMargins(20, 18, 20, 18)
        sb_layout.setSpacing(16)

        lbl_sec1 = QLabel("Monthly Budget Ceilings")
        lbl_sec1.setFont(ThemeManager.font_serif(size=15, bold=True))
        lbl_sec1.setStyleSheet(f"color: {ThemeManager.get_text_primary()};")
        sb_layout.addWidget(lbl_sec1)

        # Budgets List Container
        self.budgets_layout = QVBoxLayout()
        self.budgets_layout.setSpacing(12)
        sb_layout.addLayout(self.budgets_layout)

        section_budgets.setGraphicsEffect(ThemeManager.create_card_shadow(section_budgets))
        self.container_layout.addWidget(section_budgets)

        # 3. Section: Savings Goals
        section_goals = QFrame()
        section_goals.setObjectName("Card")
        sg_layout = QVBoxLayout(section_goals)
        sg_layout.setContentsMargins(20, 18, 20, 18)
        sg_layout.setSpacing(16)

        goals_header = QHBoxLayout()
        lbl_sec2 = QLabel("Capital & Savings Reserves")
        lbl_sec2.setFont(ThemeManager.font_serif(size=15, bold=True))
        lbl_sec2.setStyleSheet(f"color: {ThemeManager.get_text_primary()};")
        goals_header.addWidget(lbl_sec2)
        goals_header.addStretch()

        self.btn_add_goal = QPushButton("+ New Savings Goal")
        self.btn_add_goal.setProperty("class", "primary-btn")
        self.btn_add_goal.setFixedHeight(32)
        self.btn_add_goal.clicked.connect(self._add_goal)
        goals_header.addWidget(self.btn_add_goal)
        sg_layout.addLayout(goals_header)

        # Goals Grid / List
        self.goals_layout = QVBoxLayout()
        self.goals_layout.setSpacing(12)
        sg_layout.addLayout(self.goals_layout)

        section_goals.setGraphicsEffect(ThemeManager.create_card_shadow(section_goals))
        self.container_layout.addWidget(section_goals)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)
        self.apply_theme()

    def _populate_months(self) -> None:
        self.combo_month.blockSignals(True)
        self.combo_month.clear()
        available = self.service.tx_repo.get_available_months()
        curr = datetime.now().strftime("%Y-%m")
        if curr not in available:
            available.insert(0, curr)

        for m in available:
            dt = datetime.strptime(m, "%Y-%m")
            self.combo_month.addItem(dt.strftime("%B %Y"), m)

        idx = self.combo_month.findData(self.current_month)
        if idx >= 0:
            self.combo_month.setCurrentIndex(idx)
        self.combo_month.blockSignals(False)

    def _on_month_changed(self) -> None:
        m = self.combo_month.currentData()
        if m:
            self.current_month = m
            self.reload_data()

    def reload_data(self) -> None:
        """Render all active budgets and savings goals."""
        currency = self.service.get_currency()

        # Clear existing budget items
        while self.budgets_layout.count():
            item = self.budgets_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # Fetch statuses
        statuses = self.service.get_budget_statuses(self.current_month)

        if not statuses:
            lbl_empty = QLabel("No budget limits defined for this month. Click '+ Set Budget' to establish spending controls.")
            lbl_empty.setFont(ThemeManager.font_sans(size=10))
            lbl_empty.setStyleSheet(f"color: {ThemeManager.get_text_secondary()}; padding: 12px 0;")
            self.budgets_layout.addWidget(lbl_empty)
        else:
            for st in statuses:
                bar_container = QWidget()
                bc_layout = QHBoxLayout(bar_container)
                bc_layout.setContentsMargins(0, 0, 0, 0)
                bc_layout.setSpacing(10)

                name = st.budget.category_name or "Overall Monthly Budget"
                bar = BudgetBar(name, st.spent, st.budget.amount, currency)
                bc_layout.addWidget(bar, stretch=1)

                # Edit / Delete buttons
                btn_del = QPushButton("Delete")
                btn_del.setProperty("class", "danger-btn")
                btn_del.setFixedHeight(30)
                btn_del.clicked.connect(lambda _, bid=st.budget.id: self._delete_budget(bid))
                bc_layout.addWidget(btn_del)

                self.budgets_layout.addWidget(bar_container)

        # Render Savings Goals
        while self.goals_layout.count():
            item = self.goals_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        goals = self.service.goal_repo.get_all()
        if not goals:
            lbl_no_goals = QLabel("No savings goals defined. Create a reserve target to track your progress.")
            lbl_no_goals.setFont(ThemeManager.font_sans(size=10))
            lbl_no_goals.setStyleSheet(f"color: {ThemeManager.get_text_secondary()}; padding: 12px 0;")
            self.goals_layout.addWidget(lbl_no_goals)
        else:
            for g in goals:
                g_card = QFrame()
                g_layout = QVBoxLayout(g_card)
                g_layout.setContentsMargins(16, 12, 16, 12)
                g_layout.setSpacing(8)

                top = QHBoxLayout()
                lbl_g_name = QLabel(g.name)
                lbl_g_name.setFont(ThemeManager.font_sans(size=11, bold=True))
                lbl_g_name.setStyleSheet(f"color: {ThemeManager.get_text_primary()};")

                pct = g.progress_percentage
                lbl_g_val = QLabel(f"{g.saved_amount:,.2f} / {g.target_amount:,.2f} {currency} ({pct:.1f}%)")
                lbl_g_val.setFont(ThemeManager.font_sans(size=10))
                lbl_g_val.setStyleSheet(f"color: {COLORS.INCOME if g.is_completed else ThemeManager.get_text_secondary()};")

                top.addWidget(lbl_g_name)
                top.addStretch()
                top.addWidget(lbl_g_val)
                g_layout.addLayout(top)

                # Progress bar
                from PySide6.QtWidgets import QProgressBar
                pbar = QProgressBar()
                pbar.setRange(0, 100)
                pbar.setValue(int(min(100, pct)))
                pbar.setTextVisible(False)
                pbar.setFixedHeight(8)
                pbar.setStyleSheet(f"""
                    QProgressBar {{
                        background-color: {ThemeManager.get_border_color()};
                        border: none;
                        border-radius: 4px;
                    }}
                    QProgressBar::chunk {{
                        background-color: {COLORS.INCOME if g.is_completed else COLORS.GOLD};
                        border-radius: 4px;
                    }}
                """)
                g_layout.addWidget(pbar)

                # Bottom actions row
                b_row = QHBoxLayout()
                deadline_text = f"Deadline: {g.deadline}" if g.deadline else "No deadline set"
                lbl_dead = QLabel(deadline_text)
                lbl_dead.setFont(ThemeManager.font_sans(size=9))
                lbl_dead.setStyleSheet(f"color: {ThemeManager.get_text_secondary()};")
                b_row.addWidget(lbl_dead)
                b_row.addStretch()

                btn_add_money = QPushButton("+ Add Funds")
                btn_add_money.setProperty("class", "secondary-btn")
                btn_add_money.setFixedHeight(28)
                btn_add_money.clicked.connect(lambda _, gid=g.id: self._contribute_goal(gid))
                b_row.addWidget(btn_add_money)

                btn_del_g = QPushButton("Delete")
                btn_del_g.setProperty("class", "danger-btn")
                btn_del_g.setFixedHeight(28)
                btn_del_g.clicked.connect(lambda _, gid=g.id: self._delete_goal(gid))
                b_row.addWidget(btn_del_g)

                g_layout.addLayout(b_row)

                border = ThemeManager.get_border_color()
                card_bg = ThemeManager.get_card_color()
                g_card.setStyleSheet(f"""
                    QFrame {{
                        background-color: {card_bg};
                        border: 1px solid {border};
                        border-radius: 8px;
                    }}
                """)
                self.goals_layout.addWidget(g_card)

    def _set_budget(self) -> None:
        cats = self.service.cat_repo.get_all()
        dlg = BudgetEditDialog(self.current_month, cats, currency=self.service.get_currency(), parent=self)
        if dlg.exec():
            b = dlg.result_budget
            if b:
                self.service.budget_repo.set_budget(b)
                self.reload_data()
                self.data_changed.emit()
                show_toast(self, "Budget target saved.", "Success", level="success")

    def _delete_budget(self, budget_id: Optional[int]) -> None:
        if budget_id is None:
            return
        reply = QMessageBox.question(self, "Confirm Delete", "Remove this budget limit?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.service.budget_repo.delete(budget_id)
            self.reload_data()
            self.data_changed.emit()
            show_toast(self, "Budget limit deleted.", level="info")

    def _copy_previous_month(self) -> None:
        """Calculate previous month and clone budgets."""
        dt = datetime.strptime(self.current_month, "%Y-%m")
        # Go back 1 month
        prev_year = dt.year if dt.month > 1 else dt.year - 1
        prev_month = dt.month - 1 if dt.month > 1 else 12
        prev_str = f"{prev_year:04d}-{prev_month:02d}"

        count = self.service.budget_repo.copy_budgets_from_previous_month(prev_str, self.current_month)
        if count > 0:
            self.reload_data()
            self.data_changed.emit()
            show_toast(self, f"Successfully cloned {count} budget(s) from {prev_str}.", "Budgets Copied", level="success")
        else:
            QMessageBox.information(self, "No Prior Budgets", f"No budgets found in {prev_str} to copy.")

    def _add_goal(self) -> None:
        dlg = GoalDialog(currency=self.service.get_currency(), parent=self)
        if dlg.exec():
            g = dlg.result_goal
            if g:
                self.service.goal_repo.create(g)
                self.reload_data()
                show_toast(self, "Savings goal created.", "Goal Saved", level="success")

    def _contribute_goal(self, goal_id: Optional[int]) -> None:
        if goal_id is None:
            return
        from PySide6.QtWidgets import QInputDialog
        amt, ok = QInputDialog.getDouble(
            self,
            "Contribute to Savings Goal",
            f"Enter contribution amount ({self.service.get_currency()}):",
            100.0,
            1.0,
            1000000.0,
            2,
        )
        if ok and amt > 0:
            self.service.goal_repo.add_savings(goal_id, amt)
            self.reload_data()
            show_toast(self, f"Added {amt:,.2f} {self.service.get_currency()} to reserve.", "Contribution Added", level="success")

    def _delete_goal(self, goal_id: Optional[int]) -> None:
        if goal_id is None:
            return
        reply = QMessageBox.question(self, "Confirm Delete", "Are you sure you want to remove this savings goal?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.service.goal_repo.delete(goal_id)
            self.reload_data()
            show_toast(self, "Savings goal removed.", level="info")

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
