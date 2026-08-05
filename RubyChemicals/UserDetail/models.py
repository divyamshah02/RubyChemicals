"""
UserDetail/models.py
────────────────────
Changes vs original:
  • Added 'sales' to ROLE_CHOICES (prefix SL)
  • Added 'leads_sub_department' FK to Operations.LeadSubDepartment
    (only relevant for 'sales' role users and users with can_leads access)
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
import random
import string


def generate_user_id(role):
    prefix = {
        'admin':      'AD',
        'accounts':   'AC',
        'factory':    'FC',
        'accountant': 'AN',
        'office':     'OF',
        'sales':      'SL',   # ← NEW
    }.get(role, 'US')

    while True:
        number = ''.join(random.choices(string.digits, k=6))
        uid = f"{prefix}{number}"
        if not User.objects.filter(user_id=uid).exists():
            return uid


class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin',      'Admin'),
        ('accounts',   'Accounts'),
        ('factory',    'Factory'),
        ('accountant', 'Accountant'),
        ('office',     'Office'),
        ('sales',      'Sales'),   # ← NEW
    ]

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    user_id = models.CharField(max_length=10, unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    active_user = models.BooleanField(default=True)

    # ── Super Admin overrides all plugin permissions ──────────────────────
    is_super_admin = models.BooleanField(
        default=False,
        help_text="Super Admin has access to every module regardless of individual permissions."
    )

    # ── Plugin-level permissions ──────────────────────────────────────────
    can_stock_items        = models.BooleanField(default=False, verbose_name="Stock Items")
    can_vendor_management  = models.BooleanField(default=False, verbose_name="Vendor Management")
    can_production         = models.BooleanField(default=False, verbose_name="Production")
    can_dispatch           = models.BooleanField(default=False, verbose_name="Dispatch")
    can_client_management  = models.BooleanField(default=False, verbose_name="Client Management")
    can_petty_cash         = models.BooleanField(default=False, verbose_name="Petty Cash")
    can_leads              = models.BooleanField(default=False, verbose_name="Leads")

    # ── Leads Sub-Department assignment ──────────────────────────────────
    # Set for 'sales' role users OR any user with can_leads=True
    # Nullable so existing users are unaffected
    leads_sub_department = models.ForeignKey(
        'Operations.LeadSubDepartment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_users',
        help_text="Sub-department this user belongs to for the Leads module (Sales / can_leads users only)."
    )

    REQUIRED_FIELDS = ['name', 'role']

    def has_plugin_access(self, permission_field: str) -> bool:
        if self.is_super_admin:
            return True
        return bool(getattr(self, permission_field, False))

    def save(self, *args, **kwargs):
        if not self.user_id:
            self.user_id = generate_user_id(self.role)
        if not self.username:
            self.username = self.email
        if not self.email:
            self.email = self.username
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.role})"


class ActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=255)
    model_name = models.CharField(max_length=100)
    record_id = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} - {self.model_name}"
