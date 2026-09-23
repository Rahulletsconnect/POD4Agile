"""REQ-1005: Allow a customer to schedule a recurring payment to a saved beneficiary, with a
reminder sent 24 hours before each payment.

In-memory FastAPI service. Storage is a plain dict for this first implementation; swap for a
real database before production use (see IMPLEMENTATION_NOTES.md in the repo root).
"""
import uuid
from datetime import date, datetime, timedelta, timezone
from enum import Enum

from dateutil.relativedelta import relativedelta
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

app = FastAPI(title="Recurring Payments")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

REMINDER_HOURS_BEFORE = 24
TWO_FACTOR_THRESHOLD = 10_000
MAX_RETRY_DAYS = 1


class Frequency(str, Enum):
    weekly = "weekly"
    monthly = "monthly"
    quarterly = "quarterly"


class ScheduleStatus(str, Enum):
    active = "active"
    paused = "paused"
    cancelled = "cancelled"


class Beneficiary(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    account_number: str


class CreateBeneficiaryRequest(BaseModel):
    name: str
    account_number: str


class CreateScheduleRequest(BaseModel):
    beneficiary_id: str
    amount: float
    frequency: Frequency
    start_date: date
    end_date: date | None = None
    two_factor_confirmed: bool = False

    @field_validator("amount")
    @classmethod
    def positive_amount(cls, v):
        if v <= 0:
            raise ValueError("amount must be positive")
        return v


class Schedule(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    beneficiary_id: str
    amount: float
    frequency: Frequency
    start_date: date
    end_date: date | None
    status: ScheduleStatus = ScheduleStatus.active
    next_payment_date: date
    next_reminder_at: str


class AuditLogEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    schedule_id: str
    action: str
    details: str
    recorded_at: str


class PaymentAttempt(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    schedule_id: str
    scheduled_for: date
    status: str  # "paid" | "skipped_insufficient_funds" | "retried"
    attempted_at: str


BENEFICIARIES: dict[str, Beneficiary] = {}
SCHEDULES: dict[str, Schedule] = {}
AUDIT_LOG: list[AuditLogEntry] = []
PAYMENT_ATTEMPTS: list[PaymentAttempt] = []


def _advance(d: date, frequency: Frequency) -> date:
    if frequency == Frequency.weekly:
        return d + timedelta(weeks=1)
    if frequency == Frequency.monthly:
        return d + relativedelta(months=1)
    return d + relativedelta(months=3)  # quarterly


def _reminder_for(payment_date: date) -> str:
    dt = datetime.combine(payment_date, datetime.min.time(), tzinfo=timezone.utc)
    return (dt - timedelta(hours=REMINDER_HOURS_BEFORE)).isoformat()


def _record_audit(schedule_id: str, action: str, details: str) -> None:
    AUDIT_LOG.append(AuditLogEntry(schedule_id=schedule_id, action=action, details=details,
                                   recorded_at=datetime.now(timezone.utc).isoformat()))


@app.post("/beneficiaries", response_model=Beneficiary)
def create_beneficiary(req: CreateBeneficiaryRequest):
    b = Beneficiary(name=req.name, account_number=req.account_number)
    BENEFICIARIES[b.id] = b
    return b


@app.get("/beneficiaries", response_model=list[Beneficiary])
def list_beneficiaries():
    return list(BENEFICIARIES.values())


@app.post("/schedules", response_model=Schedule)
def create_schedule(req: CreateScheduleRequest):
    if req.beneficiary_id not in BENEFICIARIES:
        raise HTTPException(404, "Beneficiary not found")
    if req.end_date and req.end_date < req.start_date:
        raise HTTPException(422, "end_date must be on or after start_date")
    if req.amount > TWO_FACTOR_THRESHOLD and not req.two_factor_confirmed:
        raise HTTPException(422, f"Payments above {TWO_FACTOR_THRESHOLD} require second-factor "
                               "confirmation at setup (two_factor_confirmed=true)")

    schedule = Schedule(beneficiary_id=req.beneficiary_id, amount=req.amount, frequency=req.frequency,
                        start_date=req.start_date, end_date=req.end_date,
                        next_payment_date=req.start_date, next_reminder_at=_reminder_for(req.start_date))
    SCHEDULES[schedule.id] = schedule
    _record_audit(schedule.id, "schedule_created",
                 f"{req.frequency.value} payment of {req.amount} to beneficiary {req.beneficiary_id} "
                 f"starting {req.start_date}")
    return schedule


@app.get("/schedules", response_model=list[Schedule])
def list_schedules():
    return list(SCHEDULES.values())


@app.get("/schedules/{schedule_id}", response_model=Schedule)
def get_schedule(schedule_id: str):
    schedule = SCHEDULES.get(schedule_id)
    if not schedule:
        raise HTTPException(404, "Schedule not found")
    return schedule


@app.post("/schedules/{schedule_id}/pause", response_model=Schedule)
def pause_schedule(schedule_id: str):
    schedule = SCHEDULES.get(schedule_id)
    if not schedule:
        raise HTTPException(404, "Schedule not found")
    if schedule.status == ScheduleStatus.cancelled:
        raise HTTPException(409, "Cannot pause a cancelled schedule")
    schedule.status = ScheduleStatus.paused
    _record_audit(schedule_id, "schedule_paused", "Customer paused the recurring payment")
    return schedule


@app.post("/schedules/{schedule_id}/resume", response_model=Schedule)
def resume_schedule(schedule_id: str):
    schedule = SCHEDULES.get(schedule_id)
    if not schedule:
        raise HTTPException(404, "Schedule not found")
    if schedule.status != ScheduleStatus.paused:
        raise HTTPException(409, "Only a paused schedule can be resumed")
    schedule.status = ScheduleStatus.active
    _record_audit(schedule_id, "schedule_resumed", "Customer resumed the recurring payment")
    return schedule


@app.post("/schedules/{schedule_id}/cancel", response_model=Schedule)
def cancel_schedule(schedule_id: str):
    schedule = SCHEDULES.get(schedule_id)
    if not schedule:
        raise HTTPException(404, "Schedule not found")
    schedule.status = ScheduleStatus.cancelled
    _record_audit(schedule_id, "schedule_cancelled", "Customer cancelled the recurring payment")
    return schedule


@app.post("/schedules/{schedule_id}/process-due-payment", response_model=PaymentAttempt)
def process_due_payment(schedule_id: str, sufficient_funds: bool = True):
    """Simulates the scheduler's daily tick for one schedule: attempts the payment due today,
    skips and retries the next day on insufficient funds, and advances next_payment_date/reminder.
    A real deployment calls this from a cron job / task queue instead of a manual trigger.
    """
    schedule = SCHEDULES.get(schedule_id)
    if not schedule:
        raise HTTPException(404, "Schedule not found")
    if schedule.status != ScheduleStatus.active:
        raise HTTPException(409, f"Schedule is {schedule.status.value}, not active")

    today = schedule.next_payment_date
    if not sufficient_funds:
        attempt = PaymentAttempt(schedule_id=schedule_id, scheduled_for=today,
                                 status="skipped_insufficient_funds", attempted_at=datetime.now(timezone.utc).isoformat())
        schedule.next_payment_date = today + timedelta(days=MAX_RETRY_DAYS)
        schedule.next_reminder_at = _reminder_for(schedule.next_payment_date)
        _record_audit(schedule_id, "payment_skipped",
                     f"Insufficient funds for payment due {today}; customer notified, retrying {schedule.next_payment_date}")
    else:
        attempt = PaymentAttempt(schedule_id=schedule_id, scheduled_for=today, status="paid",
                                 attempted_at=datetime.now(timezone.utc).isoformat())
        if schedule.end_date and _advance(today, schedule.frequency) > schedule.end_date:
            schedule.status = ScheduleStatus.cancelled
            _record_audit(schedule_id, "schedule_completed", f"Final payment made on {today}; schedule ended")
        else:
            schedule.next_payment_date = _advance(today, schedule.frequency)
            schedule.next_reminder_at = _reminder_for(schedule.next_payment_date)
        _record_audit(schedule_id, "payment_made", f"Payment of {schedule.amount} made on {today}")

    PAYMENT_ATTEMPTS.append(attempt)
    return attempt


@app.get("/schedules/{schedule_id}/audit-log", response_model=list[AuditLogEntry])
def schedule_audit_log(schedule_id: str):
    if schedule_id not in SCHEDULES:
        raise HTTPException(404, "Schedule not found")
    return [e for e in AUDIT_LOG if e.schedule_id == schedule_id]


@app.get("/schedules/{schedule_id}/payments", response_model=list[PaymentAttempt])
def schedule_payments(schedule_id: str):
    if schedule_id not in SCHEDULES:
        raise HTTPException(404, "Schedule not found")
    return [p for p in PAYMENT_ATTEMPTS if p.schedule_id == schedule_id]
