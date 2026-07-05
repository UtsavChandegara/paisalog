from typing import Literal, Optional

from pydantic import BaseModel, Field


class TransactionCreate(BaseModel):
    date: str
    amount: float
    type: Literal["debit", "credit", "deposit"]
    category: str
    mode: Literal["cash", "online"] = "cash"
    note: Optional[str] = None
    others_share: float = 0
    others_person: str = ""


class SocialLedgerSplit(BaseModel):
    person_id: int
    amount: float = Field(..., gt=0)
    note: Optional[str] = None


class TransactionWithSplits(BaseModel):
    date: str
    amount: float  # This is my_share
    type: Literal["debit", "credit", "deposit"]
    category: str
    mode: Literal["cash", "online"] = "cash"
    note: Optional[str] = None
    splits: list[SocialLedgerSplit] = []


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
    note: Optional[str] = None
    category: str = "Other"
    is_settled: bool = False
    settled_at: Optional[str] = None
    source: str = "manual"


class SocialLedger(SocialLedgerCreate):
    id: int
    group_id: Optional[str] = None
    created_at: str


class SocialLedgerEntry(BaseModel):
    id: int
    person_name: str
    amount: float
    note: Optional[str] = None
    is_settled: bool
    settled_at: Optional[str] = None


class SocialLedgerGroup(BaseModel):
    group_id: str
    date: str
    created_at: str
    direction: str
    category: str
    mode: str
    note: Optional[str] = None
    total_amount: float
    entries: list[SocialLedgerEntry]


class CategoryCreate(BaseModel):
    name: str


class Category(CategoryCreate):
    id: int
    created_at: str


class PersonCreate(BaseModel):
    name: str


class Person(PersonCreate):
    id: int
    created_at: str


class SocialLedgerCreateWithSplits(BaseModel):
    date: str
    direction: Literal["i_paid", "they_paid"]
    mode: Literal["cash", "online"] = "cash"
    note: Optional[str] = None
    category: str = "Other"
    splits: list[SocialLedgerSplit]
