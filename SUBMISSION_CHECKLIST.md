# Playto Submission Checklist

## Required artifacts

- [x] Backend code (Django + DRF + PostgreSQL + Celery)
- [x] Frontend dashboard (React + Tailwind)
- [x] `README.md` setup instructions
- [x] `EXPLAINER.md` with required 6 answers
- [x] Seed command (`python manage.py seed_data`)
- [x] Tests:
  - [x] Concurrency test
  - [x] Idempotency test
  - [x] Retry timeout/fund release test

## Verification commands run

```bash
python manage.py migrate
python manage.py seed_data
python manage.py test apps.payouts.tests -v 2 --keepdb
```

## What to submit in the form

1. GitHub repo URL
2. Hosted deployment URL
3. Short note on what you are most proud of (ready in `README.md`)

## Final manual checks before submit

- [ ] Backend URL is reachable
- [ ] Frontend can request payout and show status updates
- [ ] Celery worker + beat are running in deployment
- [ ] Seed merchants visible in dashboard
- [ ] `EXPLAINER.md` reflects current code
