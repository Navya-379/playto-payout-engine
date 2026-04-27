# Playto Payout Engine Challenge

Minimal payout engine for merchants collecting in USD and withdrawing in INR.

## Stack

- Backend: Django + DRF + PostgreSQL
- Worker: Celery (with Redis broker)
- Frontend: React + Vite + Tailwind

## What is implemented

- Immutable merchant ledger in paise (`BigIntegerField`) with event types: `credit`, `hold`, `release`, `payout_debit`
- Idempotent payout API (`Idempotency-Key` scoped by merchant, payload-hash checked, response replayed)
- Concurrency-safe payout creation using `transaction.atomic()` + `select_for_update()`
- Payout state machine enforcing only legal transitions
- Background payout processing with simulated settlement outcomes (70% success, 20% fail, 10% hang)
- Retry flow for stuck processing payouts (>30s), exponential backoff, max 3 attempts, atomic fund release on fail
- Merchant dashboard endpoint + React UI for balances, payout request, payout history, live polling

## Local setup (Windows-friendly)

### 1) Backend

```bash
cd backend
python -m venv .venv
# activate venv (Windows PowerShell)
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Create `backend/.env` from `backend/.env.example`, then set values.

### 2) Database + Redis

- PostgreSQL should be running on `127.0.0.1:5432`
- Redis should be running on `127.0.0.1:6379`

Create DB once:

```sql
CREATE DATABASE playto;
```

### 3) Migrate and seed

```bash
cd backend
python manage.py migrate
python manage.py seed_data
```

### 4) Run services

Backend API:

```bash
python manage.py runserver
```

Celery worker + beat scheduler:

```bash
celery -A config worker -B -l info
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Optional env:

- `VITE_API_BASE=http://localhost:8000/api/v1`

## API

### Create payout

- `POST /api/v1/payouts`
- Header: `Idempotency-Key: <uuid>`
- Body:

```json
{
  "merchant_id": 1,
  "bank_account_id": 1,
  "amount_paise": 6000
}
```

### Merchant dashboard

- `GET /api/v1/merchants/<merchant_id>/dashboard`

Returns available balance, held balance, recent ledger entries, and payout history.

## Tests

Run:

```bash
python manage.py test apps.payouts.tests -v 2 --keepdb
```

Included:

- idempotency correctness
- concurrency safety (parallel payout requests)
- retry timeout + terminal failure + fund release

## Notes for reviewers

- All money values are stored in paise as integers.
- Balances are computed from ledger aggregation, not float math.
- Locking and ledger hold write occur in the same DB transaction to prevent overdraft.

## Deployment checklist (Railway/Render/Fly)

1. Create services:
   - PostgreSQL
   - Redis
   - Backend web service (`backend`)
   - Worker service (`backend`)
2. Set backend env vars:
   - `DJANGO_SECRET_KEY`
   - `DEBUG=False`
   - `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`
   - `REDIS_URL`
3. Run migrations on deploy:
   - `python manage.py migrate`
4. Seed once:
   - `python manage.py seed_data`
5. Web start command:
   - `python manage.py runserver 0.0.0.0:$PORT`
6. Worker start command:
   - `celery -A config worker -B -l info`
7. Frontend:
   - Set `VITE_API_BASE` to deployed backend URL + `/api/v1`
   - Build and host static frontend

## Submission note (copy-ready)

What I am most proud of:

I focused on correctness over feature volume and built the payout flow around money-safe primitives: immutable ledger events, row-level locking (`select_for_update`) for overdraft prevention, and merchant-scoped idempotency with response replay. I also implemented retry handling for stuck processing payouts with exponential backoff and atomic fund release, then validated it with targeted tests for concurrency, idempotency, and retry behavior.
