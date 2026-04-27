from django.core.management.base import BaseCommand

from apps.payouts.models import BankAccount, LedgerEntry, Merchant


class Command(BaseCommand):
    help = "Seeds merchants, bank accounts, and credits"

    def handle(self, *args, **options):
        seeds = [
            ("Acme Agency", 200_000),
            ("Pixel Freelance", 150_000),
            ("Growth Studio", 350_000),
        ]
        for name, credit_paise in seeds:
            merchant, _ = Merchant.objects.get_or_create(name=name)
            BankAccount.objects.get_or_create(
                merchant=merchant,
                account_number=f"{merchant.id:08d}1234",
                defaults={"account_holder_name": name, "ifsc_code": "HDFC0001234"},
            )
            has_credit = LedgerEntry.objects.filter(
                merchant=merchant,
                entry_type=LedgerEntry.EntryType.CREDIT,
            ).exists()
            if not has_credit:
                LedgerEntry.objects.create(
                    merchant=merchant,
                    entry_type=LedgerEntry.EntryType.CREDIT,
                    amount_paise=credit_paise,
                )
        self.stdout.write(self.style.SUCCESS("Seeded test data"))
