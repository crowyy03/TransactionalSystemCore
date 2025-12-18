import uuid
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class Wallet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner_name = models.CharField(max_length=128)
    balance = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=8, default="U")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["owner_name", "currency"], name="uniq_wallet_owner_currency"),
            models.CheckConstraint(check=Q(balance__gte=0), name="wallet_balance_non_negative"),
        ]

    def __str__(self) -> str:
        return f"{self.owner_name}:{self.currency} ({self.id})"


class TransactionStatus(models.TextChoices):
    SUCCESS = "SUCCESS", "SUCCESS"
    FAILED = "FAILED", "FAILED"


class Transaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    from_wallet = models.ForeignKey(
        Wallet,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="outgoing_transactions",
    )
    to_wallet = models.ForeignKey(
        Wallet,
        on_delete=models.PROTECT,
        related_name="incoming_transactions",
    )
    amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    fee = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=16, choices=TransactionStatus.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(check=Q(amount__gt=0), name="tx_amount_gt_zero"),
            models.CheckConstraint(check=Q(fee__gte=0), name="tx_fee_non_negative"),
        ]

    def __str__(self) -> str:
        return f"{self.id} {self.status} amount={self.amount} fee={self.fee}"


