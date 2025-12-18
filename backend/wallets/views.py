from django.db import transaction as db_transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from wallets.serializers import TransferRequestSerializer
from wallets.services import InsufficientFunds, InvalidTransfer, transfer
from wallets.tasks import send_notification


class TransferAPIView(APIView):
    def post(self, request):
        serializer = TransferRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        try:
            result = transfer(
                from_wallet_id=str(data["from_wallet_id"]),
                to_wallet_id=str(data["to_wallet_id"]),
                amount=data["amount"],
            )
        except InsufficientFunds:
            return Response({"detail": "Insufficient funds"}, status=status.HTTP_409_CONFLICT)
        except InvalidTransfer as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        db_transaction.on_commit(
            lambda: send_notification.delay(
                to_wallet_id=str(result.to_wallet.id),
                transaction_id=str(result.transaction.id),
            )
        )

        return Response(
            {
                "transaction_id": str(result.transaction.id),
                "amount": f"{result.amount:.2f}",
                "fee": f"{result.fee:.2f}",
                "total_debited": f"{result.total_debited:.2f}",
                "balances": {
                    "from_wallet": {"id": str(result.from_wallet.id), "balance": f"{result.from_wallet.balance:.2f}"},
                    "to_wallet": {"id": str(result.to_wallet.id), "balance": f"{result.to_wallet.balance:.2f}"},
                    "admin_wallet": {"id": str(result.admin_wallet.id), "balance": f"{result.admin_wallet.balance:.2f}"},
                },
            },
            status=status.HTTP_200_OK,
        )


