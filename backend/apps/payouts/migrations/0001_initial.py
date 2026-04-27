import django.utils.timezone
import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Merchant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="BankAccount",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("account_holder_name", models.CharField(max_length=255)),
                ("account_number", models.CharField(max_length=32)),
                ("ifsc_code", models.CharField(max_length=16)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "merchant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bank_accounts",
                        to="payouts.merchant",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Payout",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount_paise", models.BigIntegerField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("processing", "Processing"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                        ],
                        default="pending",
                        max_length=32,
                    ),
                ),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
                ("next_retry_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("idempotency_key", models.UUIDField(default=uuid.uuid4, editable=False)),
                ("last_error", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "bank_account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="payouts",
                        to="payouts.bankaccount",
                    ),
                ),
                (
                    "merchant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="payouts",
                        to="payouts.merchant",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="LedgerEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "entry_type",
                    models.CharField(
                        choices=[
                            ("credit", "Credit"),
                            ("hold", "Hold"),
                            ("release", "Release"),
                            ("payout_debit", "Payout Debit"),
                        ],
                        max_length=32,
                    ),
                ),
                ("amount_paise", models.BigIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "merchant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ledger_entries",
                        to="payouts.merchant",
                    ),
                ),
                (
                    "payout",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ledger_entries",
                        to="payouts.payout",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="IdempotencyKey",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.UUIDField()),
                ("request_hash", models.CharField(max_length=64)),
                ("response_code", models.IntegerField(blank=True, null=True)),
                ("response_body", models.JSONField(blank=True, null=True)),
                ("locked_until", models.DateTimeField(blank=True, null=True)),
                ("expires_at", models.DateTimeField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "merchant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="idempotency_keys",
                        to="payouts.merchant",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("merchant", "key"), name="uniq_merchant_idempotency_key"),
                ],
            },
        ),
    ]
