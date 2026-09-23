# REQ-1005 — Recurring Payments

Lets a customer schedule a recurring payment to a saved beneficiary (weekly/monthly/
quarterly), with a reminder 24 hours before each payment, a 2FA gate above 10,000, and
skip-and-retry-next-day handling on insufficient funds.

## Run the backend

```
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8021
```

API docs: http://localhost:8021/docs

## Run the tests

```
cd backend
pip install -r requirements.txt
pytest -v
```

9 tests, covering: schedule creation and its 24h-before reminder time, the >10,000
second-factor gate, an unknown beneficiary being rejected, a successful payment advancing
to the next period, insufficient funds skipping and retrying the next day, a schedule
auto-completing once its final payment passes `end_date`, pause/resume/cancel, and
`end_date` before `start_date` being rejected.

## Run the frontend

```
cd frontend
npm install
npm run dev
```

Open http://localhost:5195 — add a beneficiary, create a schedule, then use "Simulate
payment" / "Simulate insufficient funds" on a row to see the schedule advance and the
audit log fill in. The dev server proxies `/api/*` to the backend at `localhost:8021`, so
start the backend first.

## What's stubbed / needs follow-up

- Storage is in-memory (a plain dict) — swap for a real database before production use.
- `process-due-payment` is triggered manually here; production wires it to a daily
  scheduler/cron instead.
- Balance checks and 2FA are simulated inputs, not wired to a real ledger or auth provider.
