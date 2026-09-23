"""REQ-1003: Notify all signers by email when an account is closed, and retain proof of each
notification for 7 years for audit.

In-memory FastAPI service. Storage is a plain dict for this first implementation; swap for a
real database before production use (see IMPLEMENTATION_NOTES.md in the repo root).
"""
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field

app = FastAPI(title="Account Closure Notifications")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

RETENTION_YEARS = 7
MAX_RETRIES = 3


class NotificationStatus(str, Enum):
    sent = "sent"
    failed = "failed"
    retrying = "retrying"


class Signer(BaseModel):
    name: str
    email: EmailStr


class Account(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    account_number: str
    signers: list[Signer] = []
    status: str = "open"
    closed_at: str | None = None


class Notification(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    account_id: str
    recipient: EmailStr
    channel: str = "email"
    status: NotificationStatus
    retry_count: int = 0
    sent_at: str


class AuditLogEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    account_id: str
    action: str
    details: str
    recorded_at: str
    retain_until: str


ACCOUNTS: dict[str, Account] = {}
NOTIFICATIONS: dict[str, list[Notification]] = {}
AUDIT_LOG: list[AuditLogEntry] = []


class CreateAccountRequest(BaseModel):
    account_number: str
    signers: list[Signer]


def _mask(account_number: str) -> str:
    return f"****{account_number[-4:]}" if len(account_number) >= 4 else "****"


def _record_audit(account_id: str, action: str, details: str) -> AuditLogEntry:
    now = datetime.now(timezone.utc)
    entry = AuditLogEntry(account_id=account_id, action=action, details=details,
                          recorded_at=now.isoformat(),
                          retain_until=(now + timedelta(days=365 * RETENTION_YEARS)).isoformat())
    AUDIT_LOG.append(entry)
    return entry


def _send_notification(account: Account, signer: Signer, simulate_failure: bool = False) -> Notification:
    """Simulated send with retry. A real implementation swaps this for an SMTP/provider call."""
    status = NotificationStatus.failed if simulate_failure else NotificationStatus.sent
    retries = 0
    while status == NotificationStatus.failed and retries < MAX_RETRIES:
        retries += 1
        status = NotificationStatus.sent  # simulated: succeeds on retry in this stub
    if status == NotificationStatus.failed:
        _record_audit(account.id, "notification_failed",
                      f"Failed to notify {signer.email} after {retries} retries — alert raised for operations")
    notification = Notification(account_id=account.id, recipient=signer.email, status=status,
                                retry_count=retries, sent_at=datetime.now(timezone.utc).isoformat())
    NOTIFICATIONS.setdefault(account.id, []).append(notification)
    return notification


@app.post("/accounts", response_model=Account)
def create_account(req: CreateAccountRequest):
    account = Account(account_number=req.account_number, signers=req.signers)
    ACCOUNTS[account.id] = account
    return account


@app.get("/accounts/{account_id}", response_model=Account)
def get_account(account_id: str):
    account = ACCOUNTS.get(account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    return account


@app.post("/accounts/{account_id}/close", response_model=Account)
def close_account(account_id: str):
    account = ACCOUNTS.get(account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    if account.status == "closed":
        raise HTTPException(409, "Account is already closed")
    if not account.signers:
        raise HTTPException(422, "Account has no signers to notify")

    account.status = "closed"
    account.closed_at = datetime.now(timezone.utc).isoformat()
    _record_audit(account.id, "account_closed",
                 f"Account {_mask(account.account_number)} closed at {account.closed_at}")

    for signer in account.signers:
        notification = _send_notification(account, signer)
        _record_audit(account.id, "notification_sent",
                      f"Notified {signer.email} via email — status: {notification.status}, "
                      f"account {_mask(account.account_number)}, retained {RETENTION_YEARS} years for audit")

    return account


@app.get("/accounts/{account_id}/notifications", response_model=list[Notification])
def list_notifications(account_id: str):
    if account_id not in ACCOUNTS:
        raise HTTPException(404, "Account not found")
    return NOTIFICATIONS.get(account_id, [])


@app.get("/audit-log", response_model=list[AuditLogEntry])
def audit_log(account_id: str | None = None):
    if account_id:
        return [e for e in AUDIT_LOG if e.account_id == account_id]
    return AUDIT_LOG
