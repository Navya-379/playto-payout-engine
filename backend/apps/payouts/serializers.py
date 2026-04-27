from rest_framework import serializers

from .models import BankAccount


class PayoutCreateSerializer(serializers.Serializer):
    merchant_id = serializers.IntegerField(min_value=1)
    bank_account_id = serializers.IntegerField(min_value=1)
    amount_paise = serializers.IntegerField(min_value=1)

    def validate(self, attrs):
        if not BankAccount.objects.filter(
            id=attrs["bank_account_id"],
            merchant_id=attrs["merchant_id"],
        ).exists():
            raise serializers.ValidationError("Bank account does not belong to merchant")
        return attrs
