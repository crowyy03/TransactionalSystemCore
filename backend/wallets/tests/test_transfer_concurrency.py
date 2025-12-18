from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal

from django.conf import settings
from django.db import close_old_connections, connection, connections
from django.test import TransactionTestCase

from wallets.models import Wallet
from wallets.services import InsufficientFunds, transfer


class TransferConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def test_concurrent_double_spending_protection(self):
        currency = getattr(settings, "DEFAULT_CURRENCY", "U")
        admin_owner = getattr(settings, "ADMIN_WALLET_OWNER_NAME", "admin")

        Wallet.objects.create(owner_name=admin_owner, currency=currency, balance=Decimal("0.00"))
        a = Wallet.objects.create(owner_name="A_conc", currency=currency, balance=Decimal("100.00"))
        b = Wallet.objects.create(owner_name="B_conc", currency=currency, balance=Decimal("0.00"))

        n = 10
        barrier = threading.Barrier(n)

        def worker():
            close_old_connections()
            try:
                barrier.wait()
                try:
                    transfer(from_wallet_id=str(a.id), to_wallet_id=str(b.id), amount=Decimal("20.00"))
                    return True
                except InsufficientFunds:
                    return False
            finally:
                connection.close()

        results = []
        with ThreadPoolExecutor(max_workers=n) as ex:
            futs = [ex.submit(worker) for _ in range(n)]
            for fut in as_completed(futs):
                results.append(fut.result())

        connections.close_all()

        success = sum(1 for r in results if r)
        fail = sum(1 for r in results if not r)

        a.refresh_from_db()
        b.refresh_from_db()
        admin = Wallet.objects.get(owner_name=admin_owner, currency=currency)

        self.assertEqual(success, 5)
        self.assertEqual(fail, 5)
        self.assertEqual(a.balance, Decimal("0.00"))
        self.assertEqual(b.balance, Decimal("100.00"))
        self.assertEqual(admin.balance, Decimal("0.00"))


