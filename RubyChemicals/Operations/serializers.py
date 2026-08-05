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
            "created_by", "created_at", "is_active"
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



class LeadCallRecordSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    lead_status_display = serializers.CharField(source='get_lead_status_display', read_only=True)

    class Meta:
        model = LeadCallRecord
        fields = [
            'id', 'lead', 'call_date', 'contact_number', 'briefing',
            'lead_status', 'lead_status_display', 'next_followup',
            'follow_up_done', 'forwarded_to',
            'created_by', 'created_by_name', 'created_at'
        ]
        read_only_fields = ['created_by', 'created_at']


class LeadSerializer(serializers.ModelSerializer):
    call_records = LeadCallRecordSerializer(many=True, read_only=True)
    party_type_display = serializers.CharField(source='get_party_type_display', read_only=True)
    lead_status_display = serializers.CharField(source='get_lead_status_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    call_count = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = [
            'id', 'lead_id', 'date_of_connect', 'lead_source',
            'party_type', 'party_type_display', 'party_name', 'location',
            'contact_person', 'mobile_number', 'email',
            'lead_status', 'lead_status_display', 'remarks',
            'next_followup', 'forwarded_to',
            'created_by', 'created_by_name', 'created_at', 'updated_at',
            'call_records', 'call_count'
        ]
        read_only_fields = ['lead_id', 'created_by', 'created_at', 'updated_at']

    def get_call_count(self, obj):
        return obj.call_records.filter(is_active=True).count()


class LeadListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views (no nested call records)"""
    party_type_display = serializers.CharField(source='get_party_type_display', read_only=True)
    lead_status_display = serializers.CharField(source='get_lead_status_display', read_only=True)
    # sub_department_id = serializers.CharField(source='sub_department.id')
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    call_count = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = [
            'id', 'lead_id', 'date_of_connect', 'lead_source',
            'party_type', 'party_type_display', 'party_name', 'location',
            'contact_person', 'mobile_number', 'email',
            'lead_status', 'lead_status_display', 'remarks',
            'next_followup', 'forwarded_to',
            'created_by_name', 'created_at', 'call_count', 'sub_department'
        ]

    def get_call_count(self, obj):
        return obj.call_records.filter(is_active=True).count()




# ── LeadSubDepartment ─────────────────────────────────────────────────────────

class LeadSubDepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadSubDepartment
        fields = ['id', 'name', 'code', 'description', 'is_active', 'created_at']


# ── SubDeptStockItem ──────────────────────────────────────────────────────────

class SubDeptStockItemSerializer(serializers.ModelSerializer):
    sub_department_name = serializers.CharField(
        source='sub_department.name', read_only=True
    )

    class Meta:
        model = SubDeptStockItem
        fields = [
            'id', 'sub_department', 'sub_department_name',
            'product_name', 'hsn_code', 'rate', 'uom', 'warranty',
            'is_active', 'created_at',
        ]


class SubDeptStockItemListSerializer(serializers.ModelSerializer):
    """Lightweight list serializer"""
    class Meta:
        model = SubDeptStockItem
        fields = ['id', 'product_name', 'hsn_code', 'rate', 'uom', 'warranty', 'is_active']


# ── DeptLead ──────────────────────────────────────────────────────────────────

# class DeptLeadListSerializer(serializers.ModelSerializer):
#     """Lightweight serializer for list views"""
#     sub_department_name = serializers.CharField(
#         source='sub_department.name', read_only=True
#     )
#     sub_department_code = serializers.CharField(
#         source='sub_department.code', read_only=True
#     )
#     party_type_display = serializers.CharField(
#         source='get_party_type_display', read_only=True
#     )
#     lead_status_display = serializers.CharField(
#         source='get_lead_status_display', read_only=True
#     )
#     created_by_name = serializers.CharField(source='created_by.name', read_only=True)

#     class Meta:
#         model = DeptLead
#         fields = [
#             'id', 'lead_id', 'sub_department', 'sub_department_name', 'sub_department_code',
#             'date_of_connect', 'lead_source',
#             'party_type', 'party_type_display', 'party_name', 'location',
#             'contact_person', 'mobile_number', 'email',
#             'lead_status', 'lead_status_display', 'remarks',
#             'next_followup', 'forwarded_to',
#             'created_by_name', 'created_at',
#         ]


# class DeptLeadSerializer(serializers.ModelSerializer):
#     sub_department_name = serializers.CharField(
#         source='sub_department.name', read_only=True
#     )
#     sub_department_code = serializers.CharField(
#         source='sub_department.code', read_only=True
#     )
#     party_type_display = serializers.CharField(
#         source='get_party_type_display', read_only=True
#     )
#     lead_status_display = serializers.CharField(
#         source='get_lead_status_display', read_only=True
#     )
#     created_by_name = serializers.CharField(source='created_by.name', read_only=True)
#     # Flag to check if this lead has application detail
#     has_application_detail = serializers.SerializerMethodField()

#     class Meta:
#         model = DeptLead
#         fields = [
#             'id', 'lead_id', 'sub_department', 'sub_department_name', 'sub_department_code',
#             'date_of_connect', 'lead_source',
#             'party_type', 'party_type_display', 'party_name', 'location',
#             'contact_person', 'mobile_number', 'email',
#             'lead_status', 'lead_status_display', 'remarks',
#             'next_followup', 'forwarded_to',
#             'created_by', 'created_by_name', 'created_at', 'updated_at',
#             'has_application_detail',
#         ]
#         read_only_fields = ['lead_id', 'created_by', 'created_at', 'updated_at']

#     def get_has_application_detail(self, obj):
#         return hasattr(obj, 'application_detail')


# ── Quotation ─────────────────────────────────────────────────────────────────

class QuotationItemSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField()
    hsn_code     = serializers.SerializerMethodField()
    warranty     = serializers.CharField(read_only=True)
    total        = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True
    )

    class Meta:
        model  = QuotationItem
        fields = [
            'id', 'stock_item', 'product_name', 'hsn_code', 'application_area', 'scope',
            'quantity', 'rate', 'uom', 'warranty', 'description', 'total', 'is_active',
        ]

    def get_product_name(self, obj):
        if obj.stock_item:
            return obj.stock_item.product_name
        return obj.product_name

    def get_hsn_code(self, obj):
        if obj.stock_item:
            return obj.stock_item.hsn_code
        return obj.hsn_code


class QuotationSerializer(serializers.ModelSerializer):
    items = QuotationItemSerializer(many=True, read_only=True)
    lead_party_name = serializers.CharField(source='lead.party_name', read_only=True)
    lead_id_display = serializers.IntegerField(source='lead.lead_id', read_only=True)
    sub_department_name = serializers.CharField(
        source='lead.sub_department.name', read_only=True
    )
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    grand_total = serializers.SerializerMethodField()

    class Meta:
        model = Quotation
        fields = [
            'id', 'quotation_no', 'lead', 'lead_id_display', 'lead_party_name',
            'sub_department_name', 'quotation_date', 'status',
            'billing_address', 'shipping_address', 'notes',
            'created_by', 'created_by_name', 'created_at', 'updated_at',
            'items', 'grand_total',
        ]
        read_only_fields = ['quotation_no', 'created_by', 'created_at', 'updated_at']

    def get_grand_total(self, obj):
        total = sum(
            item.quantity * item.rate
            for item in obj.items.filter(is_active=True)
        )
        return total


class QuotationListSerializer(serializers.ModelSerializer):
    lead_party_name = serializers.CharField(source='lead.party_name', read_only=True)
    lead_id_display = serializers.IntegerField(source='lead.lead_id', read_only=True)
    sub_department_name = serializers.CharField(
        source='lead.sub_department.name', read_only=True
    )
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Quotation
        fields = [
            'id', 'quotation_no', 'lead', 'lead_id_display', 'lead_party_name',
            'sub_department_name', 'quotation_date', 'status',
            'created_at', 'item_count',
        ]

    def get_item_count(self, obj):
        return obj.items.filter(is_active=True).count()


# ── SampleRequisite ──────────────────────────────────────────────────────────

class SampleRequisiteItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source='stock_item.product_name', read_only=True
    )
    hsn_code = serializers.CharField(
        source='stock_item.hsn_code', read_only=True
    )

    class Meta:
        model = SampleRequisiteItem
        fields = [
            'id', 'stock_item', 'product_name', 'hsn_code',
            'quantity', 'uom', 'qty_sent', 'notes', 'is_active',
        ]


class SampleRequisiteSerializer(serializers.ModelSerializer):
    items = SampleRequisiteItemSerializer(many=True, read_only=True)
    lead_party_name = serializers.CharField(source='lead.party_name', read_only=True)
    lead_id_display = serializers.IntegerField(source='lead.lead_id', read_only=True)
    sub_department_name = serializers.CharField(
        source='lead.sub_department.name', read_only=True
    )
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = SampleRequisite
        fields = [
            'id', 'sr_no', 'lead', 'lead_id_display', 'lead_party_name',
            'sub_department_name', 'sr_date', 'status', 'status_display',
            'delivery_address', 'contact_name', 'contact_number', 'notes',
            'sent_to_factory_at', 'factory_remarks',
            'created_by', 'created_by_name', 'created_at', 'updated_at',
            'items',
        ]
        read_only_fields = ['sr_no', 'created_by', 'created_at', 'updated_at']


class SampleRequisiteListSerializer(serializers.ModelSerializer):
    lead_party_name = serializers.CharField(source='lead.party_name', read_only=True)
    lead_id_display = serializers.IntegerField(source='lead.lead_id', read_only=True)
    sub_department_name = serializers.CharField(
        source='lead.sub_department.name', read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = SampleRequisite
        fields = [
            'id', 'sr_no', 'lead', 'lead_id_display', 'lead_party_name',
            'sub_department_name', 'sr_date', 'status', 'status_display',
            'sent_to_factory_at', 'created_at', 'item_count',
        ]

    def get_item_count(self, obj):
        return obj.items.filter(is_active=True).count()


# ── Application Area & System Products ───────────────────────────────────────

class ApplicationSystemProductItemSerializer(serializers.ModelSerializer):
    resolved_name = serializers.SerializerMethodField()

    class Meta:
        model = ApplicationSystemProductItem
        fields = [
            'id', 'stock_item', 'product_name', 'hsn_code', 'rate', 'uom',
            'quantity', 'is_active', 'resolved_name',
        ]

    def get_resolved_name(self, obj):
        return obj.get_product_name()


class ApplicationSystemProductSerializer(serializers.ModelSerializer):
    items = ApplicationSystemProductItemSerializer(many=True, read_only=True)
    application_area_name = serializers.CharField(
        source='application_area.name', read_only=True
    )

    class Meta:
        model = ApplicationSystemProduct
        fields = [
            'id', 'application_area', 'application_area_name',
            'name', 'description', 'is_active', 'created_at', 'items',
        ]


class ApplicationFixedItemSerializer(serializers.ModelSerializer):
    resolved_name = serializers.SerializerMethodField()

    class Meta:
        model = ApplicationFixedItem
        fields = [
            'id', 'stock_item', 'product_name', 'hsn_code', 'rate', 'uom',
            'quantity', 'is_active', 'resolved_name',
        ]

    def get_resolved_name(self, obj):
        return obj.get_product_name()


class ApplicationAreaSerializer(serializers.ModelSerializer):
    system_products = ApplicationSystemProductSerializer(many=True, read_only=True)
    fixed_items = ApplicationFixedItemSerializer(many=True, read_only=True)
    sub_department_name = serializers.CharField(
        source='sub_department.name', read_only=True
    )

    class Meta:
        model = ApplicationArea
        fields = [
            'id', 'sub_department', 'sub_department_name',
            'name', 'description', 'is_active', 'created_at',
            'system_products', 'fixed_items',
        ]


class ApplicationAreaListSerializer(serializers.ModelSerializer):
    sub_department_name = serializers.CharField(
        source='sub_department.name', read_only=True
    )
    system_product_count = serializers.SerializerMethodField()
    fixed_item_count = serializers.SerializerMethodField()

    class Meta:
        model = ApplicationArea
        fields = [
            'id', 'sub_department', 'sub_department_name',
            'name', 'description', 'is_active',
            'system_product_count', 'fixed_item_count',
        ]

    def get_system_product_count(self, obj):
        return obj.system_products.filter(is_active=True).count()

    def get_fixed_item_count(self, obj):
        return obj.fixed_items.filter(is_active=True).count()


# ── ApplicationLead ───────────────────────────────────────────────────────────

class ApplicationLeadSerializer(serializers.ModelSerializer):
    application_area_name = serializers.CharField(
        source='application_area.name', read_only=True
    )
    selected_system_products_detail = ApplicationSystemProductSerializer(
        source='selected_system_products', many=True, read_only=True
    )
    fixed_items = serializers.SerializerMethodField()

    class Meta:
        model = ApplicationLead
        fields = [
            'id', 'dept_lead',
            'application_area', 'application_area_name',
            'selected_system_products', 'selected_system_products_detail',
            'fixed_items', 'notes', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_fixed_items(self, obj):
        fixed = obj.application_area.fixed_items.filter(is_active=True)
        return ApplicationFixedItemSerializer(fixed, many=True).data

