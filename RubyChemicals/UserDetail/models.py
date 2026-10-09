"""
UserDetail/models.py
────────────────────
Changes vs original:
  • Added 'sales' to ROLE_CHOICES (prefix SL)
  • Added 'leads_sub_department' FK to Operations.LeadSubDepartment
    (only relevant for 'sales' role users and users with can_leads access)
"""

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models
from django.utils import timezone
import os
import random
import string
import uuid


MAX_DOCUMENT_SIZE_MB = 5
ALLOWED_DOCUMENT_EXTENSIONS = ['pdf', 'jpg', 'jpeg', 'png', 'webp']


def employee_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"employees/{instance.user.user_id}/{uuid.uuid4().hex}{ext}"


def validate_document_size(file):
    if file.size > MAX_DOCUMENT_SIZE_MB * 1024 * 1024:
        raise ValidationError(f"File size must be {MAX_DOCUMENT_SIZE_MB} MB or less.")


def generate_user_id(role):
    prefix = {
        'admin':      'AD',
        'accounts':   'AC',
        'factory':    'FC',
        'accountant': 'AN',
        'office':     'OF',
        'sales':      'SL',
        'hr':         'HR',
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
        ('sales',      'Sales'),
        ('hr',         'HR'),
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
    can_hr                 = models.BooleanField(default=False, verbose_name="HR")


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

    # ── Hierarchy ────────────────────────────────────────────────────────
    # 1 = top. A supervisor (role office + Leads access) can see leads of
    # every user whose level number is greater than theirs.
    level = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="Hierarchy level (1 = top). Users with a higher level number are below this user."
    )

    # Direct supervisor. Only that supervisor (and their own supervisors up the
    # chain) see this user's leads. When empty, every user with a lower level
    # number (higher rank) can see them.
    reports_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='direct_reports',
        help_text="Direct supervisor (must have a lower level number). Leave empty to be visible to all upper levels."
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
        EmployeeDetail.objects.get_or_create(user=self, defaults={'full_name': self.name})

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


class Attendance(models.Model):
    """Simple daily check-in / check-out log for a user (one record per user per day)."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='attendance_records'
    )
    date = models.DateField(default=timezone.localdate)
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-date', '-created_at']
        unique_together = ('user', 'date')

    def __str__(self):
        return f"{self.user.name} - {self.date}"


def _document_field(help_text=""):
    return models.FileField(
        upload_to=employee_upload_path,
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(ALLOWED_DOCUMENT_EXTENSIONS),
            validate_document_size,
        ],
        help_text=help_text,
    )


class EmployeeDetail(models.Model):
    """HR profile. Exactly one per user, created automatically with the user."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee_detail')

    full_name = models.CharField(max_length=255, blank=True)
    joining_date = models.DateField(null=True, blank=True)
    department = models.CharField(max_length=100, blank=True)
    position = models.CharField(max_length=100, blank=True)
    # Employment reporting line (HR record only). Separate from User.reports_to,
    # which drives lead visibility.
    reporting_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employee_reports',
    )

    current_address = models.TextField(blank=True)
    permanent_address = models.TextField(blank=True)
    personal_mobile = models.CharField(max_length=15, blank=True)

    aadhar_number = models.CharField(max_length=12, blank=True)
    aadhar_file = _document_field("Aadhar card (PDF/Image)")
    pan_number = models.CharField(max_length=10, blank=True)
    pan_file = _document_field("PAN card (PDF/Image)")

    bank_name = models.CharField(max_length=150, blank=True)
    bank_account_no = models.CharField(max_length=30, blank=True)
    bank_branch = models.CharField(max_length=150, blank=True)
    bank_ifsc = models.CharField(max_length=11, blank=True)
    bank_proof_file = _document_field("Cancelled cheque / passbook (PDF/Image)")

    photo = _document_field("Employee photo (PDF/Image)")

    office_mobile = models.CharField(max_length=15, blank=True)
    device_details = models.CharField(max_length=255, blank=True, help_text="Office mobile make / model")
    imei_1 = models.CharField(max_length=20, blank=True)
    imei_2 = models.CharField(max_length=20, blank=True)
    sim_card_in_name_of = models.CharField(max_length=150, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Employee: {self.full_name or self.user.name}"


class EmergencyContact(models.Model):
    employee = models.ForeignKey(
        EmployeeDetail,
        on_delete=models.CASCADE,
        related_name='emergency_contacts',
    )
    name = models.CharField(max_length=150)
    relation = models.CharField(max_length=100)
    mobile = models.CharField(max_length=15)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.name} ({self.relation})"


class UniversalLeave(models.Model):
    """A day off that applies to every employee (holiday, company shutdown...)."""

    date = models.DateField(unique=True)
    title = models.CharField(max_length=150)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['date']

    def __str__(self):
        return f"{self.date} - {self.title}"


class Leave(models.Model):
    """A leave granted to one employee for one day. HR adds these manually."""

    LEAVE_TYPE_CHOICES = [
        ('casual', 'Casual'),
        ('sick',   'Sick'),
        ('earned', 'Earned / Paid'),
        ('unpaid', 'Unpaid'),
        ('other',  'Other'),
    ]
    DAY_TYPE_CHOICES = [
        ('full', 'Full Day'),
        ('half', 'Half Day'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leaves')
    date = models.DateField()
    leave_type = models.CharField(max_length=10, choices=LEAVE_TYPE_CHOICES, default='casual')
    day_type = models.CharField(max_length=4, choices=DAY_TYPE_CHOICES, default='full')
    reason = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-date']
        unique_together = ('user', 'date')

    def __str__(self):
        return f"{self.user.name} - {self.date} ({self.day_type})"
