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

class ProductionConsumptionSerializer(serializers.ModelSerializer):
    stock_item_name = serializers.CharField(source="stock_item.name", read_only=True)

    class Meta:
        model = ProductionConsumption
        fields = ["id", "stock_item", "stock_item_name", "quantity_used"]


class ProductionBatchSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    consumptions = ProductionConsumptionSerializer(many=True, read_only=True)

    class Meta:
        model = ProductionBatch
        fields = [
            "id", "batch_code", "product", "product_name",
            "production_date", "output_quantity",
            "loss_quantity", "consumptions"
        ]

class DispatchSerializer(serializers.ModelSerializer):
    stock_item_name = serializers.CharField(source="stock_item.name", read_only=True)

    class Meta:
        model = Dispatch
        fields = "__all__"

class ExpenseHeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseHead
        fields = ["id", "name"]


class PettyCashSerializer(serializers.ModelSerializer):
    expense_head_name = serializers.CharField(source="expense_head.name", read_only=True)

    class Meta:
        model = PettyCash
        fields = "__all__"
