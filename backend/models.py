from typing import Literal, Optional

from pydantic import BaseModel


class TransactionCreate(BaseModel):
    date: str
    amount: float
    type: Literal["debit", "credit", "deposit"]
    category: str
    note: Optional[str] = None


class Transaction(TransactionCreate):
    id: int
    created_at: str


class DailyBalanceCreate(BaseModel):
    date: str
    opening_balance: float
    closing_balance: float
    note: Optional[str] = None


class DailyBalance(DailyBalanceCreate):
    id: int


class SocialLedgerCreate(BaseModel):
    date: str
    amount: float
    direction: Literal["i_paid", "they_paid"]
    person_name: str
    reason: Optional[str] = None
    is_settled: bool = False
    settled_at: Optional[str] = None


class SocialLedger(SocialLedgerCreate):
    id: int
