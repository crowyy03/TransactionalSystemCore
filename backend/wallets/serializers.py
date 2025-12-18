from decimal import Decimal

from rest_framework import serializers


class TransferRequestSerializer(serializers.Serializer):
    from_wallet_id = serializers.UUIDField()
    to_wallet_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)

    def validate_amount(self, value: Decimal) -> Decimal:
        if value <= 0:
            raise serializers.ValidationError("amount должен быть > 0")
        return value


