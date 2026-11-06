"""
SpendWise Data Models
Dataclasses representing entities in the SpendWise personal expense manager.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Category:
    """Category model for income and expenses."""
    id: Optional[int]
    name: str
    type: str  # 'income' or 'expense'
    color: str  # hex color e.g. '#2F7D5B'
    icon: str  # icon identifier e.g. 'utensils', 'car', etc.

    def __post_init__(self) -> None:
        if self.type not in ("income", "expense"):
            raise ValueError(f"Invalid category type: {self.type}. Must be 'income' or 'expense'.")


@dataclass
class Transaction:
    """Transaction model representing an expense or income entry."""
    id: Optional[int]
    type: str  # 'income' or 'expense'
    amount: float
    category_id: int
    date: str  # 'YYYY-MM-DD'
    description: str = ""
    created_at: Optional[str] = None
    category_name: Optional[str] = None
    category_color: Optional[str] = None
    category_icon: Optional[str] = None

    def __post_init__(self) -> None:
        if self.type not in ("income", "expense"):
            raise ValueError(f"Invalid transaction type: {self.type}. Must be 'income' or 'expense'.")
        if self.amount <= 0:
            raise ValueError("Transaction amount must be strictly greater than 0.")
        if not self.date:
            raise ValueError("Transaction date is required.")


@dataclass
class Budget:
    """Budget model for monthly spending limits (overall or per category)."""
    id: Optional[int]
    month: str  # 'YYYY-MM'
    category_id: Optional[int]  # None for global overall monthly budget
    amount: float
    category_name: Optional[str] = None
    category_color: Optional[str] = None

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise ValueError("Budget amount must be strictly greater than 0.")
        if len(self.month) != 7 or self.month[4] != "-":
            raise ValueError(f"Invalid month format: {self.month}. Expected 'YYYY-MM'.")


@dataclass
class BudgetStatus:
    """Calculated status of a budget including spending and alert level."""
    budget: Budget
    spent: float
    percentage: float
    remaining: float
    alert_level: str  # 'normal' (<70%), 'warning' (70%-90%), 'critical' (90%-100%), 'exceeded' (>100%)


@dataclass
class Goal:
    """Savings goal model."""
    id: Optional[int]
    name: str
    target_amount: float
    saved_amount: float = 0.0
    deadline: Optional[str] = None  # 'YYYY-MM-DD' or None

    def __post_init__(self) -> None:
        if self.target_amount <= 0:
            raise ValueError("Target amount must be strictly greater than 0.")
        if self.saved_amount < 0:
            raise ValueError("Saved amount cannot be negative.")

    @property
    def progress_percentage(self) -> float:
        if self.target_amount <= 0:
            return 0.0
        return min(100.0, (self.saved_amount / self.target_amount) * 100.0)

    @property
    def is_completed(self) -> bool:
        return self.saved_amount >= self.target_amount


@dataclass
class Recurring:
    """Recurring transaction rule."""
    id: Optional[int]
    type: str  # 'income' or 'expense'
    amount: float
    category_id: int
    description: str
    day_of_month: int  # 1 to 31
    active: int = 1  # 1 for active, 0 for paused
    category_name: Optional[str] = None

    def __post_init__(self) -> None:
        if self.type not in ("income", "expense"):
            raise ValueError(f"Invalid recurring type: {self.type}. Must be 'income' or 'expense'.")
        if self.amount <= 0:
            raise ValueError("Recurring amount must be strictly greater than 0.")
        if not (1 <= self.day_of_month <= 31):
            raise ValueError("Day of month must be between 1 and 31.")


@dataclass
class MonthlySummary:
    """Aggregated financial summary for a month."""
    month: str
    income: float = 0.0
    expenses: float = 0.0
    net_savings: float = 0.0
    savings_rate: float = 0.0
    transaction_count: int = 0

