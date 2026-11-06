"""
SpendWise Report Export Module
Generates high-quality PDF reports (using ReportLab) and rich Excel workbooks (using openpyxl with charts).
Styled with private-bank aesthetic: midnight navy, cream, and gold accents.
"""

from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# ReportLab imports
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics.charts.piecharts import Pie

# openpyxl imports
import openpyxl
from openpyxl.chart import BarChart, PieChart as XLSPieChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from core.models import Transaction


# Palette Constants
NAVY = colors.HexColor("#0F1B2D")
GOLD = colors.HexColor("#B8934A")
CREAM = colors.HexColor("#FAF7F0")
WARM_BORDER = colors.HexColor("#E7E1D3")
MUTED_TEXT = colors.HexColor("#6B7280")
INCOME_GREEN = colors.HexColor("#2F7D5B")
EXPENSE_BURGUNDY = colors.HexColor("#9B2C2C")


class PDFReportGenerator:
    """Generates an elegant, publication-quality financial statement PDF."""

    def __init__(self, filename: str | Path, title: str, period: str, currency: str = "MAD") -> None:
        self.filename = str(filename)
        self.title = title
        self.period = period
        self.currency = currency
        self.doc = SimpleDocTemplate(
            self.filename,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36,
        )
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self) -> None:
        self.styles.add(
            ParagraphStyle(
                name="BankTitle",
                fontName="Helvetica-Bold",
                fontSize=20,
                leading=24,
                textColor=NAVY,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="BankSubtitle",
                fontName="Helvetica",
                fontSize=11,
                leading=14,
                textColor=GOLD,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="SectionHeading",
                fontName="Helvetica-Bold",
                fontSize=13,
                leading=16,
                textColor=NAVY,
                spaceBefore=14,
                spaceAfter=6,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="NormalSmall",
                fontName="Helvetica",
                fontSize=8.5,
                leading=11,
                textColor=colors.HexColor("#222222"),
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="NormalSmallMuted",
                fontName="Helvetica",
                fontSize=8,
                leading=10,
                textColor=MUTED_TEXT,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="AmountGreen",
                fontName="Helvetica-Bold",
                fontSize=8.5,
                leading=11,
                textColor=INCOME_GREEN,
                alignment=2,  # Right aligned
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="AmountBurgundy",
                fontName="Helvetica-Bold",
                fontSize=8.5,
                leading=11,
                textColor=EXPENSE_BURGUNDY,
                alignment=2,  # Right aligned
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="CardNumber",
                fontName="Helvetica-Bold",
                fontSize=14,
                leading=17,
                textColor=NAVY,
                alignment=1,  # Center
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="CardLabel",
                fontName="Helvetica",
                fontSize=8,
                leading=10,
                textColor=MUTED_TEXT,
                alignment=1,  # Center
            )
        )

    def generate(
        self,
        summary: Dict[str, Any],
        category_breakdown: List[Dict[str, Any]],
        transactions: List[Transaction],
    ) -> None:
        """Build the complete PDF document flow."""
        story = []

        # Header Banner
        header_table = Table(
            [
                [
                    Paragraph("SPENDWISE", self.styles["BankTitle"]),
                    Paragraph(f"Statement Period: {self.period}<br/>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", self.styles["NormalSmallMuted"]),
                ],
                [
                    Paragraph("PERSONAL WEALTH & EXPENSE MANAGEMENT", self.styles["BankSubtitle"]),
                    Paragraph(f"Base Currency: <b>{self.currency}</b>", self.styles["NormalSmallMuted"]),
                ],
            ],
            colWidths=[340, 200],
        )
        header_table.setStyle(
            TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ])
        )
        story.append(header_table)
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=1.5, color=GOLD, spaceBefore=4, spaceAfter=14))

        # Executive Summary KPI Cards
        income = summary.get("income", 0.0)
        expenses = summary.get("expenses", 0.0)
        net = summary.get("net_savings", 0.0)
        savings_rate = summary.get("savings_rate", 0.0)

        card_data = [
            [
                Paragraph("TOTAL INCOME", self.styles["CardLabel"]),
                Paragraph("TOTAL EXPENSES", self.styles["CardLabel"]),
                Paragraph("NET SAVINGS", self.styles["CardLabel"]),
                Paragraph("SAVINGS RATE", self.styles["CardLabel"]),
            ],
            [
                Paragraph(f"+{income:,.2f} {self.currency}", self.styles["CardNumber"]),
                Paragraph(f"-{expenses:,.2f} {self.currency}", self.styles["CardNumber"]),
                Paragraph(f"{'+' if net >= 0 else ''}{net:,.2f} {self.currency}", self.styles["CardNumber"]),
                Paragraph(f"{savings_rate:.1f}%", self.styles["CardNumber"]),
            ],
        ]
        card_table = Table(card_data, colWidths=[135, 135, 135, 135])
        card_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F5F2EB")),
                ("BOX", (0, 0), (-1, -1), 1, WARM_BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, WARM_BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ])
        )
        story.append(card_table)
        story.append(Spacer(1, 14))

        # Category Breakdown Table & Pie Chart
        story.append(Paragraph("Category Spending Breakdown", self.styles["SectionHeading"]))

        if category_breakdown:
            cat_rows = [[
                Paragraph("<b>Category</b>", self.styles["NormalSmall"]),
                Paragraph("<b>Amount</b>", self.styles["NormalSmall"]),
                Paragraph("<b>Share</b>", self.styles["NormalSmall"]),
            ]]
            for c in category_breakdown[:10]:
                cat_rows.append([
                    Paragraph(f"• {c['category_name']}", self.styles["NormalSmall"]),
                    Paragraph(f"{c['amount']:,.2f} {self.currency}", self.styles["NormalSmall"]),
                    Paragraph(f"{c['percentage']:.1f}%", self.styles["NormalSmall"]),
                ])

            cat_table = Table(cat_rows, colWidths=[240, 160, 140])
            cat_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
                    ("TOPPADDING", (0, 0), (-1, 0), 5),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#FAF8F5"), colors.white]),
                    ("GRID", (0, 0), (-1, -1), 0.5, WARM_BORDER),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ])
            )
            story.append(cat_table)
        else:
            story.append(Paragraph("No expenses recorded for this period.", self.styles["NormalSmallMuted"]))

        story.append(Spacer(1, 14))

        # Itemized Transactions Table
        story.append(Paragraph("Transaction Ledger", self.styles["SectionHeading"]))

        if transactions:
            tx_rows = [[
                Paragraph("<b>Date</b>", self.styles["NormalSmall"]),
                Paragraph("<b>Category</b>", self.styles["NormalSmall"]),
                Paragraph("<b>Description</b>", self.styles["NormalSmall"]),
                Paragraph("<b>Type</b>", self.styles["NormalSmall"]),
                Paragraph("<b>Amount</b>", self.styles["NormalSmall"]),
            ]]

            for tx in transactions[:120]:  # Limit ledger rows for clean PDF pagination
                amt_style = self.styles["AmountGreen"] if tx.type == "income" else self.styles["AmountBurgundy"]
                sign = "+" if tx.type == "income" else "-"
                amt_text = f"{sign}{tx.amount:,.2f} {self.currency}"

                tx_rows.append([
                    Paragraph(tx.date, self.styles["NormalSmall"]),
                    Paragraph(tx.category_name or "General", self.styles["NormalSmall"]),
                    Paragraph(tx.description or "—", self.styles["NormalSmall"]),
                    Paragraph(tx.type.capitalize(), self.styles["NormalSmall"]),
                    Paragraph(amt_text, amt_style),
                ])

            tx_table = Table(tx_rows, colWidths=[65, 100, 215, 60, 100])
            tx_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
                    ("TOPPADDING", (0, 0), (-1, 0), 5),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#FBF9F6"), colors.white]),
                    ("GRID", (0, 0), (-1, -1), 0.5, WARM_BORDER),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (4, 0), (4, -1), "RIGHT"),
                ])
            )
            story.append(tx_table)
        else:
            story.append(Paragraph("No transactions found for this period.", self.styles["NormalSmallMuted"]))

        story.append(Spacer(1, 20))
        story.append(HRFlowable(width="100%", thickness=0.8, color=WARM_BORDER, spaceBefore=10, spaceAfter=8))
        story.append(Paragraph("Confidential financial statement generated by SpendWise Personal Expense Manager.", self.styles["NormalSmallMuted"]))

        self.doc.build(story)


class ExcelReportGenerator:
    """Generates a professional Excel workbook with Data & Summary sheets, plus native charts."""

    def __init__(self, filename: str | Path, currency: str = "MAD") -> None:
        self.filename = str(filename)
        self.currency = currency
        self.wb = openpyxl.Workbook()

    def generate(
        self,
        period: str,
        summary: Dict[str, Any],
        category_breakdown: List[Dict[str, Any]],
        transactions: List[Transaction],
    ) -> None:
        """Create Summary sheet and Transactions Ledger sheet with native charts."""
        # 1. Summary Sheet
        ws_summary = self.wb.active
        ws_summary.title = "Summary & Analytics"
        ws_summary.views.sheetView[0].showGridLines = True

        # Styles
        navy_header_fill = PatternFill(start_color="0F1B2D", end_color="0F1B2D", fill_type="solid")
        gold_accent_fill = PatternFill(start_color="B8934A", end_color="B8934A", fill_type="solid")
        card_fill = PatternFill(start_color="FAF7F0", end_color="FAF7F0", fill_type="solid")
        zebra_fill = PatternFill(start_color="F5F2EB", end_color="F5F2EB", fill_type="solid")

        font_title = Font(name="Calibri", size=16, bold=True, color="0F1B2D")
        font_sub = Font(name="Calibri", size=10, color="6B7280")
        font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        font_bold = Font(name="Calibri", size=11, bold=True, color="0F1B2D")
        font_income = Font(name="Calibri", size=11, bold=True, color="2F7D5B")
        font_expense = Font(name="Calibri", size=11, bold=True, color="9B2C2C")

        thin_border = Border(
            left=Side(style="thin", color="E7E1D3"),
            right=Side(style="thin", color="E7E1D3"),
            top=Side(style="thin", color="E7E1D3"),
            bottom=Side(style="thin", color="E7E1D3"),
        )

        # Title Block
        ws_summary["A1"] = "SPENDWISE – EXECUTIVE FINANCIAL REPORT"
        ws_summary["A1"].font = font_title
        ws_summary["A2"] = f"Period: {period} | Base Currency: {self.currency} | Generated: {datetime.now().strftime('%Y-%m-%d')}"
        ws_summary["A2"].font = font_sub

        # KPI Table
        kpi_headers = ["Metric", "Amount", "Currency"]
        for col_idx, h in enumerate(kpi_headers, start=1):
            cell = ws_summary.cell(row=4, column=col_idx, value=h)
            cell.font = font_header
            cell.fill = navy_header_fill
            cell.alignment = Alignment(horizontal="center")

        kpis = [
            ("Total Income", summary.get("income", 0.0), font_income),
            ("Total Expenses", summary.get("expenses", 0.0), font_expense),
            ("Net Savings", summary.get("net_savings", 0.0), font_bold),
            ("Savings Rate (%)", summary.get("savings_rate", 0.0), font_bold),
        ]

        for r_idx, (label, val, f_style) in enumerate(kpis, start=5):
            c1 = ws_summary.cell(row=r_idx, column=1, value=label)
            c2 = ws_summary.cell(row=r_idx, column=2, value=val)
            c3 = ws_summary.cell(row=r_idx, column=3, value=self.currency if "%" not in label else "%")
            c1.font = font_bold
            c2.font = f_style
            c3.font = font_sub
            c2.number_format = "#,##0.00" if "%" not in label else "0.0%"
            for c in (c1, c2, c3):
                c.border = thin_border
                c.fill = card_fill

        # Category Breakdown Table
        ws_summary.cell(row=11, column=1, value="Category Spending").font = font_bold
        cat_headers = ["Category", "Amount", "Share (%)"]
        for col_idx, h in enumerate(cat_headers, start=1):
            cell = ws_summary.cell(row=12, column=col_idx, value=h)
            cell.font = font_header
            cell.fill = navy_header_fill

        cat_start_row = 13
        for idx, cat in enumerate(category_breakdown):
            curr_row = cat_start_row + idx
            c_name = ws_summary.cell(row=curr_row, column=1, value=cat["category_name"])
            c_amt = ws_summary.cell(row=curr_row, column=2, value=cat["amount"])
            c_pct = ws_summary.cell(row=curr_row, column=3, value=cat["percentage"] / 100.0)

            c_amt.number_format = "#,##0.00"
            c_pct.number_format = "0.0%"
            for cell in (c_name, c_amt, c_pct):
                cell.border = thin_border
                if idx % 2 == 1:
                    cell.fill = zebra_fill

        cat_end_row = max(cat_start_row + len(category_breakdown) - 1, cat_start_row)

        # Add native openpyxl Pie Chart for category spending
        if category_breakdown:
            pie = XLSPieChart()
            pie.title = "Expenses by Category"
            labels = Reference(ws_summary, min_col=1, min_row=cat_start_row, max_row=cat_end_row)
            data = Reference(ws_summary, min_col=2, min_row=12, max_row=cat_end_row)
            pie.add_data(data, titles_from_data=True)
            pie.set_categories(labels)
            pie.width = 14
            pie.height = 8.5
            ws_summary.add_chart(pie, "E4")

        # 2. Transactions Sheet
        ws_tx = self.wb.create_sheet(title="Transactions Ledger")
        ws_tx.views.sheetView[0].showGridLines = True

        tx_headers = ["ID", "Date", "Category", "Type", "Amount", "Currency", "Description"]
        for col_idx, h in enumerate(tx_headers, start=1):
            cell = ws_tx.cell(row=1, column=col_idx, value=h)
            cell.font = font_header
            cell.fill = navy_header_fill
            cell.alignment = Alignment(horizontal="center")

        for r_idx, tx in enumerate(transactions, start=2):
            c_id = ws_tx.cell(row=r_idx, column=1, value=tx.id)
            c_date = ws_tx.cell(row=r_idx, column=2, value=tx.date)
            c_cat = ws_tx.cell(row=r_idx, column=3, value=tx.category_name or "General")
            c_type = ws_tx.cell(row=r_idx, column=4, value=tx.type.capitalize())
            c_amt = ws_tx.cell(row=r_idx, column=5, value=tx.amount)
            c_curr = ws_tx.cell(row=r_idx, column=6, value=self.currency)
            c_desc = ws_tx.cell(row=r_idx, column=7, value=tx.description or "")

            c_amt.number_format = "#,##0.00"
            c_amt.font = font_income if tx.type == "income" else font_expense

            if r_idx % 2 == 1:
                for c in (c_id, c_date, c_cat, c_type, c_amt, c_curr, c_desc):
                    c.fill = zebra_fill
            for c in (c_id, c_date, c_cat, c_type, c_amt, c_curr, c_desc):
                c.border = thin_border

        # Adjust column widths automatically
        for sheet in (ws_summary, ws_tx):
            for col in sheet.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    val_str = str(cell.value or "")
                    if len(val_str) > max_len:
                        max_len = len(val_str)
                sheet.column_dimensions[col_letter].width = max(max_len + 3, 12)

        self.wb.save(self.filename)
