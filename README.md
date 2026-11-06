# SpendWise – Expense & Wealth Manager

An offline personal finance and wealth management desktop application engineered with Python 3.11+, PySide6, and SQLite (`sqlite3`). Designed with a classic, private-bank / fine stationery aesthetic (Midnight Navy, Cream, and Gold accents) to give individuals complete visibility into cash flow, spending ceilings, and capital accumulation.

---

## 🏛 Visual & Architectural Philosophy

- **Private-Bank Stationery Palette**: Midnight Navy (`#0F1B2D`), Warm Cream (`#FAF7F0`), Card White (`#FFFFFF`), Gold Accent (`#B8934A`), Income Green (`#2F7D5B`), Expense Burgundy (`#9B2C2C`), Muted Slate (`#6B7280`), and Warm Borders (`#E7E1D3`).
- **Dark Mode**: Midnight Slate (`#0B1220`) and Deep Navy Cards (`#141F33`) with consistent Gold highlights.
- **Typography**: Classic serif typography for titles and KPI metrics (`Georgia` / `Playfair Display`), clean modern sans-serif for numbers and ledger tables (`Inter` / `-apple-system`).
- **Strict Separation of Concerns**: The UI never contains business logic; all computations, thresholds, statistics, and conversions are handled exclusively by services.

---

## 📁 Project Architecture

```
SpendWise/
├── main.py                    # Application bootstrap & event loop
├── seed_demo_data.py          # Script to populate rich 6-month historical demo data
├── requirements.txt           # Production dependencies
├── pytest.ini                 # Pytest configuration
├── core/
│   ├── __init__.py
│   ├── database.py            # SQLite connection, WAL mode, foreign keys, migrations, backup/restore
│   ├── models.py              # Dataclasses: Transaction, Category, Budget, Goal, Recurring, Summary
│   ├── repositories.py        # Parameterized CRUD operations for each entity
│   ├── services.py            # Financial logic, threshold alerts, analytics, recurring generator, CSV I/O
│   └── export.py              # High-fidelity PDF (ReportLab) & Excel with native charts (openpyxl)
├── ui/
│   ├── __init__.py
│   ├── main_window.py         # Midnight navy sidebar, QStackedWidget, global shortcuts, startup hooks
│   ├── theme.py               # ThemeManager, palette constants, typography, dynamic QSS stylesheets
│   ├── pages/
│   │   ├── dashboard.py       # Executive overview: KPI cards, alert banners, budget bar, recent ledger
│   │   ├── transactions.py    # QTableView + QAbstractTableModel, search, multi-filters, CRUD dialog
│   │   ├── budgets.py         # Global & category budgets, threshold indicators, savings reserve goals
│   │   ├── statistics.py      # Donut category chart, 12-month cashflow bar chart, cumulative balance spline
│   │   ├── reports.py         # Date range selector, preview metrics, multi-threaded PDF and Excel export
│   │   └── settings.py        # Currency (MAD default), Light/Dark theme, category manager, recurring rules, DB backup
│   └── widgets/
│       ├── stat_card.py       # Styled financial KPI card with drop shadows
│       ├── budget_bar.py      # Multi-threshold progress bar (<70% green, 70-90% amber, >90% burgundy)
│       ├── transaction_dialog.py # Modal dialog with validation, type toggle, date picker
│       ├── toast.py           # Animated non-intrusive alert toast notifications
│       └── charts.py          # PySide6.QtCharts widgets styled to application palette
├── assets/
│   └── icons/                 # Crisp vector SVG line icons
└── tests/
    ├── test_services.py       # Unit tests for repositories, calculations, alerts, and document exports
    └── test_ui.py             # UI lifecycle, page switching, theme toggling, and headless tests
```

---

## 🚀 Quickstart & Setup

### 1. Prerequisites
- Python 3.11 or higher
- `pip` package manager

### 2. Create and Activate Virtual Environment
```bash
python3 -m venv .venv

# On macOS / Linux:
source .venv/bin/activate

# On Windows:
# .venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. (Optional) Seed Demo Data
To launch the app with 6 months of historical transactions, category budgets, recurring rules, and savings goals:
```bash
python seed_demo_data.py
```

### 5. Launch the Application
```bash
python main.py
```

---

## 🧪 Running Unit & Integration Tests

Run the test suite with `pytest`:
```bash
pytest
```
All 10 comprehensive unit and integration tests run in isolated test databases and headless offscreen Qt environments.

---

## 🔑 Key Features & User Guide

### 1. Executive Dashboard
- **Month Selector**: View performance across any historical month or current period.
- **KPI Metrics**: Net Monthly Savings, Total Income, Total Expenses, and Savings Rate percentage.
- **Budget Threshold Alerts**: Real-time alerts when spending approaches 70%, 90%, or exceeds 100%.
- **Category Donut Chart**: Top spending breakdown with tooltips and percentages.
- **Recent Ledger**: Instant view of the 5 most recent transactions.

### 2. Transactions Ledger
- **Custom Model**: High-performance `QTableView` with `QAbstractTableModel`.
- **Filters**: Real-time search by description/category, month selector, category filter, and Income/Expense toggle.
- **Operations**: Add, Edit, Delete (with confirmation safety prompt), and Export filtered view to CSV.
- **Formatting**: Right-aligned amounts, income in green (`#2F7D5B`), expenses in burgundy (`#9B2C2C`).

### 3. Budgets & Capital Reserves
- **Ceilings**: Set overall monthly spending limits and per-category monthly limits.
- **Color Thresholds**:
  - Green: Under 70% consumption
  - Amber: 70% – 90% warning
  - Burgundy: Over 90% critical / exceeded
- **Copy from Prior Month**: One-click rollover of previous month's budgets.
- **Savings Goals**: Track reserve funds (e.g., Emergency Reserve, Vacation, Investments) with progress bars and contribution dialogs.

### 4. Analytics & Trends
- **Expenses by Category**: Donut chart with category shares and amounts.
- **12-Month Cash Flow**: Grouped bar chart comparing income vs expenses over the last 12 months.
- **Cumulative Balance Curve**: Spline line chart showing long-term capital accumulation.

### 5. Statements & Reports
- **Executive PDF Report**: Built with `ReportLab` — includes executive header, KPI summary table, category breakdown table, and itemized transaction ledger.
- **Excel Statement (`.xlsx`)**: Built with `openpyxl` — includes a styled KPI & Category Summary Sheet with an embedded native Excel Pie Chart, and an itemized Transactions Ledger sheet.
- **Background Execution**: Export runs on background `QThread` workers so the UI never freezes.

### 6. System Settings & Data Operations
- **Currency**: Default MAD (Moroccan Dirham), customizable to USD, EUR, GBP, CAD, CHF, AED, SAR.
- **Theme**: Instant toggle between Light Mode and Dark Mode.
- **Categories**: Create, edit, and delete income/expense categories with custom colors.
- **Recurring Rules**: Setup recurring expenses or income (processed automatically on startup).
- **Database Backup & Restore**: One-click local backup and restoration of the SQLite database.
- **Bulk CSV Import**: Import bank statements with automatic category matching and validation.

---

## ⌨️ Global Keyboard Shortcuts

| Shortcut | Description |
| :--- | :--- |
| `Ctrl + N` / `Cmd + N` | Open New Transaction Dialog |
| `Ctrl + F` / `Cmd + F` | Switch to Transactions and focus Search Bar |
| `Ctrl + E` / `Cmd + E` | Switch to Statements & Reports |

---

## 🔒 Privacy & Offline Security
SpendWise stores 100% of user data locally inside an encrypted-ready SQLite database. No external network requests, third-party analytics, or telemetry are transmitted.

