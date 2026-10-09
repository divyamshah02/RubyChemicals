"""
UserDetail/hr_serializers.py
────────────────────────────
Serializers for the HR module: employee profiles, emergency contacts and leaves.
"""

import re

from rest_framework import serializers

from .models import EmergencyContact, EmployeeDetail, Leave, UniversalLeave, User

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

    class Meta:
        model = EmployeeDetail
        fields = [
            'id', 'user', 'user_code', 'user_name', 'email', 'role', 'active_user',
            'full_name', 'joining_date', 'department', 'position',
            'reporting_to', 'reporting_to_name',
            'current_address', 'permanent_address', 'personal_mobile',
            'aadhar_number', 'aadhar_file', 'pan_number', 'pan_file',
            'bank_name', 'bank_account_no', 'bank_branch', 'bank_ifsc', 'bank_proof_file',
            'photo',
            'office_mobile', 'device_details', 'imei_1', 'imei_2', 'sim_card_in_name_of',
            'emergency_contacts', 'missing_fields', 'is_complete',
            'updated_at',
        ]
        read_only_fields = ['id', 'updated_at']

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

    def validate_personal_mobile(self, value):
        return _clean_mobile(value, "Personal mobile number")

    def validate_office_mobile(self, value):
        return _clean_mobile(value, "Office mobile number")

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

    def validate_imei_1(self, value):
        value = (value or '').strip()
        if value and not IMEI_RE.match(value):
            raise serializers.ValidationError("IMEI must be 15 digits.")
        return value

    validate_imei_2 = validate_imei_1

    def validate_reporting_to(self, value):
        if value and self.instance and value.pk == self.instance.user_id:
            raise serializers.ValidationError("An employee cannot report to themselves.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        errors = {}
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
