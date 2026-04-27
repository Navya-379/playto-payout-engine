# EXPLAINER.md

## 1. The Ledger

Balance calculation lives in `apps/payouts/services.py`.

```python
def get_balances(merchant_id: int) -> dict[str, int]:
    credits = _sum_entries(merchant_id, LedgerEntry.EntryType.CREDIT)
    holds = _sum_entries(merchant_id, LedgerEntry.EntryType.HOLD)
    releases = _sum_entries(merchant_id, LedgerEntry.EntryType.RELEASE)
    payout_debits = _sum_entries(merchant_id, LedgerEntry.EntryType.PAYOUT_DEBIT)
    available = credits - holds + releases
    held = holds - releases - payout_debits
    return {"available_paise": max(available, 0), "held_paise": max(held, 0)}
```

I modeled credits/debits as immutable ledger rows (`credit`, `hold`, `release`, `payout_debit`) so the balance can always be recomputed from source of truth and audited.
This avoids mutable balance drift and makes every state change traceable.

## 2. The Lock

Overdraft prevention code:

```python
with transaction.atomic():
    merchant = Merchant.objects.select_for_update().get(id=merchant_id)
    balances = get_balances(merchant.id)
    if balances["available_paise"] < amount_paise:
        raise ValidationError("Insufficient available balance")
    payout = Payout.objects.create(...)
    LedgerEntry.objects.create(... entry_type=LedgerEntry.EntryType.HOLD ...)
```

This relies on PostgreSQL row-level lock (`SELECT ... FOR UPDATE`) to serialize concurrent requests for one merchant.
Because both "check available" and "write hold" happen inside the same transaction, two parallel requests cannot both reserve the same funds.

## 3. The Idempotency

Idempotency is persisted in `IdempotencyKey` with unique constraint on `(merchant, key)`.  
On each request:
1. create/find idempotency row
2. validate request hash matches prior payload
3. if response already stored, return exact stored response
4. otherwise process and persist response payload + status code

If the first request is in-flight and the second arrives, both converge on the same row. The second call receives the stored response once the first transaction writes it.
If the key is reused with a different payload hash, request is rejected.

## 4. The State Machine

Transition gate:

```python
allowed = {
    Payout.Status.PENDING: {Payout.Status.PROCESSING},
    Payout.Status.PROCESSING: {Payout.Status.COMPLETED, Payout.Status.FAILED},
}
if to_status not in allowed.get(payout.status, set()):
    raise ValidationError(f"Illegal status transition {payout.status} -> {to_status}")
```

This blocks illegal transitions such as `failed -> completed` and backwards moves.
A failed payout release ledger entry is written atomically with the status update.

## 5. Retry Logic

Retry flow is implemented in `retry_stuck_payouts()`:

- Select payouts in `processing` for more than 30 seconds
- Attempt settlement again (same outcome simulation)
- If still unresolved, increment attempts and schedule next retry with exponential backoff
- Max attempts = 3, then mark `failed` and write `release` entry in same transaction

This protects merchant funds by guaranteeing unresolved holds eventually become terminal and auditable.

## 6. The AI Audit

AI initially suggested non-transactional balance checking:

```python
balance = get_balance(merchant_id)
if balance >= amount:
    Payout.objects.create(...)
```

This is race-prone because two concurrent requests can both pass the check and overdraft.  
I replaced it with transactional locking (`select_for_update`) and hold-ledger write in the same transaction.
