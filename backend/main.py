from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status

from .database import create_tables, get_db_connection
from .models import (
    DailyBalance,
    DailyBalanceCreate,
    SocialLedger,
    SocialLedgerCreate,
    Transaction,
    TransactionCreate,
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
        INSERT INTO transactions (date, amount, type, category, note)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            transaction.date,
            transaction.amount,
            transaction.type,
            transaction.category,
            transaction.note,
        ),
    )
    connection.commit()

    transaction_id = cursor.lastrowid
    saved_transaction = connection.execute(
        """
        SELECT id, date, amount, type, category, note, created_at
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
        SELECT id, date, amount, type, category, note, created_at
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
        SELECT id, date, amount, type, category, note, created_at
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
        connection.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Daily balance already exists for this date",
        )

    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO daily_balance (date, opening_balance, closing_balance, note)
        VALUES (?, ?, ?, ?)
        """,
        (
            daily_balance.date,
            daily_balance.opening_balance,
            daily_balance.closing_balance,
            daily_balance.note,
        ),
    )
    connection.commit()

    daily_balance_id = cursor.lastrowid
    saved_daily_balance = connection.execute(
        """
        SELECT id, date, opening_balance, closing_balance, note
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
        SELECT id, date, opening_balance, closing_balance, note
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
        SELECT id, date, opening_balance, closing_balance, note
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
    response_model=SocialLedger,
    status_code=status.HTTP_201_CREATED,
)
def create_social_ledger_entry(social_ledger: SocialLedgerCreate):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO social_ledger (
            date,
            amount,
            direction,
            person_name,
            reason,
            is_settled,
            settled_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            social_ledger.date,
            social_ledger.amount,
            social_ledger.direction,
            social_ledger.person_name,
            social_ledger.reason,
            int(social_ledger.is_settled),
            social_ledger.settled_at,
        ),
    )
    connection.commit()

    social_ledger_id = cursor.lastrowid
    saved_social_ledger = connection.execute(
        """
        SELECT id, date, amount, direction, person_name, reason, is_settled, settled_at
        FROM social_ledger
        WHERE id = ?
        """,
        (social_ledger_id,),
    ).fetchone()

    connection.close()
    return dict(saved_social_ledger)


@app.get("/social-ledger", response_model=list[SocialLedger])
def get_social_ledger_entries():
    connection = get_db_connection()

    social_ledger_entries = connection.execute(
        """
        SELECT id, date, amount, direction, person_name, reason, is_settled, settled_at
        FROM social_ledger
        ORDER BY is_settled ASC, date DESC, id DESC
        """
    ).fetchall()

    connection.close()
    return [dict(entry) for entry in social_ledger_entries]


@app.get("/social-ledger/{social_ledger_id}", response_model=SocialLedger)
def get_social_ledger_entry(social_ledger_id: int):
    connection = get_db_connection()

    social_ledger = connection.execute(
        """
        SELECT id, date, amount, direction, person_name, reason, is_settled, settled_at
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
        SELECT id, date, amount, direction, person_name, reason, is_settled, settled_at
        FROM social_ledger
        WHERE id = ?
        """,
        (social_ledger_id,),
    ).fetchone()

    connection.close()
    return dict(settled_social_ledger)
