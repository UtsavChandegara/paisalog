from contextlib import asynccontextmanager
from calendar import monthrange
from datetime import date, timedelta
from collections import defaultdict
import sqlite3
import uuid

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

from .database import create_tables, get_db_connection
from .models import (
    Category,
    CategoryCreate,
    DailyBalance,
    DailyBalanceCreate,
    Person,
    PersonCreate,
    SocialLedger,
    SocialLedgerCreate,
    SocialLedgerCreateWithSplits,
    SocialLedgerEntry,
    SocialLedgerGroup,
    Transaction,
    TransactionCreate,
    TransactionWithSplits,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(title="PaisaLog API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULT_CATEGORIES = [
    "Food", "Transport", "Shopping", "Rent", "Stationary",
    "Medical", "Entertainment", "Recharge", "Education", "Other"
]


@app.post(
    "/transactions",
    response_model=Transaction,
    status_code=status.HTTP_201_CREATED,
)
def create_transaction(transaction: TransactionCreate):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO transactions (date, amount, type, category, mode, note, others_share, others_person)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            transaction.date,
            transaction.amount,
            transaction.type,
            transaction.category,
            transaction.mode,
            transaction.note,
            transaction.others_share,
            transaction.others_person,
        ),
    )
    transaction_id = cursor.lastrowid
    connection.commit()

    saved_transaction = connection.execute(
        """
        SELECT id, date, amount, type, category, mode, note, created_at, others_share, others_person
        FROM transactions
        WHERE id = ?
        """,
        (transaction_id,),
    ).fetchone()

    connection.close()
    return dict(saved_transaction)


@app.get("/transactions", response_model=list[Transaction])
def get_transactions():
    connection = get_db_connection()

    transactions = connection.execute(
        """
        SELECT id, date, amount, type, category, mode, note, created_at, others_share, others_person
        FROM transactions
        ORDER BY date DESC, id DESC
        """
    ).fetchall()

    connection.close()
    return [dict(transaction) for transaction in transactions]


@app.get("/transactions/{transaction_id}", response_model=Transaction)
def get_transaction(transaction_id: int):
    connection = get_db_connection()

    transaction = connection.execute(
        """
        SELECT id, date, amount, type, category, mode, note, created_at, others_share, others_person
        FROM transactions
        WHERE id = ?
        """,
        (transaction_id,),
    ).fetchone()

    connection.close()

    if transaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    return dict(transaction)


@app.get("/statement")
def get_statement(statement_range: int = Query(7, alias="range")):
    if statement_range not in [7, 15, 30]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Range must be 7, 15, or 30",
        )

    date_to = date.today()
    date_from = date_to - timedelta(days=statement_range)

    connection = get_db_connection()
    transactions = connection.execute(
        """
        SELECT id, date, amount, type, category, mode, note, created_at, others_share, others_person
        FROM transactions
        WHERE date >= ? AND date <= ?
        ORDER BY date DESC, id DESC
        """,
        (date_from.isoformat(), date_to.isoformat()),
    ).fetchall()
    connection.close()

    transaction_list = [dict(transaction) for transaction in transactions]

    total_debit = sum(
        transaction["amount"]
        for transaction in transaction_list
        if transaction["type"] == "debit"
    )
    total_credit = sum(
        transaction["amount"]
        for transaction in transaction_list
        if transaction["type"] == "credit"
    )
    total_deposit = sum(
        transaction["amount"]
        for transaction in transaction_list
        if transaction["type"] == "deposit"
    )
    net = total_credit + total_deposit - total_debit

    return {
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "total_debit": total_debit,
        "total_credit": total_credit,
        "total_deposit": total_deposit,
        "net": net,
        "transactions": transaction_list,
    }


def get_report_dates(report_type: str, month: int | None, year: int | None):
    today = date.today()

    if report_type == "weekly":
        return today - timedelta(days=6), today

    if report_type == "15days":
        if today.day <= 15:
            return today.replace(day=1), today.replace(day=15)

        last_day = monthrange(today.year, today.month)[1]
        return today.replace(day=16), today.replace(day=last_day)

    if report_type == "monthly":
        if month is None or year is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="month and year are required for monthly reports",
            )

        if month < 1 or month > 12:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="month must be between 1 and 12",
            )

        last_day = monthrange(year, month)[1]
        return date(year, month, 1), date(year, month, last_day)

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="type must be weekly, 15days, or monthly",
    )


def balance_total(daily_balance, opening_or_closing):
    if daily_balance is None:
        return 0

    cash_value = daily_balance[f"cash_{opening_or_closing}"] or 0
    online_value = daily_balance[f"online_{opening_or_closing}"] or 0
    return cash_value + online_value


@app.get("/report")
def get_report(
    report_type: str = Query(..., alias="type"),
    month: int | None = None,
    year: int | None = None,
):
    date_from, date_to = get_report_dates(report_type, month, year)
    date_from_text = date_from.isoformat()
    date_to_text = date_to.isoformat()

    connection = get_db_connection()

    transactions = connection.execute(
        """
        SELECT id, date, amount, type, category, mode, note, created_at, others_share, others_person
        FROM transactions
        WHERE date >= ? AND date <= ?
        ORDER BY date ASC, id ASC
        """,
        (date_from_text, date_to_text),
    ).fetchall()

    daily_trail = connection.execute(
        """
        SELECT
            id,
            date,
            cash_opening,
            cash_closing,
            online_opening,
            online_closing,
            note
        FROM daily_balance
        WHERE date >= ? AND date <= ?
        ORDER BY date ASC, id ASC
        """,
        (date_from_text, date_to_text),
    ).fetchall()

    first_daily_balance = daily_trail[0] if daily_trail else None
    last_daily_balance = daily_trail[-1] if daily_trail else None
    opening_balance = balance_total(first_daily_balance, "opening")
    closing_balance = balance_total(last_daily_balance, "closing")

    social_entries = connection.execute(
        """
        SELECT person_name, amount, mode, direction, is_settled
        FROM social_ledger
        WHERE date >= ? AND date <= ?
        ORDER BY date ASC, id ASC
        """,
        (date_from_text, date_to_text),
    ).fetchall()

    connection.close()

    transaction_list = [dict(transaction) for transaction in transactions]
    daily_trail_list = [dict(balance) for balance in daily_trail]
    social_list = [dict(entry) for entry in social_entries]

    total_credit = sum(
        transaction["amount"]
        for transaction in transaction_list
        if transaction["type"] == "credit"
    )
    total_deposit = sum(
        transaction["amount"]
        for transaction in transaction_list
        if transaction["type"] == "deposit"
    )
    total_debit = sum(
        transaction["amount"]
        for transaction in transaction_list
        if transaction["type"] == "debit"
    )
    cash_spent = sum(
        transaction["amount"]
        for transaction in transaction_list
        if transaction["type"] == "debit" and transaction["mode"] == "cash"
    )
    online_spent = sum(
        transaction["amount"]
        for transaction in transaction_list
        if transaction["type"] == "debit" and transaction["mode"] == "online"
    )

    social_paid_by_me = [
        {
            "person_name": entry["person_name"],
            "amount": entry["amount"],
            "mode": entry["mode"],
            "is_settled": bool(entry["is_settled"]),
        }
        for entry in social_list
        if entry["direction"] == "i_paid"
    ]
    social_paid_for_me = [
        {
            "person_name": entry["person_name"],
            "amount": entry["amount"],
            "mode": entry["mode"],
            "is_settled": bool(entry["is_settled"]),
        }
        for entry in social_list
        if entry["direction"] == "they_paid"
    ]
    unsettled_entries = [
        entry for entry in social_list if not bool(entry["is_settled"])
    ]
    unsettled_total = sum(entry["amount"] for entry in unsettled_entries)
    net = total_credit + total_deposit - total_debit
    accountability_gap = (
        opening_balance + total_credit + total_deposit
    ) - (total_debit + closing_balance)

    return {
        "date_from": date_from_text,
        "date_to": date_to_text,
        "report_type": report_type,
        "opening_balance": opening_balance,
        "closing_balance": closing_balance,
        "total_credit": total_credit,
        "total_deposit": total_deposit,
        "total_debit": total_debit,
        "cash_spent": cash_spent,
        "online_spent": online_spent,
        "social_paid_by_me": social_paid_by_me,
        "social_paid_for_me": social_paid_for_me,
        "unsettled_count": len(unsettled_entries),
        "unsettled_total": unsettled_total,
        "net": net,
        "accountability_gap": accountability_gap,
        "daily_trail": daily_trail_list,
        "transactions": transaction_list,
    }


@app.post(
    "/daily-balance",
    response_model=DailyBalance,
    status_code=status.HTTP_201_CREATED,
)
def create_daily_balance(daily_balance: DailyBalanceCreate):
    connection = get_db_connection()

    existing_daily_balance = connection.execute(
        """
        SELECT id
        FROM daily_balance
        WHERE date = ?
        """,
        (daily_balance.date,),
    ).fetchone()

    if existing_daily_balance is not None:
        update_data = daily_balance.model_dump(
            exclude={"date"},
            exclude_unset=True,
        )

        if update_data:
            assignments = ", ".join(f"{field} = ?" for field in update_data)
            connection.execute(
                f"""
                UPDATE daily_balance
                SET {assignments}
                WHERE id = ?
                """,
                (*update_data.values(), existing_daily_balance["id"]),
            )
            connection.commit()

        daily_balance_id = existing_daily_balance["id"]
    else:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO daily_balance (
                date,
                cash_opening,
                cash_closing,
                online_opening,
                online_closing,
                note
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                daily_balance.date,
                daily_balance.cash_opening,
                daily_balance.cash_closing,
                daily_balance.online_opening,
                daily_balance.online_closing,
                daily_balance.note,
            ),
        )
        connection.commit()
        daily_balance_id = cursor.lastrowid

    saved_daily_balance = connection.execute(
        """
        SELECT
            id,
            date,
            cash_opening,
            cash_closing,
            online_opening,
            online_closing,
            note
        FROM daily_balance
        WHERE id = ?
        """,
        (daily_balance_id,),
    ).fetchone()

    connection.close()
    return dict(saved_daily_balance)


@app.get("/daily-balance", response_model=list[DailyBalance])
def get_daily_balances():
    connection = get_db_connection()

    daily_balances = connection.execute(
        """
        SELECT
            id,
            date,
            cash_opening,
            cash_closing,
            online_opening,
            online_closing,
            note
        FROM daily_balance
        ORDER BY date DESC, id DESC
        """
    ).fetchall()

    connection.close()
    return [dict(daily_balance) for daily_balance in daily_balances]


@app.get("/daily-balance/{daily_balance_id}", response_model=DailyBalance)
def get_daily_balance(daily_balance_id: int):
    connection = get_db_connection()

    daily_balance = connection.execute(
        """
        SELECT
            id,
            date,
            cash_opening,
            cash_closing,
            online_opening,
            online_closing,
            note
        FROM daily_balance
        WHERE id = ?
        """,
        (daily_balance_id,),
    ).fetchone()

    connection.close()

    if daily_balance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Daily balance not found",
        )

    return dict(daily_balance)


@app.post(
    "/social-ledger",
    response_model=list[SocialLedger],
    status_code=status.HTTP_201_CREATED,
)
def create_social_ledger_entry(social_ledger: SocialLedgerCreateWithSplits):
    connection = get_db_connection()
    cursor = connection.cursor()
    created_entries = []
    group_id = str(uuid.uuid4())

    for split in social_ledger.splits:
        person = connection.execute("SELECT name FROM people WHERE id = ?", (split.person_id,)).fetchone()
        if not person:
            raise HTTPException(status_code=400, detail=f"Person with id {split.person_id} not found.")

        cursor.execute(
            """
            INSERT INTO social_ledger (date, amount, direction, person_name, mode, note, category, is_settled, source, group_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                social_ledger.date,
                split.amount,
                social_ledger.direction,
                person["name"],
                social_ledger.mode,
                split.note or social_ledger.note,
                social_ledger.category,
                0,
                "manual",
                group_id,
            ),
        )
        entry_id = cursor.lastrowid
        new_entry = connection.execute(
            """
            SELECT id, date, amount, direction, person_name, mode,
                   COALESCE(note, reason) as note, category, is_settled, settled_at,
                   source, group_id, created_at
            FROM social_ledger
            WHERE id = ?
            """,
            (entry_id,)
        ).fetchone()
        created_entries.append(dict(new_entry))

    connection.commit()
    connection.close()
    return created_entries


@app.get("/social-ledger", response_model=list[SocialLedger])
def get_social_ledger_entries():
    connection = get_db_connection()

    social_ledger_entries = connection.execute(
        """
        SELECT
            id,
            date,
            amount,
            direction,
            person_name,
            mode,
            COALESCE(note, reason) as note,
            category,
            is_settled,
            settled_at,
            source,
            group_id,
            created_at
        FROM social_ledger
        ORDER BY is_settled ASC, date DESC, id DESC
        """
    ).fetchall()

    connection.close()
    return [dict(entry) for entry in social_ledger_entries]


@app.get("/social-ledger/groups", response_model=list[SocialLedgerGroup])
def get_social_ledger_groups():
    connection = get_db_connection()
    entries = connection.execute(
        """
        SELECT
            id, date, amount, direction, person_name, mode, COALESCE(note, reason) as note,
            category, is_settled, settled_at, source, group_id, created_at
        FROM social_ledger
        ORDER BY created_at DESC
        """
    ).fetchall()
    connection.close()

    groups = defaultdict(list)
    for entry in entries:
        # If group_id is null, treat it as a unique group using its own ID as the key
        key = entry["group_id"] if entry["group_id"] else f"single-{entry['id']}"
        groups[key].append(dict(entry))

    response_groups = []
    for group_key, group_entries in groups.items():
        first_entry = group_entries[0]
        total_amount = sum(e["amount"] for e in group_entries)

        group = SocialLedgerGroup(
            group_id=group_key,
            date=first_entry["date"],
            created_at=first_entry["created_at"],
            direction=first_entry["direction"],
            category=first_entry["category"],
            mode=first_entry["mode"],
            note=first_entry["note"],
            total_amount=total_amount,
            entries=[
                SocialLedgerEntry(
                    id=e["id"],
                    person_name=e["person_name"],
                    amount=e["amount"],
                    note=e["note"],
                    is_settled=bool(e["is_settled"]),
                    settled_at=e["settled_at"],
                )
                for e in group_entries
            ],
        )
        response_groups.append(group)

    return response_groups

@app.get("/social-ledger/{social_ledger_id}", response_model=SocialLedger)
def get_social_ledger_entry(social_ledger_id: int):
    connection = get_db_connection()

    social_ledger = connection.execute(
        """
        SELECT
            id,
            date,
            amount,
            direction,
            person_name,
            mode,
            COALESCE(note, reason) as note,
            category,
            is_settled,
            settled_at,
            source,
            group_id,
            created_at
        FROM social_ledger
        WHERE id = ?
        """,
        (social_ledger_id,),
    ).fetchone()

    connection.close()

    if social_ledger is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Social ledger entry not found",
        )

    return dict(social_ledger)


@app.patch("/social-ledger/{social_ledger_id}/settle", response_model=SocialLedger)
def settle_social_ledger_entry(social_ledger_id: int):
    connection = get_db_connection()

    social_ledger = connection.execute(
        """
        SELECT id
        FROM social_ledger
        WHERE id = ?
        """,
        (social_ledger_id,),
    ).fetchone()

    if social_ledger is None:
        connection.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Social ledger entry not found",
        )

    connection.execute(
        """
        UPDATE social_ledger
        SET is_settled = 1,
            settled_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (social_ledger_id,),
    )
    connection.commit()

    settled_social_ledger = connection.execute(
        """
        SELECT
            id,
            date,
            amount,
            direction,
            person_name,
            mode,
            COALESCE(note, reason) as note,
            category,
            is_settled,
            settled_at,
            source,
            group_id,
            created_at
        FROM social_ledger
        WHERE id = ?
        """,
        (social_ledger_id,),
    ).fetchone()

    connection.close()
    return dict(settled_social_ledger)


@app.get("/people", response_model=list[Person])
def get_people():
    connection = get_db_connection()
    people = connection.execute(
        "SELECT id, name, created_at FROM people ORDER BY name ASC"
    ).fetchall()
    connection.close()
    return [dict(person) for person in people]


@app.post("/people", response_model=Person, status_code=status.HTTP_201_CREATED)
def create_person(person: PersonCreate):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO people (name) VALUES (?)", (person.name,)
        )
        person_id = cursor.lastrowid
        connection.commit()
        new_person = connection.execute(
            "SELECT id, name, created_at FROM people WHERE id = ?", (person_id,)
        ).fetchone()
        connection.close()
        return dict(new_person)
    except sqlite3.IntegrityError:
        connection.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Person '{person.name}' already exists.",
        )


@app.delete("/people/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_person(person_id: int):
    connection = get_db_connection()
    # Optional: Check if person is used in social_ledger before deleting
    # For now, just delete
    person = connection.execute("SELECT id FROM people WHERE id = ?", (person_id,)).fetchone()
    if person is None:
        connection.close()
        raise HTTPException(status_code=404, detail="Person not found")

    # Check if person is used in non-settled social ledger entries
    # count = connection.execute("SELECT COUNT(*) FROM social_ledger WHERE person_name = ? AND is_settled = 0", (person['name'],)).fetchone()[0]
    # if count > 0:
    #     raise HTTPException(status_code=400, detail="Cannot delete person with unsettled social ledger entries.")

    connection.execute("DELETE FROM people WHERE id = ?", (person_id,))
    connection.commit()
    connection.close()
    return


@app.get("/categories", response_model=list[Category])
def get_categories():
    connection = get_db_connection()
    categories = connection.execute(
        "SELECT id, name, created_at FROM categories ORDER BY name ASC"
    ).fetchall()
    connection.close()
    return [dict(category) for category in categories]


@app.post("/categories", response_model=Category, status_code=status.HTTP_201_CREATED)
def create_category(category: CategoryCreate):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO categories (name) VALUES (?)", (category.name,)
        )
        category_id = cursor.lastrowid
        connection.commit()
        new_category = connection.execute(
            "SELECT id, name, created_at FROM categories WHERE id = ?", (category_id,)
        ).fetchone()
        connection.close()
        return dict(new_category)
    except sqlite3.IntegrityError:
        connection.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category '{category.name}' already exists.",
        )


@app.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int):
    connection = get_db_connection()
    category = connection.execute(
        "SELECT id, name FROM categories WHERE id = ?", (category_id,)
    ).fetchone()

    if category is None:
        connection.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found."
        )

    if category["name"] in DEFAULT_CATEGORIES:
        connection.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete a default category: {category['name']}.",
        )

    connection.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    connection.commit()
    connection.close()
    return
