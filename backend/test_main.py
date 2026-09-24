from fastapi.testclient import TestClient

from main import FAILED_ATTEMPTS, SESSIONS, app

client = TestClient(app)


def setup_function():
    SESSIONS.clear()
    FAILED_ATTEMPTS.clear()


def test_login_with_correct_credentials():
    r = client.post("/login", json={"username": "test", "password": "test"})
    assert r.status_code == 200
    data = r.json()
    assert data["username"] == "test"
    assert data["token"]


def test_login_with_wrong_password_rejected():
    r = client.post("/login", json={"username": "test", "password": "wrong"})
    assert r.status_code == 401


def test_login_with_wrong_username_rejected():
    r = client.post("/login", json={"username": "nope", "password": "test"})
    assert r.status_code == 401


def test_me_returns_session_for_valid_token():
    token = client.post("/login", json={"username": "test", "password": "test"}).json()["token"]
    r = client.get("/me", params={"token": token})
    assert r.status_code == 200
    assert r.json()["username"] == "test"


def test_me_rejects_unknown_token():
    r = client.get("/me", params={"token": "not-a-real-token"})
    assert r.status_code == 401


def test_logout_invalidates_session():
    token = client.post("/login", json={"username": "test", "password": "test"}).json()["token"]
    assert client.post("/logout", params={"token": token}).json()["ok"] is True
    assert client.get("/me", params={"token": token}).status_code == 401


def test_too_many_failed_attempts_locks_out():
    for _ in range(5):
        client.post("/login", json={"username": "lockout-user", "password": "wrong"})
    r = client.post("/login", json={"username": "lockout-user", "password": "wrong"})
    assert r.status_code == 429


def test_account_requires_login():
    assert client.get("/account", params={"token": "nope"}).status_code == 401


def test_account_returns_balance_when_logged_in():
    token = client.post("/login", json={"username": "test", "password": "test"}).json()["token"]
    r = client.get("/account", params={"token": token})
    assert r.status_code == 200
    assert r.json()["balance"] > 0


def test_transactions_requires_login():
    assert client.get("/transactions", params={"token": "nope"}).status_code == 401


def test_transactions_returns_list_when_logged_in():
    token = client.post("/login", json={"username": "test", "password": "test"}).json()["token"]
    r = client.get("/transactions", params={"token": token})
    assert r.status_code == 200
    assert len(r.json()) > 0
    assert "description" in r.json()[0]
