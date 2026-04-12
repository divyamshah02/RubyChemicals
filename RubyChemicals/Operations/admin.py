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


@admin.register(Dispatch)
class DispatchAdmin(admin.ModelAdmin):
    list_display = ("dispatch_date", "customer_name", "stock_item", "quantity", "created_by")
    list_filter = ("dispatch_date", "stock_item")
    search_fields = ("customer_name", "stock_item__name")
    ordering = ("-dispatch_date",)


@admin.register(ExpenseHead)
class ExpenseHeadAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    search_fields = ("name",)


@admin.register(PettyCash)
class PettyCashAdmin(admin.ModelAdmin):
    list_display = ("expense_date", "expense_head", "amount", "created_by")
    list_filter = ("expense_date", "expense_head")
    ordering = ("-expense_date",)
