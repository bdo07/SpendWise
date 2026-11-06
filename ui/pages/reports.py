"""
SpendWise Reports Page
Generates executive PDF statements (ReportLab) and Excel workbooks (openpyxl).
Uses background QThread workers to ensure zero UI freezing during heavy document rendering.
"""

from __future__ import annotations
import os
import subprocess
from datetime import datetime
from typing import Any, Dict, List, Optional
from PySide6.QtCore import QDate, QObject, QThread, Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDateEdit,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from core.export import ExcelReportGenerator, PDFReportGenerator
from core.models import Transaction
from core.services import FinanceService
from ui.theme import COLORS, ThemeManager
from ui.widgets.stat_card import StatCard
from ui.widgets.toast import show_toast


class ExportWorker(QObject):
    """Background worker thread for generating PDF or Excel reports."""

    finished = Signal(str)  # Emits generated file path
    error = Signal(str)

    def __init__(
        self,
        export_type: str,  # 'pdf' or 'excel'
        destination: str,
        period: str,
        currency: str,
        summary: Dict[str, Any],
        category_breakdown: List[Dict[str, Any]],
        transactions: List[Transaction],
    ) -> None:
        super().__init__()
        self.export_type = export_type
        self.destination = destination
        self.period = period
        self.currency = currency
        self.summary = summary
        self.category_breakdown = category_breakdown
        self.transactions = transactions

    def run(self) -> None:
        """Execute document compilation in worker thread."""
        try:
            if self.export_type == "pdf":
                generator = PDFReportGenerator(
                    filename=self.destination,
                    title="Executive Financial Statement",
                    period=self.period,
                    currency=self.currency,
                )
                generator.generate(
                    summary=self.summary,
                    category_breakdown=self.category_breakdown,
                    transactions=self.transactions,
                )
            elif self.export_type == "excel":
                generator = ExcelReportGenerator(
                    filename=self.destination,
                    currency=self.currency,
                )
                generator.generate(
                    period=self.period,
                    summary=self.summary,
                    category_breakdown=self.category_breakdown,
                    transactions=self.transactions,
                )
            self.finished.emit(self.destination)
        except Exception as e:
            self.error.emit(str(e))


class ReportsPage(QWidget):
    """Report generation and export interface."""

    def __init__(self, service: FinanceService, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.service = service
        self.current_month = datetime.now().strftime("%Y-%m")
        self.worker_thread: Optional[QThread] = None

        self._setup_ui()
        self.update_preview()

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
        self.lbl_title = QLabel("Executive Statements & Reports")
        self.lbl_title.setFont(ThemeManager.font_serif(size=22, bold=True))
        self.lbl_subtitle = QLabel("Generate publication-ready PDF statements or multi-sheet Excel workbooks")
        self.lbl_subtitle.setFont(ThemeManager.font_sans(size=11))
        self.lbl_subtitle.setStyleSheet(f"color: {ThemeManager.get_text_secondary()};")
        title_layout.addWidget(self.lbl_title)
        title_layout.addWidget(self.lbl_subtitle)
        header_layout.addLayout(title_layout)
        self.container_layout.addLayout(header_layout)

        # 2. Scope & Period Configuration Card
        config_card = QFrame()
        config_card.setObjectName("Card")
        cc_layout = QVBoxLayout(config_card)
        cc_layout.setContentsMargins(20, 18, 20, 18)
        cc_layout.setSpacing(14)

        lbl_scope_title = QLabel("Select Reporting Period")
        lbl_scope_title.setFont(ThemeManager.font_serif(size=14, bold=True))
        lbl_scope_title.setStyleSheet(f"color: {ThemeManager.get_text_primary()};")
        cc_layout.addWidget(lbl_scope_title)

        # Radio buttons: By Month vs Custom Range
        radio_layout = QHBoxLayout()
        self.rb_month = QRadioButton("Specific Month")
        self.rb_month.setChecked(True)
        self.rb_custom = QRadioButton("Custom Date Range")

        self.radio_group = QButtonGroup(self)
        self.radio_group.addButton(self.rb_month)
        self.radio_group.addButton(self.rb_custom)
        self.rb_month.toggled.connect(self._on_scope_type_toggled)

        radio_layout.addWidget(self.rb_month)
        radio_layout.addWidget(self.rb_custom)
        radio_layout.addStretch()
        cc_layout.addLayout(radio_layout)

        # Controls row
        ctrl_layout = QHBoxLayout()

        # Month combo
        self.combo_month = QComboBox()
        self.combo_month.setFixedWidth(200)
        self.combo_month.setFixedHeight(36)
        self._populate_months()
        self.combo_month.currentTextChanged.connect(self.update_preview)
        ctrl_layout.addWidget(self.combo_month)

        # Custom date pickers
        self.lbl_from = QLabel("From:")
        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDisplayFormat("yyyy-MM-dd")
        self.date_start.setDate(QDate.currentDate().addMonths(-1))
        self.date_start.setFixedHeight(36)
        self.date_start.dateChanged.connect(self.update_preview)

        self.lbl_to = QLabel("To:")
        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setDisplayFormat("yyyy-MM-dd")
        self.date_end.setDate(QDate.currentDate())
        self.date_end.setFixedHeight(36)
        self.date_end.dateChanged.connect(self.update_preview)

        ctrl_layout.addWidget(self.lbl_from)
        ctrl_layout.addWidget(self.date_start)
        ctrl_layout.addWidget(self.lbl_to)
        ctrl_layout.addWidget(self.date_end)
        ctrl_layout.addStretch()
        cc_layout.addLayout(ctrl_layout)

        self.container_layout.addWidget(config_card)

        # 3. Statement Preview Cards
        preview_label = QLabel("Statement Summary Preview")
        preview_label.setFont(ThemeManager.font_serif(size=14, bold=True))
        preview_label.setStyleSheet(f"color: {ThemeManager.get_text_primary()};")
        self.container_layout.addWidget(preview_label)

        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(16)
        self.card_income = StatCard("Income Recorded", "0.00 MAD", "Total incoming capital", value_role="income")
        self.card_expense = StatCard("Expenses Incurred", "0.00 MAD", "Total outflow", value_role="expense")
        self.card_net = StatCard("Net Statement Balance", "0.00 MAD", "Net retained savings", value_role="primary")
        self.card_tx_count = StatCard("Transactions Ledger", "0 items", "Itemized line entries", value_role="gold")

        kpi_row.addWidget(self.card_income)
        kpi_row.addWidget(self.card_expense)
        kpi_row.addWidget(self.card_net)
        kpi_row.addWidget(self.card_tx_count)
        self.container_layout.addLayout(kpi_row)

        # 4. Action Export Buttons Card
        action_card = QFrame()
        action_card.setObjectName("Card")
        ac_layout = QVBoxLayout(action_card)
        ac_layout.setContentsMargins(20, 20, 20, 20)
        ac_layout.setSpacing(14)

        lbl_ac_title = QLabel("Generate & Export Documents")
        lbl_ac_title.setFont(ThemeManager.font_serif(size=14, bold=True))
        lbl_ac_title.setStyleSheet(f"color: {ThemeManager.get_text_primary()};")
        ac_layout.addWidget(lbl_ac_title)

        lbl_ac_desc = QLabel(
            "Compile comprehensive reports formatted with executive charts, summary KPIs, and complete itemized ledgers."
        )
        lbl_ac_desc.setFont(ThemeManager.font_sans(size=10))
        lbl_ac_desc.setStyleSheet(f"color: {ThemeManager.get_text_secondary()};")
        ac_layout.addWidget(lbl_ac_desc)

        # Buttons Row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(16)

        self.btn_export_pdf = QPushButton("📄  Export Executive PDF Report")
        self.btn_export_pdf.setProperty("class", "primary-btn")
        self.btn_export_pdf.setFixedHeight(44)
        self.btn_export_pdf.clicked.connect(self._export_pdf)
        btn_row.addWidget(self.btn_export_pdf)

        self.btn_export_excel = QPushButton("📊  Export Structured Excel (.xlsx)")
        self.btn_export_excel.setProperty("class", "secondary-btn")
        self.btn_export_excel.setFixedHeight(44)
        self.btn_export_excel.clicked.connect(self._export_excel)
        btn_row.addWidget(self.btn_export_excel)

        btn_row.addStretch()
        ac_layout.addLayout(btn_row)

        # Progress bar (Indeterminate during compilation)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)
        ac_layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("")
        self.lbl_status.setFont(ThemeManager.font_sans(size=9))
        self.lbl_status.setStyleSheet(f"color: {ThemeManager.get_palette().gold};")
        self.lbl_status.setVisible(False)
        ac_layout.addWidget(self.lbl_status)

        self.container_layout.addWidget(action_card)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        self._on_scope_type_toggled()
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

    def _on_scope_type_toggled(self) -> None:
        is_month = self.rb_month.isChecked()
        self.combo_month.setVisible(is_month)
        self.lbl_from.setVisible(not is_month)
        self.date_start.setVisible(not is_month)
        self.lbl_to.setVisible(not is_month)
        self.date_end.setVisible(not is_month)
        self.update_preview()

    def _get_active_range(self) -> tuple[str, str, str]:
        """Return (start_date, end_date, period_label)."""
        if self.rb_month.isChecked():
            m = self.combo_month.currentData() or datetime.now().strftime("%Y-%m")
            dt = datetime.strptime(m, "%Y-%m")
            return f"{m}-01", f"{m}-31", dt.strftime("%B %Y")
        else:
            s_date = self.date_start.date().toString("yyyy-MM-dd")
            e_date = self.date_end.date().toString("yyyy-MM-dd")
            return s_date, e_date, f"{s_date} to {e_date}"

    def update_preview(self) -> None:
        """Fetch transactions for selected period and update preview cards."""
        start_date, end_date, _ = self._get_active_range()
        currency = self.service.get_currency()

        txs = self.service.tx_repo.get_all(start_date=start_date, end_date=end_date)
        income = sum(t.amount for t in txs if t.type == "income")
        expenses = sum(t.amount for t in txs if t.type == "expense")
        net = income - expenses

        self.card_income.update_data(f"+{income:,.2f} {currency}", value_role="income")
        self.card_expense.update_data(f"-{expenses:,.2f} {currency}", value_role="expense")
        net_role = "income" if net >= 0 else "expense"
        sign = "+" if net >= 0 else ""
        self.card_net.update_data(f"{sign}{net:,.2f} {currency}", value_role=net_role)
        self.card_tx_count.update_data(f"{len(txs)} line items", value_role="gold")

    def _export_pdf(self) -> None:
        self._start_export("pdf")

    def _export_excel(self) -> None:
        self._start_export("excel")

    def _start_export(self, export_type: str) -> None:
        """Launch background worker to generate report document."""
        start_date, end_date, period_label = self._get_active_range()
        clean_name = period_label.replace(" ", "_").replace("/", "-")
        ext = ".pdf" if export_type == "pdf" else ".xlsx"
        default_file = f"SpendWise_Statement_{clean_name}{ext}"
        filter_str = "PDF Document (*.pdf)" if export_type == "pdf" else "Excel Workbook (*.xlsx)"

        dest_path, _ = QFileDialog.getSaveFileName(self, f"Save {export_type.upper()} Report", default_file, filter_str)
        if not dest_path:
            return

        txs = self.service.tx_repo.get_all(start_date=start_date, end_date=end_date)
        income = sum(t.amount for t in txs if t.type == "income")
        expenses = sum(t.amount for t in txs if t.type == "expense")
        net = income - expenses
        savings_rate = (net / income * 100.0) if income > 0 else 0.0

        summary = {
            "income": income,
            "expenses": expenses,
            "net_savings": net,
            "savings_rate": savings_rate,
        }

        # Category breakdown for period
        # Build category sums from transactions
        cats: dict[str, dict] = {}
        for t in txs:
            if t.type == "expense":
                name = t.category_name or "General"
                cats[name] = cats.get(name, {"category_name": name, "amount": 0.0})
                cats[name]["amount"] += t.amount

        total_exp = sum(c["amount"] for c in cats.values())
        breakdown = []
        for c in sorted(cats.values(), key=lambda x: x["amount"], reverse=True):
            pct = (c["amount"] / total_exp * 100.0) if total_exp > 0 else 0.0
            breakdown.append({
                "category_name": c["category_name"],
                "amount": c["amount"],
                "percentage": pct,
            })

        # Set UI to exporting state
        self.progress_bar.setVisible(True)
        self.lbl_status.setText(f"Compiling {export_type.upper()} report...")
        self.lbl_status.setVisible(True)
        self.btn_export_pdf.setEnabled(False)
        self.btn_export_excel.setEnabled(False)

        # Thread setup
        self.worker_thread = QThread()
        self.worker = ExportWorker(
            export_type=export_type,
            destination=dest_path,
            period=period_label,
            currency=self.service.get_currency(),
            summary=summary,
            category_breakdown=breakdown,
            transactions=txs,
        )
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._on_export_finished)
        self.worker.error.connect(self._on_export_error)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.error.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        self.worker_thread.start()

    def _on_export_finished(self, file_path: str) -> None:
        self.progress_bar.setVisible(False)
        self.lbl_status.setVisible(False)
        self.btn_export_pdf.setEnabled(True)
        self.btn_export_excel.setEnabled(True)

        show_toast(self, f"Document generated: {os.path.basename(file_path)}", "Export Complete", level="success")

        # Open file or directory prompt
        reply = QMessageBox.information(
            self,
            "Statement Ready",
            f"Your report has been successfully compiled to:\n{file_path}\n\nWould you like to open it now?",
            QMessageBox.Open | QMessageBox.Close,
            QMessageBox.Open,
        )
        if reply == QMessageBox.Open:
            try:
                if os.name == "posix":
                    subprocess.call(["open", file_path])
                elif os.name == "nt":
                    os.startfile(file_path)  # type: ignore
            except Exception:
                pass

    def _on_export_error(self, err_msg: str) -> None:
        self.progress_bar.setVisible(False)
        self.lbl_status.setVisible(False)
        self.btn_export_pdf.setEnabled(True)
        self.btn_export_excel.setEnabled(True)
        QMessageBox.critical(self, "Export Failed", f"Failed to generate statement:\n{err_msg}")

    def apply_theme(self) -> None:
        p = ThemeManager.get_palette()

        self.setStyleSheet(f"""
            QFrame#Card {{
                background-color: {p.card_bg};
                border: 1px solid {p.border};
                border-radius: 12px;
            }}
        """)
        self.lbl_title.setStyleSheet(f"color: {p.text_primary};")
        self.lbl_subtitle.setStyleSheet(f"color: {p.text_secondary};")
        self.card_income.apply_theme()
        self.card_expense.apply_theme()
        self.card_net.apply_theme()
        self.card_tx_count.apply_theme()

