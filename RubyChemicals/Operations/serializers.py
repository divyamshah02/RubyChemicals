from rest_framework import serializers
from .models import *

class StockGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockGroup
        fields = ["id", "name", "description"]


class StockItemSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source="group.name", read_only=True)

    class Meta:
        model = StockItem
        fields = [
            "id", "name", "group", "group_name",
            "unit", "current_quantity", "rate", "is_active"
        ]

class StockInwardSerializer(serializers.ModelSerializer):
    stock_item_name = serializers.CharField(source="stock_item.name", read_only=True)

    class Meta:
        model = StockInward
        fields = "__all__"

class StockAdjustmentSerializer(serializers.ModelSerializer):
    stock_item_name = serializers.CharField(source="stock_item.name", read_only=True)

    class Meta:
        model = StockAdjustment
        fields = "__all__"

class ProductionCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductionCard
        fields = [
            "id", "production_code", "production_date", "product_name", 
            "total_output_quantity", "total_loss", "unit", "accounted", 
            "remarks", "notes", "created_by"
        ]


class ProductionBatchSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_unit = serializers.CharField(source="product.unit", read_only=True)

    class Meta:
        model = ProductionBatch
        fields = [
            "id", "batch_code", "production_card", "product", "product_name",
            "product_unit", "output_quantity", "loss_quantity"
        ]


class ProductionConsumptionSerializer(serializers.ModelSerializer):
    stock_item_name = serializers.CharField(source="stock_item.name", read_only=True)

    class Meta:
        model = ProductionConsumption
        fields = ["id", "stock_item", "stock_item_name", "quantity_used"]


class ProductionCardDetailSerializer(serializers.ModelSerializer):
    batches = ProductionBatchSerializer(many=True, read_only=True)
    consumptions = ProductionConsumptionSerializer(many=True, read_only=True)

    class Meta:
        model = ProductionCard
        fields = [
            "id", "production_code", "production_date", "product_name",
            "total_output_quantity", "total_loss", "unit", "accounted", 
            "remarks", "notes", "batches", "consumptions", "created_by"
        ]

class DispatchSerializer(serializers.ModelSerializer):
    stock_item_name = serializers.CharField(source="stock_item.name", read_only=True)
    client_name = serializers.CharField(source="client.company_name", read_only=True)

    class Meta:
        model = Dispatch
        fields = [
            "id", "dispatch_code", "dispatch_date", "stock_item", "stock_item_name",
            "client", "client_name", "dispatch_quantity", "unit", "shipping_address", "notes"
        ]

class ExpenseHeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseHead
        fields = ["id", "name"]


class PettyCashSerializer(serializers.ModelSerializer):
    expense_head_name = serializers.CharField(source="expense_head.name", read_only=True)

    class Meta:
        model = PettyCash
        fields = "__all__"


class ClientAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientAddress
        fields = [
            "id", "client", "address_type", "street", "city", "state",
            "postal_code", "country", "is_default"
        ]


class ClientProfileSerializer(serializers.ModelSerializer):
    addresses = ClientAddressSerializer(many=True, read_only=True)

    class Meta:
        model = ClientProfile
        fields = [
            "id", "company_name", "contact_person", "email", "phone",
            "gst_no", "notes", "is_active", "addresses"
        ]


class ClientProfileListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientProfile
        fields = [
            "id", "company_name", "contact_person", "email", "phone", "is_active"
        ]
