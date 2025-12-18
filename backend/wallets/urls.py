from django.urls import path

from wallets.views import TransferAPIView


urlpatterns = [
    path("transfer", TransferAPIView.as_view(), name="transfer"),
    path("transfer/", TransferAPIView.as_view(), name="transfer_slash"),
]


