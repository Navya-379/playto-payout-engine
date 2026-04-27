from celery import shared_task

from .models import Payout
from .services import process_one_payout, retry_stuck_payouts


@shared_task
def process_pending_payouts() -> None:
    for payout_id in Payout.objects.filter(status=Payout.Status.PENDING).values_list("id", flat=True)[:50]:
        process_one_payout(payout_id)


@shared_task
def retry_processing_payouts() -> None:
    retry_stuck_payouts()
