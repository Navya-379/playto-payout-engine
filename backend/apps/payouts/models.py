import uuid

from django.db import models
from django.utils import timezone


class Merchant(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)


class BankAccount(models.Model):
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name="bank_accounts")
    account_holder_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=32)
    ifsc_code = models.CharField(max_length=16)
    created_at = models.DateTimeField(auto_now_add=True)


class Payout(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name="payouts")
    bank_account = models.ForeignKey(BankAccount, on_delete=models.PROTECT, related_name="payouts")
    amount_paise = models.BigIntegerField()
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveSmallIntegerField(default=0)
    next_retry_at = models.DateTimeField(default=timezone.now)
    idempotency_key = models.UUIDField(default=uuid.uuid4, editable=False)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class LedgerEntry(models.Model):
    class EntryType(models.TextChoices):
        CREDIT = "credit", "Credit"
        HOLD = "hold", "Hold"
        RELEASE = "release", "Release"
        PAYOUT_DEBIT = "payout_debit", "Payout Debit"

    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name="ledger_entries")
    payout = models.ForeignKey(Payout, on_delete=models.CASCADE, related_name="ledger_entries", null=True, blank=True)
    entry_type = models.CharField(max_length=32, choices=EntryType.choices)
    amount_paise = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class IdempotencyKey(models.Model):
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name="idempotency_keys")
    key = models.UUIDField()
    request_hash = models.CharField(max_length=64)
    response_code = models.IntegerField(null=True, blank=True)
    response_body = models.JSONField(null=True, blank=True)
    locked_until = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["merchant", "key"], name="uniq_merchant_idempotency_key"),
        ]
