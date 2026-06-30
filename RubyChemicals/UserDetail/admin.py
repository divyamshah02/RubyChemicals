from django.contrib import admin
from .models import User, ActivityLog


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "user_id", "name", "email", "role",
        "is_super_admin", "active_user", "created_at",
    )
    list_filter = ("role", "active_user", "is_super_admin")
    search_fields = ("name", "email", "user_id")
    ordering = ("-created_at",)

    fieldsets = (
        ("Basic Info", {
            "fields": ("user_id", "name", "email", "role", "active_user", "password"),
        }),
        ("Access Control", {
            "fields": (
                "is_super_admin",
                "can_stock_items",
                "can_vendor_management",
                "can_production",
                "can_dispatch",
                "can_client_management",
                "can_petty_cash",
                "can_leads",
            ),
        }),
        ("Timestamps", {
            "fields": ("created_at",),
        }),
    )
    readonly_fields = ("user_id", "created_at")


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("user", "action", "model_name", "record_id", "created_at")
    list_filter = ("action", "model_name")
    ordering = ("-created_at",)
