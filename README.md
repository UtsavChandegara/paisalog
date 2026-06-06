# PaisaLog

PaisaLog is a personal finance tracker built with FastAPI, SQLite, and vanilla HTML/CSS/JS for recording transactions, daily balances, shared expenses, and short-term statements.

## Features

- Add and view personal transactions with date, amount, type, category, and notes.
- Track transaction types including debit, credit, and deposit.
- Generate 7-day, 15-day, and 30-day financial statements.
- View statement summaries with total debit, total credit, total deposit, and net balance.
- Record daily opening and closing balances.
- Maintain a social ledger for shared expenses or money owed between people.
- Mark social ledger entries as settled.
- Store data locally using SQLite.
- Use a simple browser-based frontend built with plain HTML, CSS, and JavaScript.
- Access interactive API documentation through FastAPI.

## Tech Stack

- **Backend:** FastAPI
- **Database:** SQLite
- **Validation:** Pydantic
- **Frontend:** HTML, CSS, JavaScript
- **Server:** Uvicorn

## Project Structure

```text
paisalog/
├── backend/
│   ├── database.py
│   ├── main.py
│   └── models.py
├── frontend/
│   ├── app.js
│   ├── index.html
│   └── style.css
├── .gitignore
└── README.md
```

## How to Run Locally

1. Clone the repository and move into the project directory:

```bash
git clone <repository-url>
cd paisalog
```

2. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows, activate it with:

```bash
.venv\Scripts\activate
```

3. Install the backend dependencies:

```bash
pip install fastapi uvicorn
```

4. Start the FastAPI server:

```bash
uvicorn backend.main:app --reload
```

5. Open the API documentation in your browser:

```text
http://127.0.0.1:8000/docs
```

6. Open the frontend:

```bash
cd frontend
python3 -m http.server 5500
```

Then visit:

```text
http://127.0.0.1:5500
```

The SQLite database file is created automatically at `backend/paisalog.db` when the backend starts.

## API Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/transactions` | Create a new transaction. |
| `GET` | `/transactions` | Get all transactions. |
| `GET` | `/transactions/{transaction_id}` | Get a single transaction by ID. |
| `GET` | `/statement?range={range}` | Get a statement for the selected range: 7, 15, or 30 days. |
| `POST` | `/daily-balance` | Create a daily balance record. |
| `GET` | `/daily-balance` | Get all daily balance records. |
| `GET` | `/daily-balance/{daily_balance_id}` | Get a single daily balance record by ID. |
| `POST` | `/social-ledger` | Create a social ledger entry. |
| `GET` | `/social-ledger` | Get all social ledger entries. |
| `GET` | `/social-ledger/{social_ledger_id}` | Get a single social ledger entry by ID. |
| `PATCH` | `/social-ledger/{social_ledger_id}/settle` | Mark a social ledger entry as settled. |

## Screenshots

Screenshots will be added here.

- Transaction tracker screen
- Daily balance screen
- Social ledger screen
- Statement summary screen
