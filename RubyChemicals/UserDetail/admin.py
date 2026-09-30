"""
UserDetail/admin.py
───────────────────
Changes vs original:
  • Added 'sales' to role filter
  • Added 'leads_sub_department' to User fieldset (Leads Access section)
"""

from django.contrib import admin
from .models import User, ActivityLog
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import AdminPasswordChangeForm
from django.urls import path
from django.shortcuts import get_object_or_404, redirect, render

@admin.register(User)
class UserAdmin(BaseUserAdmin):

    list_display = (
        "user_id",
        "name",
        "email",
        "username",
        "role",
        "is_super_admin",
        "active_user",
        "leads_sub_department",
        "created_at",
    )

    list_filter = (
        "role",
        "active_user",
        "is_super_admin",
        "leads_sub_department",
    )

    search_fields = (
        "name",
        "email",
        "user_id",
    )

    ordering = ("-created_at",)

    readonly_fields = (
        "user_id",
        "created_at",
    )

    autocomplete_fields = ("leads_sub_department",)

    fieldsets = (
        ("Basic Info", {
            "fields": (
                "user_id",
                "username",
                "name",
                "email",
                "role",
                "active_user",
            ),
        }),

        ("Password", {
            "fields": ("password",),
            "description": (
                "Passwords are not stored in plain text. "
                "Use the 'Change Password' button below."
            ),
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

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "name",
                    "role",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    def get_urls(self):
        urls = super().get_urls()

        custom_urls = [
            path(
                "<int:user_id>/change-password/",
                self.admin_site.admin_view(self.change_password_view),
                name="custom_user_change_password",
            ),
        ]

        return custom_urls + urls

    def change_password_view(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)

        if request.method == "POST":
            form = AdminPasswordChangeForm(user, request.POST)

            if form.is_valid():
                form.save()
                self.message_user(request, "Password changed successfully.")
                return redirect(
                    f"/admin/{user._meta.app_label}/{user._meta.model_name}/{user.pk}/change/"
                )
        else:
            form = AdminPasswordChangeForm(user)

        context = {
            "title": f"Change password: {user}",
            "form": form,
            "opts": self.model._meta,
            "original": user,
        }

        return render(
            request,
            "admin/auth/user/change_password.html",
            context,
        )

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("user", "action", "model_name", "record_id", "created_at")
    list_filter = ("action", "model_name")
    ordering = ("-created_at",)
