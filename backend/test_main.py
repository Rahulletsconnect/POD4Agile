from datetime import date

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _beneficiary():
    r = client.post("/beneficiaries", json={"name": "Landlord Co", "account_number": "9876543210"})
    assert r.status_code == 200
    return r.json()


def _schedule(**overrides):
    b = _beneficiary()
    body = {"beneficiary_id": b["id"], "amount": 500, "frequency": "monthly",
           "start_date": "2026-01-01", "end_date": None, "two_factor_confirmed": False}
    body.update(overrides)
    r = client.post("/schedules", json=body)
    return r


def test_create_beneficiary():
    b = _beneficiary()
    assert b["name"] == "Landlord Co"


def test_create_monthly_schedule_sets_first_reminder_24h_before():
    r = _schedule()
    assert r.status_code == 200
    s = r.json()
    assert s["status"] == "active"
    assert s["next_payment_date"] == "2026-01-01"
    assert s["next_reminder_at"].startswith("2025-12-31T00:00:00")


def test_large_payment_requires_two_factor_confirmation():
    r = _schedule(amount=15000, two_factor_confirmed=False)
    assert r.status_code == 422
    r2 = _schedule(amount=15000, two_factor_confirmed=True)
    assert r2.status_code == 200


def test_unknown_beneficiary_rejected():
    r = client.post("/schedules", json={"beneficiary_id": "nope", "amount": 100,
                                        "frequency": "weekly", "start_date": "2026-01-01"})
    assert r.status_code == 404


def test_successful_payment_advances_to_next_period_monthly():
    schedule = _schedule().json()
    r = client.post(f"/schedules/{schedule['id']}/process-due-payment", params={"sufficient_funds": True})
    assert r.status_code == 200
    assert r.json()["status"] == "paid"

    updated = client.get(f"/schedules/{schedule['id']}").json()
    assert updated["next_payment_date"] == "2026-02-01"
    assert updated["next_reminder_at"].startswith("2026-01-31")


def test_insufficient_funds_skips_and_retries_next_day():
    schedule = _schedule().json()
    r = client.post(f"/schedules/{schedule['id']}/process-due-payment", params={"sufficient_funds": False})
    assert r.json()["status"] == "skipped_insufficient_funds"

    updated = client.get(f"/schedules/{schedule['id']}").json()
    assert updated["next_payment_date"] == "2026-01-02"  # retried the next day, not skipped to Feb

    audit = client.get(f"/schedules/{schedule['id']}/audit-log").json()
    assert any(e["action"] == "payment_skipped" for e in audit)


def test_schedule_completes_when_final_payment_passes_end_date():
    schedule = _schedule(frequency="monthly", start_date="2026-01-01", end_date="2026-01-15").json()
    r = client.post(f"/schedules/{schedule['id']}/process-due-payment", params={"sufficient_funds": True})
    assert r.json()["status"] == "paid"
    updated = client.get(f"/schedules/{schedule['id']}").json()
    assert updated["status"] == "cancelled"  # no further monthly payment fits before end_date


def test_pause_resume_and_cancel():
    schedule = _schedule().json()
    sid = schedule["id"]

    assert client.post(f"/schedules/{sid}/pause").json()["status"] == "paused"
    r = client.post(f"/schedules/{sid}/process-due-payment")
    assert r.status_code == 409  # can't process a paused schedule

    assert client.post(f"/schedules/{sid}/resume").json()["status"] == "active"
    assert client.post(f"/schedules/{sid}/cancel").json()["status"] == "cancelled"
    assert client.post(f"/schedules/{sid}/pause").status_code == 409  # can't pause a cancelled one


def test_end_date_before_start_date_rejected():
    r = _schedule(start_date="2026-05-01", end_date="2026-01-01")
    assert r.status_code == 422
