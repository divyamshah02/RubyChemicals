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
    list_display = ('cash_account', 'expense_head', 'amount', 'transaction_type', 'expense_date')
    list_filter = ('transaction_type', 'expense_date')
    search_fields = ('expense_head__name',)
    autocomplete_fields = ('cash_account', 'expense_head')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('cash_account', 'expense_head')


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