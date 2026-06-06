from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status

from .database import create_tables, get_db_connection
from .models import Transaction, TransactionCreate


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(title="PaisaLog API", lifespan=lifespan)


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
