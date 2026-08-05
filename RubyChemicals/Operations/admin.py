from django.contrib import admin
from .models import *


# ---------------- STOCK ---------------- #

@admin.register(StockGroup)
class StockGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    search_fields = ('name',)
    list_filter = ('is_active',)


@admin.register(StockItem)
class StockItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'group', 'unit', 'current_quantity', 'rate', 'is_active')
    search_fields = ('name', 'group__name')
    list_filter = ('group', 'unit', 'is_active')
    autocomplete_fields = ('group',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('group')


@admin.register(StockLog)
class StockLogAdmin(admin.ModelAdmin):
    list_display = ('date', 'created_at', 'updated_at')
    ordering = ('-date',)
    readonly_fields = ('created_at', 'updated_at')


# ---------------- VENDOR ---------------- #

@admin.register(VendorProfile)
class VendorProfileAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'contact_person', 'phone', 'is_active')
    search_fields = ('company_name', 'contact_person', 'phone')
    list_filter = ('is_active',)


@admin.register(VendorAddress)
class VendorAddressAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'address_type', 'city', 'is_default')
    search_fields = ('vendor__company_name', 'city', 'street')
    autocomplete_fields = ('vendor',)


class VendorAddressInline(admin.TabularInline):
    model = VendorAddress
    extra = 1


class StockInwardInline(admin.TabularInline):
    model = StockInward
    extra = 1
    autocomplete_fields = ('stock_item',)


@admin.register(VendorInward)
class VendorInwardAdmin(admin.ModelAdmin):
    list_display = ('inward_code', 'vendor', 'inward_date', 'accounted', 'created_at')
    search_fields = ('inward_code', 'invoice_number', 'vendor__company_name')
    list_filter = ('accounted', 'inward_date')
    autocomplete_fields = ('vendor',)
    inlines = [StockInwardInline]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('vendor')


@admin.register(StockInward)
class StockInwardAdmin(admin.ModelAdmin):
    list_display = ('stock_item', 'quantity', 'date', 'created_at')
    list_filter = ('date',)
    search_fields = ('stock_item__name',)
    autocomplete_fields = ('stock_item', 'inward_entry')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('stock_item', 'inward_entry')


@admin.register(StockAdjustment)
class StockAdjustmentAdmin(admin.ModelAdmin):
    list_display = ('stock_item', 'adjustment_type', 'quantity', 'date')
    list_filter = ('adjustment_type', 'date')
    search_fields = ('stock_item__name',)
    autocomplete_fields = ('stock_item',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('stock_item')


# ---------------- PRODUCTION ---------------- #

class ProductionBatchInline(admin.TabularInline):
    model = ProductionBatch
    extra = 1
    autocomplete_fields = ('product',)


class ProductionConsumptionInline(admin.TabularInline):
    model = ProductionConsumption
    extra = 1
    autocomplete_fields = ('stock_item',)


@admin.register(ProductionCard)
class ProductionCardAdmin(admin.ModelAdmin):
    list_display = ('production_code', 'production_date', 'total_output_quantity', 'accounted')
    list_filter = ('accounted', 'production_date')
    search_fields = ('production_code', 'product_name')
    inlines = [ProductionBatchInline, ProductionConsumptionInline]


@admin.register(ProductionBatch)
class ProductionBatchAdmin(admin.ModelAdmin):
    list_display = ('batch_code', 'product', 'output_quantity', 'loss_quantity')
    search_fields = ('batch_code', 'product__name')
    autocomplete_fields = ('product', 'production_card')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product', 'production_card')


@admin.register(ProductionConsumption)
class ProductionConsumptionAdmin(admin.ModelAdmin):
    list_display = ('production_card', 'stock_item', 'quantity_used')
    search_fields = ('stock_item__name', 'production_card__production_code')
    autocomplete_fields = ('production_card', 'stock_item')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('production_card', 'stock_item')


# ---------------- PETTY CASH ---------------- #

@admin.register(PettyCashAccount)
class PettyCashAccountAdmin(admin.ModelAdmin):
    list_display = ('cash_type', 'current_balance', 'credit_balance')
    search_fields = ('cash_type',)


@admin.register(ExpenseHead)
class ExpenseHeadAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    search_fields = ('name',)


@admin.register(PettyCash)
class PettyCashAdmin(admin.ModelAdmin):
    list_display = ('cash_account', 'expense_head', 'amount', 'transaction_type', 'expense_date', 'paid_via', 'payment_type')
    list_filter = ('transaction_type', 'expense_date', 'paid_via', 'payment_type')
    search_fields = ('expense_head__name', 'to', 'paid_by', 'particulars')
    autocomplete_fields = ('cash_account', 'expense_head')
    fieldsets = (
        ('Transaction Details', {
            'fields': ('cash_account', 'expense_head', 'expense_date', 'amount', 'transaction_type')
        }),
        ('Payment Information', {
            'fields': ('to', 'paid_via', 'payment_type', 'paid_by', 'particulars')
        }),
        ('Additional', {
            'fields': ('notes', 'created_by', 'is_active')
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('cash_account', 'expense_head')


@admin.register(PettyCashLog)
class PettyCashLogAdmin(admin.ModelAdmin):
    list_display = ('date', 'created_at', 'updated_at')
    ordering = ('-date',)
    readonly_fields = ('created_at', 'updated_at')
    search_fields = ('date',)


# ---------------- CLIENT ---------------- #

@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'contact_person', 'phone', 'is_active')
    search_fields = ('company_name', 'contact_person')
    list_filter = ('is_active',)


@admin.register(ClientAddress)
class ClientAddressAdmin(admin.ModelAdmin):
    list_display = ('client', 'address_type', 'city', 'is_default')
    search_fields = ('client__company_name', 'city', 'street')
    autocomplete_fields = ('client',)


class DispatchItemInline(admin.TabularInline):
    model = DispatchItem
    extra = 1
    autocomplete_fields = ('stock_item',)


@admin.register(Dispatch)
class DispatchAdmin(admin.ModelAdmin):
    list_display = ('dispatch_code', 'client', 'dispatch_date', 'accounted')
    list_filter = ('dispatch_date', 'accounted')
    search_fields = ('dispatch_code', 'invoice_number', 'client__company_name')
    autocomplete_fields = ('client', 'shipping_address')
    inlines = [DispatchItemInline]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('client', 'shipping_address')


@admin.register(DispatchItem)
class DispatchItemAdmin(admin.ModelAdmin):
    list_display = ('dispatch', 'stock_item', 'quantity', 'unit')
    search_fields = ('stock_item__name', 'dispatch__dispatch_code')
    autocomplete_fields = ('dispatch', 'stock_item')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('dispatch', 'stock_item')


# ---------------- LEADS (original) ---------------- #

class LeadCallRecordInline(admin.TabularInline):
    model = LeadCallRecord
    extra = 0
    readonly_fields = ('created_at',)
    fields = (
        'call_date', 'contact_number', 'briefing',
        'lead_status', 'next_followup', 'follow_up_done',
        'forwarded_to', 'created_by', 'created_at'
    )


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = (
        'lead_id', 'party_name', 'sub_department', 'party_type', 'contact_person',
        'mobile_number', 'lead_status', 'next_followup', 'created_at'
    )
    list_filter = ('lead_status', 'party_type', 'sub_department', 'is_active')
    search_fields = ('lead_id', 'party_name', 'contact_person', 'mobile_number', 'email')
    readonly_fields = ('lead_id', 'created_at', 'updated_at')
    autocomplete_fields = ('sub_department',)
    inlines = [LeadCallRecordInline]

    fieldsets = (
        ('Lead Info', {
            'fields': ('lead_id', 'date_of_connect', 'lead_source', 'sub_department')
        }),
        ('Party Details', {
            'fields': ('party_type', 'party_name', 'location', 'contact_person', 'mobile_number', 'email')
        }),
        ('Status & Follow-up', {
            'fields': ('lead_status', 'remarks', 'next_followup', 'forwarded_to')
        }),
        ('Meta', {
            'fields': ('created_by', 'created_at', 'updated_at', 'is_active')
        }),
    )


@admin.register(LeadCallRecord)
class LeadCallRecordAdmin(admin.ModelAdmin):
    list_display = (
        'lead', 'call_date', 'contact_number', 'lead_status',
        'next_followup', 'follow_up_done', 'created_by'
    )
    list_filter = ('lead_status', 'follow_up_done', 'call_date')
    search_fields = ('lead__lead_id', 'lead__party_name', 'briefing')
    autocomplete_fields = ('lead',)
    readonly_fields = ('created_at',)


# ---------------- LEADS SUB-DEPT MODULE ---------------- #

class QuotationItemInline(admin.TabularInline):
    model = QuotationItem
    extra = 1
    fields = ('stock_item', 'quantity', 'rate', 'uom', 'application_area', 'description', 'is_active')
    autocomplete_fields = ('stock_item',)


class SampleRequisiteItemInline(admin.TabularInline):
    model = SampleRequisiteItem
    extra = 1
    fields = ('stock_item', 'quantity', 'uom', 'qty_sent', 'notes', 'is_active')
    autocomplete_fields = ('stock_item',)


class ApplicationSystemProductItemInline(admin.TabularInline):
    model = ApplicationSystemProductItem
    extra = 1
    fields = ('stock_item', 'product_name', 'hsn_code', 'rate', 'uom', 'quantity', 'is_active')
    autocomplete_fields = ('stock_item',)


class ApplicationFixedItemInline(admin.TabularInline):
    model = ApplicationFixedItem
    extra = 1
    fields = ('stock_item', 'product_name', 'hsn_code', 'rate', 'uom', 'quantity', 'is_active')
    autocomplete_fields = ('stock_item',)


class ApplicationSystemProductInline(admin.TabularInline):
    model = ApplicationSystemProduct
    extra = 0
    show_change_link = True
    fields = ('name', 'description', 'is_active')


@admin.register(LeadSubDepartment)
class LeadSubDepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active', 'created_at')
    search_fields = ('name', 'code')
    list_filter = ('is_active',)
    ordering = ('name',)


@admin.register(SubDeptStockItem)
class SubDeptStockItemAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'sub_department', 'hsn_code', 'rate', 'uom', 'warranty', 'is_active')
    list_filter = ('sub_department', 'uom', 'is_active')
    search_fields = ('product_name', 'hsn_code', 'warranty')
    ordering = ('sub_department', 'product_name')


@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ('quotation_no', 'lead', 'quotation_date', 'status', 'created_by', 'created_at')
    list_filter = ('status', 'lead__sub_department')
    search_fields = ('quotation_no', 'lead__party_name')
    ordering = ('-created_at',)
    readonly_fields = ('quotation_no', 'created_at', 'updated_at')
    inlines = [QuotationItemInline]
    autocomplete_fields = ('lead', 'created_by')


@admin.register(SampleRequisite)
class SampleRequisiteAdmin(admin.ModelAdmin):
    list_display = ('sr_no', 'lead', 'sr_date', 'status', 'sent_to_factory_at', 'created_by')
    list_filter = ('status', 'lead__sub_department')
    search_fields = ('sr_no', 'lead__party_name')
    ordering = ('-created_at',)
    readonly_fields = ('sr_no', 'created_at', 'updated_at')
    inlines = [SampleRequisiteItemInline]
    autocomplete_fields = ('lead', 'created_by')


@admin.register(ApplicationArea)
class ApplicationAreaAdmin(admin.ModelAdmin):
    list_display = ('name', 'sub_department', 'is_active')
    list_filter = ('sub_department', 'is_active')
    search_fields = ('name',)
    inlines = [ApplicationSystemProductInline, ApplicationFixedItemInline]
    autocomplete_fields = ('sub_department',)


@admin.register(ApplicationSystemProduct)
class ApplicationSystemProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'application_area', 'is_active')
    list_filter = ('application_area__sub_department', 'is_active')
    search_fields = ('name',)
    inlines = [ApplicationSystemProductItemInline]
    autocomplete_fields = ('application_area',)


@admin.register(ApplicationLead)
class ApplicationLeadAdmin(admin.ModelAdmin):
    list_display = ('lead', 'application_area', 'created_at')
    list_filter = ('application_area',)
    search_fields = ('lead__party_name',)
    filter_horizontal = ('selected_system_products',)
    autocomplete_fields = ('lead', 'application_area')
