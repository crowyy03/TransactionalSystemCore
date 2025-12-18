from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal

import httpx
from django.conf import settings
from django.core.management.base import BaseCommand

from wallets.models import Wallet


class Command(BaseCommand):
    help = "Демо: 10 параллельных запросов на /api/transfer — баланс не уходит в минус."

    def add_arguments(self, parser):
        parser.add_argument("--base-url", default="http://localhost:8000", help="Базовый URL backend")
        parser.add_argument("--requests", type=int, default=10, help="Количество параллельных запросов")
        parser.add_argument("--amount", default="20.00", help="Сумма одного списания")

    def handle(self, *args, **options):
        base_url: str = options["base_url"].rstrip("/")
        n: int = int(options["requests"])
        amount = Decimal(str(options["amount"]))

        currency = getattr(settings, "DEFAULT_CURRENCY", "U")
        admin_owner = getattr(settings, "ADMIN_WALLET_OWNER_NAME", "admin")

        a, _ = Wallet.objects.get_or_create(owner_name="A", currency=currency, defaults={"balance": Decimal("0.00")})
        b, _ = Wallet.objects.get_or_create(owner_name="B", currency=currency, defaults={"balance": Decimal("0.00")})
        admin, _ = Wallet.objects.get_or_create(owner_name=admin_owner, currency=currency, defaults={"balance": Decimal("0.00")})

        Wallet.objects.filter(id=a.id).update(balance=Decimal("100.00"))
        Wallet.objects.filter(id=b.id).update(balance=Decimal("0.00"))
        Wallet.objects.filter(id=admin.id).update(balance=Decimal("0.00"))

        a.refresh_from_db()
        b.refresh_from_db()
        admin.refresh_from_db()

        self.stdout.write(self.style.SUCCESS(f"Wallet A: {a.id} balance={a.balance}"))
        self.stdout.write(self.style.SUCCESS(f"Wallet B: {b.id} balance={b.balance}"))
        self.stdout.write(self.style.SUCCESS(f"Wallet admin: {admin.id} balance={admin.balance}"))

        url = f"{base_url}/api/transfer"
        payload = {
            "from_wallet_id": str(a.id),
            "to_wallet_id": str(b.id),
            "amount": f"{amount:.2f}",
        }

        barrier = threading.Barrier(n)

        def do_request(i: int):
            barrier.wait()
            with httpx.Client(timeout=20.0) as client:
                try:
                    r = client.post(url, json=payload)
                    return i, r.status_code, r.text
                except Exception as e:
                    return i, 0, str(e)

        ok = 0
        fail = 0
        statuses: dict[int, int] = {}

        self.stdout.write(f"Стартуем {n} параллельных запросов по {payload['amount']} на {url} ...")

        with ThreadPoolExecutor(max_workers=n) as ex:
            futures = [ex.submit(do_request, i) for i in range(n)]
            for fut in as_completed(futures):
                i, status, body = fut.result()
                statuses[i] = status
                if 200 <= status < 300:
                    ok += 1
                else:
                    fail += 1
                try:
                    parsed = json.loads(body)
                    detail = parsed.get("detail")
                except Exception:
                    detail = body[:120]
                self.stdout.write(f"#{i}: status={status} detail={detail}")

        a.refresh_from_db()
        b.refresh_from_db()
        admin.refresh_from_db()

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Итог: success={ok}, failed={fail}"))
        self.stdout.write(self.style.SUCCESS(f"Final A balance={a.balance} (должно быть >= 0.00)"))
        self.stdout.write(self.style.SUCCESS(f"Final B balance={b.balance}"))
        self.stdout.write(self.style.SUCCESS(f"Final admin balance={admin.balance}"))


