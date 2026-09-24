"""Sample login page backend, landing on a simple banking home page after login.

Username: test   Password: test

In-memory session store and static sample account data. Storage and auth here are
deliberately minimal — swap for real password hashing (e.g. bcrypt), a real user store,
and a real ledger before production use (see README.md in the repo root).
"""
import secrets
from datetime import date, datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Sample Login Application")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

TEST_USERNAME = "test"
TEST_PASSWORD = "test"
MAX_ATTEMPTS = 5

SESSIONS: dict[str, dict] = {}
FAILED_ATTEMPTS: dict[str, int] = {}

SAMPLE_ACCOUNT = {"account_number": "****4821", "currency": "USD", "balance": 12450.75}
SAMPLE_TRANSACTIONS = [
    {"id": 1, "date": str(date(2026, 9, 18)), "description": "Salary deposit", "amount": 4200.00},
    {"id": 2, "date": str(date(2026, 9, 19)), "description": "Grocery Mart", "amount": -86.40},
    {"id": 3, "date": str(date(2026, 9, 20)), "description": "Electric Co. bill payment", "amount": -142.10},
    {"id": 4, "date": str(date(2026, 9, 21)), "description": "Transfer to J. Smith", "amount": -300.00},
    {"id": 5, "date": str(date(2026, 9, 22)), "description": "Coffee Shop", "amount": -6.75},
]


def _require_session(token: str) -> dict:
    session = SESSIONS.get(token)
    if not session:
        raise HTTPException(401, "Not logged in")
    return session


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str
    logged_in_at: str


@app.post("/login", response_model=LoginResponse)
def login(req: LoginRequest):
    attempts = FAILED_ATTEMPTS.get(req.username, 0)
    if attempts >= MAX_ATTEMPTS:
        raise HTTPException(429, "Too many failed attempts. Try again later.")

    if req.username != TEST_USERNAME or req.password != TEST_PASSWORD:
        FAILED_ATTEMPTS[req.username] = attempts + 1
        raise HTTPException(401, "Invalid username or password")

    FAILED_ATTEMPTS.pop(req.username, None)
    token = secrets.token_urlsafe(24)
    session = {"username": req.username, "logged_in_at": datetime.now(timezone.utc).isoformat()}
    SESSIONS[token] = session
    return LoginResponse(token=token, **session)


@app.get("/me")
def me(token: str):
    return _require_session(token)


@app.post("/logout")
def logout(token: str):
    SESSIONS.pop(token, None)
    return {"ok": True}


@app.get("/account")
def account(token: str):
    _require_session(token)
    return SAMPLE_ACCOUNT


@app.get("/transactions")
def transactions(token: str):
    _require_session(token)
    return SAMPLE_TRANSACTIONS
