from django.contrib import admin
from .models import User, ActivityLog


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("user_id", "name", "email", "role", "active_user", "created_at")
    list_filter = ("role", "active_user")
    search_fields = ("name", "email", "user_id")
    ordering = ("-created_at",)


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("user", "action", "model_name", "record_id", "created_at")
    list_filter = ("action", "model_name")
    ordering = ("-created_at",)
