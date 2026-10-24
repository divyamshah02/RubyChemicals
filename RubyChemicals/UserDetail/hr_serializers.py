"""
UserDetail/hr_serializers.py
────────────────────────────
Serializers for the HR module: employee profiles, emergency contacts and leaves.
"""

import re

from rest_framework import serializers

from django.db.models import Q
from django.utils import timezone

from .models import (
    Asset,
    AssetAssignment,
    EmergencyContact,
    EmployeeDetail,
    Leave,
    LeaveApplication,
    Payroll,
    PayrollLeaveLine,
    Reimbursement,
    UniversalLeave,
    User,
)

# Documents HR must upload before a profile can be saved.
# Remove an entry here to make that document optional.
REQUIRED_DOCUMENTS = {
    'aadhar_file':     'Aadhar document',
    'pan_file':        'PAN document',
    'bank_proof_file': 'Bank proof document',
    'photo':           'Photo',
}

# Fields that must be filled for a profile to count as complete.
COMPLETENESS_FIELDS = {
    'full_name':         'Name',
    'joining_date':      'Joining date',
    'department':        'Department',
    'position':          'Position',
    'current_address':   'Current address',
    'permanent_address': 'Permanent address',
    'personal_mobile':   'Personal mobile',
    'aadhar_number':     'Aadhar number',
    'pan_number':        'PAN number',
    'bank_name':         'Bank name',
    'bank_account_no':   'Account number',
    'bank_branch':       'Branch name',
    'bank_ifsc':         'IFSC',
}

MOBILE_RE = re.compile(r'^\+?\d{10,14}$')
AADHAR_RE = re.compile(r'^\d{12}$')
PAN_RE = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]$')
IFSC_RE = re.compile(r'^[A-Z]{4}0[A-Z0-9]{6}$')
IMEI_RE = re.compile(r'^\d{15}$')
EMPLOYEE_CODE_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9\-_/]*$')


def _clean_mobile(value, label):
    value = (value or '').replace(' ', '').replace('-', '')
    if value and not MOBILE_RE.match(value):
        raise serializers.ValidationError(f"{label} must be 10 to 14 digits.")
    return value


class EmergencyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = ['id', 'name', 'relation', 'mobile']
        read_only_fields = ['id']

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Name is required.")
        return value

    def validate_relation(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Relation is required.")
        return value

    def validate_mobile(self, value):
        value = _clean_mobile(value, "Mobile number")
        if not value:
            raise serializers.ValidationError("Mobile number is required.")
        return value


class EmployeeDetailSerializer(serializers.ModelSerializer):
    user = serializers.IntegerField(source='user_id', read_only=True)
    user_code = serializers.CharField(source='user.user_id', read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    role = serializers.CharField(source='user.role', read_only=True)
    active_user = serializers.BooleanField(source='user.active_user', read_only=True)
    reporting_to_name = serializers.SerializerMethodField()
    emergency_contacts = EmergencyContactSerializer(many=True, read_only=True)
    missing_fields = serializers.SerializerMethodField()
    is_complete = serializers.SerializerMethodField()
    # Edited through the dedicated leave-quota endpoint, never through the profile form.
    monthly_casual_leaves = serializers.DecimalField(
        max_digits=4, decimal_places=1, read_only=True, coerce_to_string=False)
    monthly_sick_leaves = serializers.DecimalField(
        max_digits=4, decimal_places=1, read_only=True, coerce_to_string=False)

    # Salary amounts are sent as numbers so the UI can add them up without parsing strings.
    tds_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=0, required=False, coerce_to_string=False)
    basic_pay = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=0, required=False, coerce_to_string=False)
    da = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=0, required=False, coerce_to_string=False)
    hra = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=0, required=False, coerce_to_string=False)
    lta = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=0, required=False, coerce_to_string=False)
    epf = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=0, required=False, coerce_to_string=False)
    gratuity = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=0, required=False, coerce_to_string=False)
    esic = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=0, required=False, coerce_to_string=False)
    total_salary = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True, coerce_to_string=False)

    exit_intent_display = serializers.CharField(source='get_exit_intent_display', read_only=True)
    exited_by_name = serializers.SerializerMethodField()
    assets = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeDetail
        fields = [
            'id', 'user', 'user_code', 'user_name', 'email', 'role', 'active_user',
            'full_name', 'employee_code', 'joining_date', 'department', 'position',
            'reporting_to', 'reporting_to_name',
            'marital_status', 'date_of_birth', 'anniversary_date', 'blood_group',
            'mother_name', 'father_name', 'spouse_name',
            'current_address', 'permanent_address', 'personal_mobile',
            'aadhar_number', 'aadhar_file', 'pan_number', 'pan_file',
            'bank_name', 'bank_account_no', 'bank_branch', 'bank_ifsc', 'bank_proof_file',
            'photo', 'cv_file',
            'assets',
            'tds_applicable', 'tds_amount',
            'basic_pay', 'da', 'hra', 'lta', 'epf', 'gratuity', 'esic', 'total_salary',
            'is_exited', 'last_working_day', 'exit_intent', 'exit_intent_display',
            'exit_remarks', 'exited_at', 'exited_by_name',
            'emergency_contacts', 'missing_fields', 'is_complete',
            'monthly_casual_leaves', 'monthly_sick_leaves',
            'updated_at',
        ]
        # Exit details are written only through the exit endpoint.
        read_only_fields = [
            'id', 'updated_at',
            'is_exited', 'last_working_day', 'exit_intent', 'exit_remarks', 'exited_at',
        ]

    def get_exited_by_name(self, obj):
        return obj.exited_by.name if obj.exited_by_id else None

    def get_assets(self, obj):
        """Assets the employee holds right now (uses the prefetch cache)."""
        held = sorted(obj.user.held_assets.all(), key=lambda a: a.code_number)
        return AssetSerializer(held, many=True).data

    def get_reporting_to_name(self, obj):
        return obj.reporting_to.name if obj.reporting_to_id else None

    def get_missing_fields(self, obj):
        missing = [label for field, label in COMPLETENESS_FIELDS.items() if not getattr(obj, field)]
        missing += [label for field, label in REQUIRED_DOCUMENTS.items() if not getattr(obj, field)]
        # Use the prefetch cache when available.
        if not len(obj.emergency_contacts.all()):
            missing.append('Emergency contact')
        return missing

    def get_is_complete(self, obj):
        return not self.get_missing_fields(obj)

    # ── Field validation ─────────────────────────────────────────────────

    def validate_employee_code(self, value):
        value = (value or '').strip()
        if not value:
            return value
        if not EMPLOYEE_CODE_RE.match(value):
            raise serializers.ValidationError(
                "Employee code can only contain letters, numbers, hyphen, underscore or slash.")
        duplicates = EmployeeDetail.objects.filter(employee_code__iexact=value)
        if self.instance:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError("This employee code is already used by another employee.")
        return value

    def validate_personal_mobile(self, value):
        return _clean_mobile(value, "Personal mobile number")

    def validate_aadhar_number(self, value):
        value = (value or '').replace(' ', '')
        if value and not AADHAR_RE.match(value):
            raise serializers.ValidationError("Aadhar number must be exactly 12 digits.")
        return value

    def validate_pan_number(self, value):
        value = (value or '').strip().upper()
        if value and not PAN_RE.match(value):
            raise serializers.ValidationError("PAN must look like ABCDE1234F.")
        return value

    def validate_bank_ifsc(self, value):
        value = (value or '').strip().upper()
        if value and not IFSC_RE.match(value):
            raise serializers.ValidationError("IFSC must look like HDFC0001234.")
        return value

    def validate_reporting_to(self, value):
        if value and self.instance and value.pk == self.instance.user_id:
            raise serializers.ValidationError("An employee cannot report to themselves.")
        return value

    def validate_date_of_birth(self, value):
        if value and value >= timezone.localdate():
            raise serializers.ValidationError("Date of birth must be in the past.")
        return value

    def _effective(self, attrs, field):
        """New value if it is being changed, otherwise the stored one."""
        if field in attrs:
            return attrs[field]
        return getattr(self.instance, field, None) if self.instance else None

    def validate(self, attrs):
        attrs = super().validate(attrs)
        errors = {}

        if self._effective(attrs, 'tds_applicable') and not self._effective(attrs, 'tds_amount'):
            errors['tds_amount'] = "Enter the monthly TDS amount when TDS is applicable."

        dob = self._effective(attrs, 'date_of_birth')
        anniversary = self._effective(attrs, 'anniversary_date')
        if dob and anniversary and anniversary <= dob:
            errors['anniversary_date'] = "Anniversary must be after the date of birth."

        for field, label in REQUIRED_DOCUMENTS.items():
            uploaded = attrs.get(field)
            existing = getattr(self.instance, field, None) if self.instance else None
            if not uploaded and not existing:
                errors[field] = f"{label} is required (PDF or image)."
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class LeaveSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.name', read_only=True)
    user_code = serializers.CharField(source='user.user_id', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    leave_type_display = serializers.CharField(source='get_leave_type_display', read_only=True)

    class Meta:
        model = Leave
        fields = [
            'id', 'user', 'user_name', 'user_code', 'date',
            'leave_type', 'leave_type_display', 'day_type', 'reason',
            'created_by_name', 'created_at',
        ]

    def get_created_by_name(self, obj):
        return obj.created_by.name if obj.created_by_id else None


class UniversalLeaveSerializer(serializers.ModelSerializer):
    class Meta:
        model = UniversalLeave
        fields = ['id', 'date', 'title', 'created_at']


class LeaveApplicationSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.name', read_only=True)
    user_code = serializers.CharField(source='user.user_id', read_only=True)
    leave_type_display = serializers.CharField(source='get_leave_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    days = serializers.DecimalField(max_digits=5, decimal_places=1, read_only=True, coerce_to_string=False)
    reviewed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = LeaveApplication
        fields = [
            'id', 'user', 'user_name', 'user_code',
            'from_date', 'to_date', 'leave_type', 'leave_type_display',
            'day_type', 'reason', 'days', 'status', 'status_display',
            'reviewed_by_name', 'reviewed_at', 'review_note', 'created_at',
        ]

    def get_reviewed_by_name(self, obj):
        return obj.reviewed_by.name if obj.reviewed_by_id else None


class ReimbursementSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.name', read_only=True)
    user_code = serializers.CharField(source='user.user_id', read_only=True)
    receipt_url = serializers.SerializerMethodField()
    is_paid = serializers.SerializerMethodField()
    payroll_period = serializers.SerializerMethodField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, coerce_to_string=False)

    class Meta:
        model = Reimbursement
        fields = [
            'id', 'user', 'user_name', 'user_code', 'expense_date', 'description', 'amount',
            'receipt', 'receipt_url', 'payroll', 'is_paid', 'payroll_period', 'created_at',
        ]
        read_only_fields = ['id', 'user', 'payroll', 'created_at']
        extra_kwargs = {'receipt': {'write_only': True}}

    def get_receipt_url(self, obj):
        if not obj.receipt:
            return None
        request = self.context.get('request')
        return request.build_absolute_uri(obj.receipt.url) if request else obj.receipt.url

    def get_is_paid(self, obj):
        return bool(obj.payroll_id and obj.payroll.status == 'paid')

    def get_payroll_period(self, obj):
        return f"{obj.payroll.year}-{obj.payroll.month:02d}" if obj.payroll_id else None

    def validate_description(self, value):
        value = (value or '').strip()
        if len(value) < 3:
            raise serializers.ValidationError("Describe what the expense was for.")
        return value

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value

    def validate_expense_date(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError("Expense date cannot be in the future.")
        return value


class PayrollLeaveLineSerializer(serializers.ModelSerializer):
    leave_type_display = serializers.SerializerMethodField()
    days = serializers.DecimalField(max_digits=3, decimal_places=1, coerce_to_string=False)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, coerce_to_string=False)

    class Meta:
        model = PayrollLeaveLine
        fields = ['id', 'leave', 'date', 'leave_type', 'leave_type_display', 'day_type', 'days',
                  'reason', 'deduct', 'amount']

    def get_leave_type_display(self, obj):
        return dict(Leave.LEAVE_TYPE_CHOICES).get(obj.leave_type, obj.leave_type)


class PayrollSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.name', read_only=True)
    user_code = serializers.CharField(source='user.user_id', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    generated_by_name = serializers.SerializerMethodField()
    leave_lines = PayrollLeaveLineSerializer(many=True, read_only=True)
    reimbursements = ReimbursementSerializer(many=True, read_only=True)

    class Meta:
        model = Payroll
        fields = [
            'id', 'user', 'user_name', 'user_code', 'year', 'month',
            'basic_pay', 'da', 'hra', 'lta', 'epf', 'gratuity', 'esic', 'total_salary',
            'per_day_rate', 'leave_days_deducted', 'leave_deduction',
            'tds_applicable', 'tds_deducted', 'salary_for_month',
            'reimbursement_total', 'adjustment_amount', 'adjustment_note', 'net_payable',
            'status', 'status_display', 'paid_on', 'notes',
            'generated_by_name', 'generated_at', 'leave_lines', 'reimbursements',
        ]
        read_only_fields = fields

    def get_generated_by_name(self, obj):
        return obj.generated_by.name if obj.generated_by_id else None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for key in (
            'basic_pay', 'da', 'hra', 'lta', 'epf', 'gratuity', 'esic', 'total_salary',
            'per_day_rate', 'leave_days_deducted', 'leave_deduction', 'tds_deducted',
            'salary_for_month', 'reimbursement_total', 'adjustment_amount', 'net_payable',
        ):
            data[key] = float(data[key])
        return data


ASSET_TAG_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9\-_./ ]{2,49}$')


class AssetSerializer(serializers.ModelSerializer):
    asset_code = serializers.CharField(read_only=True)
    type_display = serializers.SerializerMethodField()
    identifier_label = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    assigned_to_name = serializers.SerializerMethodField()
    assigned_to_code = serializers.SerializerMethodField()

    class Meta:
        model = Asset
        fields = [
            'id', 'code_number', 'asset_code', 'asset_type', 'type_display', 'type_label', 'name',
            'unique_identifier', 'identifier_label', 'secondary_identifier', 'registered_name', 'notes',
            'status', 'status_display', 'assigned_to', 'assigned_to_name', 'assigned_to_code',
            'assigned_on', 'created_at',
        ]
        read_only_fields = [
            'id', 'code_number', 'status', 'assigned_to', 'assigned_on', 'created_at',
        ]

    def get_type_display(self, obj):
        if obj.asset_type == Asset.TYPE_OTHER and obj.type_label:
            return obj.type_label
        return obj.get_asset_type_display()

    def get_identifier_label(self, obj):
        return Asset.IDENTIFIER_LABELS.get(obj.asset_type, 'Identifier')

    def get_assigned_to_name(self, obj):
        return obj.assigned_to.name if obj.assigned_to_id else None

    def get_assigned_to_code(self, obj):
        return obj.assigned_to.user_id if obj.assigned_to_id else None

    def validate_asset_type(self, value):
        if self.instance and value != self.instance.asset_type:
            raise serializers.ValidationError("The type of an existing asset cannot be changed.")
        return value

    def _taken_by(self, value):
        clash = Asset.objects.filter(
            Q(unique_identifier__iexact=value) | Q(secondary_identifier__iexact=value))
        if self.instance:
            clash = clash.exclude(pk=self.instance.pk)
        return clash.first()

    def validate(self, attrs):
        creating = self.instance is None
        asset_type = attrs.get('asset_type') or (self.instance.asset_type if self.instance else None)
        if not asset_type:
            raise serializers.ValidationError({'asset_type': "Choose the asset type."})

        def value_of(field):
            if field in attrs:
                return (attrs[field] or '').strip()
            return getattr(self.instance, field, '') if self.instance else ''

        for field in ('name', 'type_label', 'registered_name', 'notes'):
            if field in attrs:
                attrs[field] = (attrs[field] or '').strip()

        errors = {}

        if creating or 'unique_identifier' in attrs:
            identifier = value_of('unique_identifier')
            label = Asset.IDENTIFIER_LABELS[asset_type]
            if asset_type == Asset.TYPE_MOBILE:
                if not IMEI_RE.match(identifier):
                    errors['unique_identifier'] = "IMEI must be exactly 15 digits."
            elif asset_type == Asset.TYPE_SIM:
                identifier = identifier.replace(' ', '').replace('-', '')
                if not MOBILE_RE.match(identifier):
                    errors['unique_identifier'] = "SIM number must be 10 to 14 digits."
            else:
                identifier = identifier.upper()
                if not ASSET_TAG_RE.match(identifier):
                    errors['unique_identifier'] = f"{label} must be 3 to 50 letters, numbers or - _ . /"
            if 'unique_identifier' not in errors:
                clash = self._taken_by(identifier)
                if clash:
                    errors['unique_identifier'] = f"{clash.asset_code} already uses this number."
                attrs['unique_identifier'] = identifier

        if asset_type == Asset.TYPE_MOBILE:
            second = value_of('secondary_identifier')
            if second:
                if not IMEI_RE.match(second):
                    errors['secondary_identifier'] = "IMEI 2 must be exactly 15 digits."
                elif second == attrs.get('unique_identifier', value_of('unique_identifier')):
                    errors['secondary_identifier'] = "IMEI 2 must differ from IMEI 1."
                else:
                    clash = self._taken_by(second)
                    if clash:
                        errors['secondary_identifier'] = f"{clash.asset_code} already uses this number."
            attrs['secondary_identifier'] = second
        else:
            attrs['secondary_identifier'] = ''

        if asset_type == Asset.TYPE_OTHER:
            if not value_of('type_label'):
                errors['type_label'] = "Say what this asset is (for example Monitor)."
        else:
            attrs['type_label'] = ''

        if asset_type != Asset.TYPE_SIM:
            attrs['registered_name'] = ''

        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class AssetAssignmentSerializer(serializers.ModelSerializer):
    asset_code = serializers.CharField(source='asset.asset_code', read_only=True)
    asset_type = serializers.CharField(source='asset.asset_type', read_only=True)
    asset_type_display = serializers.SerializerMethodField()
    asset_name = serializers.CharField(source='asset.name', read_only=True)
    unique_identifier = serializers.CharField(source='asset.unique_identifier', read_only=True)
    employee_name = serializers.SerializerMethodField()
    employee_code = serializers.SerializerMethodField()
    end_reason_display = serializers.CharField(source='get_end_reason_display', read_only=True)
    assigned_by_name = serializers.SerializerMethodField()
    ended_by_name = serializers.SerializerMethodField()
    days_held = serializers.SerializerMethodField()

    class Meta:
        model = AssetAssignment
        fields = [
            'id', 'asset', 'asset_code', 'asset_type', 'asset_type_display', 'asset_name',
            'unique_identifier', 'employee', 'employee_name', 'employee_code',
            'assigned_on', 'returned_on', 'end_reason', 'end_reason_display',
            'assign_note', 'return_note', 'assigned_by_name', 'ended_by_name', 'days_held',
        ]
        read_only_fields = fields

    def get_asset_type_display(self, obj):
        if obj.asset.asset_type == Asset.TYPE_OTHER and obj.asset.type_label:
            return obj.asset.type_label
        return obj.asset.get_asset_type_display()

    def get_employee_name(self, obj):
        return obj.employee_name or (obj.employee.name if obj.employee_id else '')

    def get_employee_code(self, obj):
        return obj.employee.user_id if obj.employee_id else None

    def get_assigned_by_name(self, obj):
        return obj.assigned_by.name if obj.assigned_by_id else None

    def get_ended_by_name(self, obj):
        return obj.ended_by.name if obj.ended_by_id else None

    def get_days_held(self, obj):
        end = obj.returned_on or timezone.localdate()
        return (end - obj.assigned_on).days
