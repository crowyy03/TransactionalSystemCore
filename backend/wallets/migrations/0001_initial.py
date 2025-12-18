import uuid
from decimal import Decimal

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Wallet",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("owner_name", models.CharField(max_length=128)),
                ("balance", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=18)),
                ("currency", models.CharField(default="U", max_length=8)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("owner_name", "currency"), name="uniq_wallet_owner_currency"),
                ],
            },
        ),
        migrations.CreateModel(
            name="Transaction",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=18)),
                ("fee", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=18)),
                ("status", models.CharField(choices=[("SUCCESS", "SUCCESS"), ("FAILED", "FAILED")], max_length=16)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "from_wallet",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="outgoing_transactions",
                        to="wallets.wallet",
                    ),
                ),
                (
                    "to_wallet",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="incoming_transactions",
                        to="wallets.wallet",
                    ),
                ),
            ],
        ),
    ]


