from django.contrib import admin

from wallets.models import Transaction, Wallet


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("id", "owner_name", "currency", "balance", "created_at", "updated_at")
    list_filter = ("currency", "owner_name")
    search_fields = ("id", "owner_name")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "from_wallet", "to_wallet", "amount", "fee", "created_at")
    list_filter = ("status",)
    search_fields = ("id",)


