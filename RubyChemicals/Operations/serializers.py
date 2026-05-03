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
            "id", "name", "group", "group_name", "hsn_code", "gst",
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

class StockLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockLog
        fields = ["id", "date", "stock_data"]

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
        fields = [
            "id", "cash_account", "expense_head", "expense_head_name", 
            "expense_date", "amount", "transaction_type", "notes",
            "to", "paid_via", "payment_type", "paid_by", "particulars",
            "created_by", "created_at"
        ]


class PettyCashLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PettyCashLog
        fields = ["id", "date", "cash_data"]


class ClientAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientAddress
        fields = [
            "id", "client", "address_type", "street", "city", "state", "contact_name", "contact_number", "gst_no", 
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



class VendorAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorAddress
        fields = [
            "id", "vendor", "address_type", "street", "city", "state",
            "postal_code", "country", "is_default"
        ]


class VendorProfileSerializer(serializers.ModelSerializer):
    addresses = VendorAddressSerializer(many=True, read_only=True)

    class Meta:
        model = VendorProfile
        fields = [
            "id", "company_name", "contact_person", "email", "phone",
            "gst_no", "notes", "is_active", "addresses"
        ]


class VendorProfileListSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorProfile
        fields = [
            "id", "company_name", "contact_person", "email", "phone", "is_active"
        ]


class VendorInwardItemSerializer(serializers.ModelSerializer):
    stock_item_name = serializers.CharField(source="stock_item.name", read_only=True)

    class Meta:
        model = StockInward
        fields = [
            "id", "stock_item", "stock_item_name",
            "quantity", "notes", "date"
        ]


class VendorInwardSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.company_name", read_only=True)
    items = VendorInwardItemSerializer(many=True, read_only=True)
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = VendorInward
        fields = [
            "id", "inward_code", "inward_date", "vendor", "vendor_name",
            "accounted", "invoice_number", "pdf", "image", "notes", "items", "item_count"
        ]

    def get_item_count(self, obj):
        return obj.items.filter(is_active=True).count()

