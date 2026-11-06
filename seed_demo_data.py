"""
Demo Data Seeding Script for SpendWise.
Populates realistic transactions across the last 6 months, active recurring rules,
monthly category budgets, and savings goals so the dashboard and charts look rich immediately.
"""

from __future__ import annotations
import random
from datetime import datetime, timedelta
from core.database import db
from core.models import Budget, Goal, Recurring, Transaction
from core.repositories import (
    BudgetRepository,
    CategoryRepository,
    GoalRepository,
    RecurringRepository,
    TransactionRepository,
)
from core.services import FinanceService


def seed_demo_data(reset: bool = False) -> None:
    """Populate database with rich sample data."""
    cat_repo = CategoryRepository(db)
    tx_repo = TransactionRepository(db)
    budget_repo = BudgetRepository(db)
    rec_repo = RecurringRepository(db)
    goal_repo = GoalRepository(db)
    service = FinanceService(db)

    categories = {c.name: c for c in cat_repo.get_all()}
    if not categories:
        db.init_db()
        categories = {c.name: c for c in cat_repo.get_all()}

    # Check if data already exists
    existing_txs = tx_repo.get_all(limit=10)
    if existing_txs and not reset:
        print("Database already contains transactions. Skipping demo seeding.")
        return

    print("Seeding rich demo data for SpendWise...")

    today = datetime.now()
    tx_batch = []

    # Expense templates: (category, description_list, min_amt, max_amt, frequency_per_month)
    expense_templates = [
        ("Food", ["Carrefour Market", "Organic Gourmet Market", "Italian Trattoria", "Specialty Coffee Roasters", "Artisan Bakery", "Sushi House"], 45.0, 520.0, 10),
        ("Transport", ["Shell Fuel Station", "Total Fuel Station", "Highway Toll", "Tramway Monthly Pass", "Careem Ride", "Airport Taxi"], 30.0, 400.0, 6),
        ("Bills", ["Maroc Telecom Fiber", "Lydec Water & Electricity", "Mobile 5G Plan", "Home Insurance"], 120.0, 850.0, 3),
        ("Leisure", ["Cinéma Megarama", "Weekend Coastal Getaway", "Concert Ticket", "Tennis Court Booking", "Spa & Wellness"], 150.0, 1200.0, 4),
        ("Shopping", ["Zara Man Apparel", "Massimo Dutti Shoes", "Apple Store Accessories", "Bookstore Livres", "Home Fragrances"], 180.0, 1850.0, 3),
        ("Health", ["Pharmacy Centrale", "Dental Checkup", "Vitamins & Supplements", "Optician Eyewear"], 80.0, 950.0, 2),
        ("Education", ["O'Reilly Learning Subscription", "Language Tutor Class", "Design Masterclass"], 200.0, 800.0, 2),
        ("Other", ["Dry Cleaning Service", "Postal Courier Delivery", "Bank Account Service Fee"], 40.0, 180.0, 2),
    ]

    # Generate transactions for the last 6 months
    for month_offset in range(5, -1, -1):
        # Calculate year and month
        target_date = today - timedelta(days=month_offset * 30)
        year = target_date.year
        month = target_date.month
        month_str = f"{year:04d}-{month:02d}"

        # 1. Salary Income on the 28th (or 25th)
        sal_cat = categories.get("Salary")
        if sal_cat:
            tx_batch.append(
                Transaction(
                    id=None,
                    type="income",
                    amount=26500.0,
                    category_id=sal_cat.id,  # type: ignore
                    date=f"{month_str}-28",
                    description="Monthly Executive Salary",
                )
            )

        # 2. Freelance / Consulting Income
        fl_cat = categories.get("Freelance")
        if fl_cat and month_offset in (0, 1, 3, 4):
            tx_batch.append(
                Transaction(
                    id=None,
                    type="income",
                    amount=random.choice([4500.0, 6800.0, 8200.0, 5500.0]),
                    category_id=fl_cat.id,  # type: ignore
                    date=f"{month_str}-{random.randint(10, 20):02d}",
                    description="Fintech Advisory & Architecture Consulting",
                )
            )

        # 3. Apartment Rent on the 1st
        rent_cat = categories.get("Rent")
        if rent_cat:
            tx_batch.append(
                Transaction(
                    id=None,
                    type="expense",
                    amount=5500.0,
                    category_id=rent_cat.id,  # type: ignore
                    date=f"{month_str}-01",
                    description="Luxury Apartment Rent – Downtown",
                )
            )

        # 4. Generate random expenses for this month
        max_day = today.day if month_offset == 0 else 28
        for cat_name, descs, min_a, max_a, freq in expense_templates:
            cat = categories.get(cat_name)
            if not cat:
                continue
            # Adjust frequency for current month
            actual_freq = max(1, int(freq * (max_day / 30.0))) if month_offset == 0 else freq
            for _ in range(actual_freq):
                day = random.randint(1, max(1, max_day))
                amt = round(random.uniform(min_a, max_a), 2)
                desc = random.choice(descs)
                tx_batch.append(
                    Transaction(
                        id=None,
                        type="expense",
                        amount=amt,
                        category_id=cat.id,  # type: ignore
                        date=f"{month_str}-{day:02d}",
                        description=desc,
                    )
                )

        # 5. Set up budgets for the current month and last month
        if month_offset in (0, 1):
            budget_repo.set_budget(Budget(id=None, month=month_str, category_id=None, amount=18500.0))
            if categories.get("Food"):
                budget_repo.set_budget(Budget(id=None, month=month_str, category_id=categories["Food"].id, amount=3800.0))
            if categories.get("Transport"):
                budget_repo.set_budget(Budget(id=None, month=month_str, category_id=categories["Transport"].id, amount=1600.0))
            if categories.get("Rent"):
                budget_repo.set_budget(Budget(id=None, month=month_str, category_id=categories["Rent"].id, amount=5500.0))
            if categories.get("Bills"):
                budget_repo.set_budget(Budget(id=None, month=month_str, category_id=categories["Bills"].id, amount=1400.0))
            if categories.get("Leisure"):
                budget_repo.set_budget(Budget(id=None, month=month_str, category_id=categories["Leisure"].id, amount=2200.0))
            if categories.get("Shopping"):
                budget_repo.set_budget(Budget(id=None, month=month_str, category_id=categories["Shopping"].id, amount=2500.0))

    # Commit all transactions
    tx_repo.create_many(tx_batch)
    print(f"Created {len(tx_batch)} historical transactions.")

    # 6. Recurring Transactions
    if not rec_repo.get_all():
        if categories.get("Salary"):
            rec_repo.create(Recurring(id=None, type="income", amount=26500.0, category_id=categories["Salary"].id, description="Monthly Salary", day_of_month=28, active=1))
        if categories.get("Rent"):
            rec_repo.create(Recurring(id=None, type="expense", amount=5500.0, category_id=categories["Rent"].id, description="Apartment Lease Rent", day_of_month=1, active=1))
        if categories.get("Bills"):
            rec_repo.create(Recurring(id=None, type="expense", amount=399.0, category_id=categories["Bills"].id, description="High-Speed Fiber Internet", day_of_month=5, active=1))
        if categories.get("Leisure"):
            rec_repo.create(Recurring(id=None, type="expense", amount=450.0, category_id=categories["Leisure"].id, description="Equinox Gym Membership", day_of_month=10, active=1))
        print("Created recurring transaction rules.")

    # 7. Savings Goals
    if not goal_repo.get_all():
        goal_repo.create(Goal(id=None, name="Emergency Wealth Reserve (6 Mo)", target_amount=80000.0, saved_amount=54000.0, deadline="2027-06-30"))
        goal_repo.create(Goal(id=None, name="Japan Cultural Grand Tour", target_amount=42000.0, saved_amount=28500.0, deadline="2027-10-15"))
        goal_repo.create(Goal(id=None, name="Dividend Growth Portfolio", target_amount=150000.0, saved_amount=92000.0, deadline="2028-12-31"))
        print("Created savings goals.")

    print("Demo data seeded successfully!")


if __name__ == "__main__":
    seed_demo_data(reset=False)
