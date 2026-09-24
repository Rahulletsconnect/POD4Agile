# Sample Login Application

A minimal login page with a hardcoded test account, for demoing an end-to-end auth flow.

**Test credentials:** username `test`, password `test`.

## Run the backend

```
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8022
```

API docs: http://localhost:8022/docs

## Run the tests

```
cd backend
pip install -r requirements.txt
pytest -v
```

7 tests, covering: successful login, wrong password, wrong username, `/me` with a valid and an
invalid token, logout invalidating the session, and lockout after 5 failed attempts.

## Run the frontend

```
cd frontend
npm install
npm run dev
```

Open http://localhost:5197 — sign in with `test` / `test`. The dev server proxies `/api/*` to
the backend at `localhost:8022`, so start the backend first.

## What's stubbed / needs follow-up

- One hardcoded account — swap for a real user store before production use.
- Passwords are compared in plain text — use a real hash (e.g. bcrypt) in production.
- Sessions are an in-memory dict, not a real session store (Redis, DB, signed JWT, etc.).
