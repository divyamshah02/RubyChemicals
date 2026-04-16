from django.contrib import admin
from .models import *

@admin.register(StockGroup)
class StockGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    search_fields = ("name",)
    list_filter = ("is_active",)
    ordering = ("name",)


@admin.register(StockItem)
class StockItemAdmin(admin.ModelAdmin):
    list_display = ("name", "group", "unit", "current_quantity", "rate", "is_active")
    list_filter = ("group", "unit", "is_active")
    search_fields = ("name",)
    ordering = ("name",)
    readonly_fields = ("current_quantity",)


@admin.register(StockInward)
class StockInwardAdmin(admin.ModelAdmin):
    list_display = ("date", "stock_item", "quantity", "created_by", "created_at")
    list_filter = ("date", "stock_item")
    search_fields = ("stock_item__name",)
    ordering = ("-date",)


@admin.register(StockAdjustment)
class StockAdjustmentAdmin(admin.ModelAdmin):
    list_display = ("date", "stock_item", "adjustment_type", "quantity", "reason", "created_by")
    list_filter = ("adjustment_type", "date", "stock_item")
    search_fields = ("stock_item__name", "reason")
    ordering = ("-date",)


class ProductionBatchInline(admin.TabularInline):
    model = ProductionBatch
    extra = 0


@admin.register(ProductionCard)
class ProductionCardAdmin(admin.ModelAdmin):
    list_display = ("production_code", "production_date", "total_output_quantity", "unit", "created_by")
    list_filter = ("production_date",)
    search_fields = ("production_code",)
    ordering = ("-production_date",)
    inlines = [ProductionBatchInline]


@admin.register(ProductionBatch)
class ProductionBatchAdmin(admin.ModelAdmin):
    list_display = ("batch_code", "production_card", "product", "output_quantity", "loss_quantity", "created_by")
    list_filter = ("production_card__production_date", "product")
    search_fields = ("batch_code", "product__name")
    ordering = ("-created_at",)


class ProductionConsumptionInline(admin.TabularInline):
    model = ProductionConsumption
    extra = 0


class DispatchItemInline(admin.TabularInline):
    model = DispatchItem
    extra = 0
    fields = ('stock_item', 'quantity', 'unit')


@admin.register(Dispatch)
class DispatchAdmin(admin.ModelAdmin):
    list_display = ("dispatch_code", "dispatch_date", "client", "vehicle_number", "created_by")
    list_filter = ("dispatch_date", "vehicle_type")
    search_fields = ("dispatch_code", "client__company_name", "vehicle_number")
    ordering = ("-dispatch_date",)
    readonly_fields = ("dispatch_code",)
    inlines = [DispatchItemInline]


@admin.register(DispatchItem)
class DispatchItemAdmin(admin.ModelAdmin):
    list_display = ("dispatch", "stock_item", "quantity", "unit")
    list_filter = ("dispatch__dispatch_date", "stock_item")
    search_fields = ("dispatch__dispatch_code", "stock_item__name")
    ordering = ("-dispatch__dispatch_date",)


@admin.register(ExpenseHead)
class ExpenseHeadAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    search_fields = ("name",)
    list_filter = ("is_active",)


@admin.register(PettyCashAccount)
class PettyCashAccountAdmin(admin.ModelAdmin):
    list_display = ("get_cash_type_display", "current_balance", "credit_balance", "updated_at")
    readonly_fields = ("current_balance", "credit_balance", "created_at", "updated_at")
    fields = ("cash_type", "current_balance", "credit_balance", "created_at", "updated_at")
    
    def get_cash_type_display(self, obj):
        return obj.get_cash_type_display()
    get_cash_type_display.short_description = "Cash Type"


@admin.register(PettyCash)
class PettyCashAdmin(admin.ModelAdmin):
    list_display = ("cash_account", "expense_date", "expense_head", "transaction_type", "amount", "created_by")
    list_filter = ("expense_date", "cash_account__cash_type", "transaction_type", "expense_head")
    search_fields = ("expense_head__name",)
    readonly_fields = ("created_at", "created_by")
    ordering = ("-expense_date",)
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

