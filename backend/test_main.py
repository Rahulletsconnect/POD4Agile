from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _create_account(signers=None):
    if signers is None:
        signers = [{"name": "Alice Signer", "email": "alice@example.com"},
                  {"name": "Bob Signer", "email": "bob@example.com"}]
    r = client.post("/accounts", json={"account_number": "1234567890", "signers": signers})
    assert r.status_code == 200
    return r.json()


def test_create_account():
    account = _create_account()
    assert account["status"] == "open"
    assert len(account["signers"]) == 2


def test_closing_account_notifies_all_signers():
    account = _create_account()
    r = client.post(f"/accounts/{account['id']}/close")
    assert r.status_code == 200
    assert r.json()["status"] == "closed"

    notifications = client.get(f"/accounts/{account['id']}/notifications").json()
    assert len(notifications) == 2
    assert {n["recipient"] for n in notifications} == {"alice@example.com", "bob@example.com"}
    assert all(n["status"] == "sent" for n in notifications)


def test_closing_account_writes_audit_trail_with_masked_account_number():
    account = _create_account()
    client.post(f"/accounts/{account['id']}/close")

    entries = client.get("/audit-log", params={"account_id": account["id"]}).json()
    assert any(e["action"] == "account_closed" for e in entries)
    assert sum(1 for e in entries if e["action"] == "notification_sent") == 2
    for e in entries:
        assert "1234567890" not in e["details"]  # full account number must never appear
        assert "****7890" in e["details"] or e["action"] != "account_closed"


def test_cannot_close_account_twice():
    account = _create_account()
    client.post(f"/accounts/{account['id']}/close")
    r = client.post(f"/accounts/{account['id']}/close")
    assert r.status_code == 409


def test_cannot_close_account_with_no_signers():
    account = _create_account(signers=[])
    r = client.post(f"/accounts/{account['id']}/close")
    assert r.status_code == 422


def test_unknown_account_returns_404():
    assert client.get("/accounts/does-not-exist").status_code == 404
    assert client.post("/accounts/does-not-exist/close").status_code == 404
