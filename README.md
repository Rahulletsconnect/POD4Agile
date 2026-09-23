# REQ-1003 — Account Closure Notifications

Notifies every signer by email when an account is closed, and keeps a 7-year audit trail
(masked account number, per-signer delivery status, retry count).

## Run the backend

```
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8020
```

API docs: http://localhost:8020/docs

## Run the tests

```
cd backend
pip install -r requirements.txt
pytest -v
```

6 tests, covering: creating an account, notifying every signer on close, the masked audit
trail, refusing to close an already-closed account, refusing to close an account with no
signers, and 404s on an unknown account.

## Run the frontend

```
cd frontend
npm install
npm run dev
```

Open http://localhost:5190 — create an account with one or more signers, close it, and
watch the notification + audit log sections populate. The dev server proxies `/api/*` to
the backend at `localhost:8020`, so start the backend first.

## What's stubbed / needs follow-up

- Storage is in-memory (a plain dict) — swap for a real database before production use.
- Email/SMS sending is simulated (`_send_notification` in `backend/main.py`), not wired to
  an actual provider.
- No auth on the API yet.
