import hashlib
import json
import random
from datetime import timedelta
from typing import Any

from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError

from .models import IdempotencyKey, LedgerEntry, Merchant, Payout


def _hash_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _sum_entries(merchant_id: int, entry_type: str) -> int:
    return (
        LedgerEntry.objects.filter(merchant_id=merchant_id, entry_type=entry_type)
        .aggregate(total=Coalesce(Sum("amount_paise"), 0))
        .get("total", 0)
    )


def get_balances(merchant_id: int) -> dict[str, int]:
    credits = _sum_entries(merchant_id, LedgerEntry.EntryType.CREDIT)
    holds = _sum_entries(merchant_id, LedgerEntry.EntryType.HOLD)
    releases = _sum_entries(merchant_id, LedgerEntry.EntryType.RELEASE)
    payout_debits = _sum_entries(merchant_id, LedgerEntry.EntryType.PAYOUT_DEBIT)
    available = credits - holds + releases
    held = holds - releases - payout_debits
    return {"available_paise": max(available, 0), "held_paise": max(held, 0)}


def _get_idempotency_row(merchant_id: int, idem_key, payload_hash: str) -> IdempotencyKey:
    now = timezone.now()
    row, _ = IdempotencyKey.objects.get_or_create(
        merchant_id=merchant_id,
        key=idem_key,
        defaults={
            "request_hash": payload_hash,
            "expires_at": now + timedelta(hours=24),
            "locked_until": now + timedelta(seconds=30),
        },
    )
    if row.expires_at < now:
        row.request_hash = payload_hash
        row.response_code = None
        row.response_body = None
        row.expires_at = now + timedelta(hours=24)
        row.locked_until = now + timedelta(seconds=30)
        row.save()
    if row.request_hash != payload_hash:
        raise ValidationError("Idempotency key reused with different payload")
    return row


def create_payout(*, merchant_id: int, bank_account_id: int, amount_paise: int, idem_key):
    payload_hash = _hash_payload({"bank_account_id": bank_account_id, "amount_paise": amount_paise})
    with transaction.atomic():
        merchant = Merchant.objects.select_for_update().get(id=merchant_id)
        idempotency_row = _get_idempotency_row(merchant.id, idem_key, payload_hash)
        if idempotency_row.response_body is not None:
            return idempotency_row.response_body, idempotency_row.response_code
        balances = get_balances(merchant.id)
        if balances["available_paise"] < amount_paise:
            raise ValidationError("Insufficient available balance")
        payout = Payout.objects.create(
            merchant_id=merchant.id,
            bank_account_id=bank_account_id,
            amount_paise=amount_paise,
            status=Payout.Status.PENDING,
            attempts=0,
            idempotency_key=idem_key,
        )
        LedgerEntry.objects.create(
            merchant_id=merchant.id,
            payout=payout,
            entry_type=LedgerEntry.EntryType.HOLD,
            amount_paise=amount_paise,
        )
        response = {
            "payout_id": payout.id,
            "merchant_id": merchant.id,
            "bank_account_id": bank_account_id,
            "amount_paise": amount_paise,
            "status": payout.status,
        }
        idempotency_row.response_body = response
        idempotency_row.response_code = status.HTTP_201_CREATED
        idempotency_row.locked_until = None
        idempotency_row.save(update_fields=["response_body", "response_code", "locked_until"])
    return response, status.HTTP_201_CREATED


def transition_payout(payout: Payout, to_status: str) -> None:
    allowed = {
        Payout.Status.PENDING: {Payout.Status.PROCESSING},
        Payout.Status.PROCESSING: {Payout.Status.COMPLETED, Payout.Status.FAILED},
    }
    if to_status not in allowed.get(payout.status, set()):
        raise ValidationError(f"Illegal status transition {payout.status} -> {to_status}")
    payout.status = to_status
    payout.save(update_fields=["status", "updated_at"])


def process_one_payout(payout_id: int) -> None:
    with transaction.atomic():
        payout = Payout.objects.select_for_update().get(id=payout_id)
        if payout.status != Payout.Status.PENDING:
            return
        transition_payout(payout, Payout.Status.PROCESSING)
        payout.attempts = 1
        payout.next_retry_at = timezone.now() + timedelta(seconds=2)
        payout.save(update_fields=["attempts", "next_retry_at", "updated_at"])

    roll = random.random()
    if roll < 0.7:
        with transaction.atomic():
            payout = Payout.objects.select_for_update().get(id=payout_id)
            if payout.status != Payout.Status.PROCESSING:
                return
            transition_payout(payout, Payout.Status.COMPLETED)
            LedgerEntry.objects.create(
                merchant_id=payout.merchant_id,
                payout=payout,
                entry_type=LedgerEntry.EntryType.PAYOUT_DEBIT,
                amount_paise=payout.amount_paise,
            )
    elif roll < 0.9:
        with transaction.atomic():
            payout = Payout.objects.select_for_update().get(id=payout_id)
            if payout.status != Payout.Status.PROCESSING:
                return
            transition_payout(payout, Payout.Status.FAILED)
            LedgerEntry.objects.create(
                merchant_id=payout.merchant_id,
                payout=payout,
                entry_type=LedgerEntry.EntryType.RELEASE,
                amount_paise=payout.amount_paise,
            )


def _attempt_processing_settlement(locked: Payout) -> bool:
    """
    Return True when payout reaches terminal state; False when still processing.
    Must be called while holding a row lock in an atomic transaction.
    """
    roll = random.random()
    if roll < 0.7:
        transition_payout(locked, Payout.Status.COMPLETED)
        LedgerEntry.objects.create(
            merchant_id=locked.merchant_id,
            payout=locked,
            entry_type=LedgerEntry.EntryType.PAYOUT_DEBIT,
            amount_paise=locked.amount_paise,
        )
        return True
    if roll < 0.9:
        transition_payout(locked, Payout.Status.FAILED)
        LedgerEntry.objects.create(
            merchant_id=locked.merchant_id,
            payout=locked,
            entry_type=LedgerEntry.EntryType.RELEASE,
            amount_paise=locked.amount_paise,
        )
        return True
    return False


def retry_stuck_payouts() -> None:
    cutoff = timezone.now() - timedelta(seconds=30)
    stuck = Payout.objects.filter(
        status=Payout.Status.PROCESSING,
        updated_at__lt=cutoff,
        next_retry_at__lte=timezone.now(),
    )
    for payout in stuck:
        with transaction.atomic():
            locked = Payout.objects.select_for_update().get(id=payout.id)
            if locked.status != Payout.Status.PROCESSING:
                continue
            if locked.attempts >= 3:
                transition_payout(locked, Payout.Status.FAILED)
                LedgerEntry.objects.create(
                    merchant_id=locked.merchant_id,
                    payout=locked,
                    entry_type=LedgerEntry.EntryType.RELEASE,
                    amount_paise=locked.amount_paise,
                )
                continue

            if _attempt_processing_settlement(locked):
                continue

            locked.attempts += 1
            if locked.attempts >= 3:
                transition_payout(locked, Payout.Status.FAILED)
                LedgerEntry.objects.create(
                    merchant_id=locked.merchant_id,
                    payout=locked,
                    entry_type=LedgerEntry.EntryType.RELEASE,
                    amount_paise=locked.amount_paise,
                )
                continue

            locked.next_retry_at = timezone.now() + timedelta(seconds=2 ** locked.attempts)
            locked.save(update_fields=["attempts", "next_retry_at", "updated_at"])
