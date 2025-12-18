import random
import time

from celery import shared_task


@shared_task(bind=True)
def send_notification(self, *, to_wallet_id: str, transaction_id: str) -> None:
    try:
        time.sleep(5)
        if random.random() < 0.3:
            raise Exception("Simulated notification failure")
        return
    except Exception as e:
        raise self.retry(countdown=3, max_retries=3, exc=e)


