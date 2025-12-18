from decimal import Decimal

from django.conf import settings
from django.test import TestCase
from rest_framework.test import APIClient

from wallets.models import Transaction, Wallet


class TransferAPITests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.currency = getattr(settings, "DEFAULT_CURRENCY", "U")
        self.admin_owner = getattr(settings, "ADMIN_WALLET_OWNER_NAME", "admin")

        self.admin = Wallet.objects.create(owner_name=self.admin_owner, currency=self.currency, balance=Decimal("0.00"))
        self.a = Wallet.objects.create(owner_name="A_test", currency=self.currency, balance=Decimal("0.00"))
        self.b = Wallet.objects.create(owner_name="B_test", currency=self.currency, balance=Decimal("0.00"))

    def test_success_without_fee(self):
        self.a.balance = Decimal("100.00")
        self.a.save(update_fields=["balance"])

        r = self.client.post(
            "/api/transfer/",
            data={"from_wallet_id": str(self.a.id), "to_wallet_id": str(self.b.id), "amount": "10.00"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)

        self.a.refresh_from_db()
        self.b.refresh_from_db()
        self.admin.refresh_from_db()

        self.assertEqual(self.a.balance, Decimal("90.00"))
        self.assertEqual(self.b.balance, Decimal("10.00"))
        self.assertEqual(self.admin.balance, Decimal("0.00"))
        self.assertEqual(Transaction.objects.count(), 1)

    def test_success_with_fee(self):
        self.a.balance = Decimal("2000.00")
        self.a.save(update_fields=["balance"])

        r = self.client.post(
            "/api/transfer/",
            data={"from_wallet_id": str(self.a.id), "to_wallet_id": str(self.b.id), "amount": "1500.00"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)

        self.a.refresh_from_db()
        self.b.refresh_from_db()
        self.admin.refresh_from_db()

        self.assertEqual(self.a.balance, Decimal("350.00"))
        self.assertEqual(self.b.balance, Decimal("1500.00"))
        self.assertEqual(self.admin.balance, Decimal("150.00"))

    def test_insufficient_funds(self):
        self.a.balance = Decimal("10.00")
        self.a.save(update_fields=["balance"])

        r = self.client.post(
            "/api/transfer/",
            data={"from_wallet_id": str(self.a.id), "to_wallet_id": str(self.b.id), "amount": "20.00"},
            format="json",
        )
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.json().get("detail"), "Insufficient funds")


