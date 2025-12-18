from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("wallets", "0001_initial"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="wallet",
            constraint=models.CheckConstraint(
                check=Q(balance__gte=0),
                name="wallet_balance_non_negative",
            ),
        ),
        migrations.AddConstraint(
            model_name="transaction",
            constraint=models.CheckConstraint(
                check=Q(amount__gt=0),
                name="tx_amount_gt_zero",
            ),
        ),
        migrations.AddConstraint(
            model_name="transaction",
            constraint=models.CheckConstraint(
                check=Q(fee__gte=0),
                name="tx_fee_non_negative",
            ),
        ),
    ]


