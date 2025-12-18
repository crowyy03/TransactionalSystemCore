from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import F

from wallets.models import Transaction, TransactionStatus, Wallet


class TransferError(Exception):
    pass


class InsufficientFunds(TransferError):
    pass


class InvalidTransfer(TransferError):
    pass


def _q2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _ensure_admin_wallet(currency: str) -> Wallet:
    owner = getattr(settings, "ADMIN_WALLET_OWNER_NAME", "admin")
    try:
        return Wallet.objects.get(owner_name=owner, currency=currency)
    except Wallet.DoesNotExist:
        try:
            return Wallet.objects.create(owner_name=owner, currency=currency, balance=Decimal("0.00"))
        except IntegrityError:
            return Wallet.objects.get(owner_name=owner, currency=currency)


@dataclass(frozen=True)
class TransferResult:
    transaction: Transaction
    from_wallet: Wallet
    to_wallet: Wallet
    admin_wallet: Wallet
    amount: Decimal
    fee: Decimal
    total_debited: Decimal


@transaction.atomic
def transfer(*, from_wallet_id: str, to_wallet_id: str, amount: Decimal) -> TransferResult:
    if from_wallet_id == to_wallet_id:
        raise InvalidTransfer("from_wallet_id и to_wallet_id должны отличаться")

    if amount <= 0:
        raise InvalidTransfer("amount должен быть > 0")

    amount = _q2(amount)

    from_currency = (
        Wallet.objects.filter(id=from_wallet_id).values_list("currency", flat=True).first()
    )
    if not from_currency:
        raise InvalidTransfer("from_wallet не найден")

    admin_wallet = _ensure_admin_wallet(currency=from_currency)

    wallet_ids: list[str] = [str(from_wallet_id), str(to_wallet_id), str(admin_wallet.id)]
    wallets = list(
        Wallet.objects.select_for_update()
        .filter(id__in=wallet_ids)
        .order_by("id")
    )
    if len(wallets) != 3:
        raise InvalidTransfer("Один или несколько кошельков не найдены")

    by_id = {str(w.id): w for w in wallets}
    from_wallet = by_id[str(from_wallet_id)]
    to_wallet = by_id[str(to_wallet_id)]
    admin_wallet = by_id[str(admin_wallet.id)]

    if from_wallet.currency != to_wallet.currency:
        raise InvalidTransfer("Валюты кошельков не совпадают")
    if admin_wallet.currency != from_wallet.currency:
        raise InvalidTransfer("Неподдерживаемая валюта/несовпадение валют")

    fee = Decimal("0.00")
    if amount > Decimal("1000.00"):
        fee = _q2(amount * Decimal("0.10"))

    total = _q2(amount + fee)

    if from_wallet.balance < total:
        raise InsufficientFunds("Insufficient funds")

    Wallet.objects.filter(id=from_wallet.id).update(balance=F("balance") - total)
    Wallet.objects.filter(id=to_wallet.id).update(balance=F("balance") + amount)
    if fee > 0:
        Wallet.objects.filter(id=admin_wallet.id).update(balance=F("balance") + fee)

    tx = Transaction.objects.create(
        from_wallet=from_wallet,
        to_wallet=to_wallet,
        amount=amount,
        fee=fee,
        status=TransactionStatus.SUCCESS,
    )

    from_wallet.refresh_from_db()
    to_wallet.refresh_from_db()
    admin_wallet.refresh_from_db()

    return TransferResult(
        transaction=tx,
        from_wallet=from_wallet,
        to_wallet=to_wallet,
        admin_wallet=admin_wallet,
        amount=amount,
        fee=fee,
        total_debited=total,
    )


