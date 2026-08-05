"""
UserDetail/admin.py
───────────────────
Changes vs original:
  • Added 'sales' to role filter
  • Added 'leads_sub_department' to User fieldset (Leads Access section)
"""

from django.contrib import admin
from .models import User, ActivityLog


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "user_id", "name", "email", "role",
        "is_super_admin", "active_user",
        "leads_sub_department", "created_at",
    )
    list_filter = ("role", "active_user", "is_super_admin", "leads_sub_department")
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
        ("Leads Department Assignment", {
            "description": "Assign a sub-department for Sales / can_leads users.",
            "fields": ("leads_sub_department",),
        }),
        ("Timestamps", {
            "fields": ("created_at",),
        }),
    )
    readonly_fields = ("user_id", "created_at")
    autocomplete_fields = ("leads_sub_department",)


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("user", "action", "model_name", "record_id", "created_at")
    list_filter = ("action", "model_name")
    ordering = ("-created_at",)
