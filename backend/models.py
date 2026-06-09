from typing import Literal, Optional

from pydantic import BaseModel


class TransactionCreate(BaseModel):
    date: str
    amount: float
    type: Literal["debit", "credit", "deposit"]
    category: str
    mode: Literal["cash", "online"] = "cash"
    note: Optional[str] = None
    others_share: float = 0
    others_person: str = ""


class Transaction(TransactionCreate):
    id: int
    created_at: str


class DailyBalanceCreate(BaseModel):
    date: str
    cash_opening: Optional[float] = None
    cash_closing: Optional[float] = None
    online_opening: Optional[float] = None
    online_closing: Optional[float] = None
    note: Optional[str] = None


class DailyBalance(DailyBalanceCreate):
    id: int


class SocialLedgerCreate(BaseModel):
    date: str
    amount: float
    direction: Literal["i_paid", "they_paid"]
    person_name: str
    mode: Literal["cash", "online"] = "cash"
    reason: Optional[str] = None
    is_settled: bool = False
    settled_at: Optional[str] = None


class SocialLedger(SocialLedgerCreate):
    id: int
