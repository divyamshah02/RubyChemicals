"""
UserDetail/serializers.py
─────────────────────────
Changes vs original:
  • Added 'sales' role
  • Added 'leads_sub_department' and 'leads_sub_department_name' to user serializers
"""

from rest_framework import serializers
from .models import User, ActivityLog, Attendance

PERMISSION_FIELDS = [
    "is_super_admin",
    "can_stock_items",
    "can_vendor_management",
    "can_production",
    "can_dispatch",
    "can_client_management",
    "can_petty_cash",
    "can_leads",
    "can_hr",
]


class UserSerializer(serializers.ModelSerializer):
    leads_sub_department_name = serializers.CharField(
        source='leads_sub_department.name', read_only=True
    )
    reports_to_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "user_id",
            "name",
            "email",
            "role",
            "active_user",
            "created_at",
            "leads_sub_department",
            "leads_sub_department_name",
            "level",
            "reports_to",
            "reports_to_name",
        ] + PERMISSION_FIELDS

    def get_reports_to_name(self, obj):
        return obj.reports_to.name if obj.reports_to_id else None


class HierarchyValidationMixin:
    """Keeps `level` and `reports_to` consistent on create and update."""

    def validate(self, attrs):
        attrs = super().validate(attrs)
        instance = getattr(self, 'instance', None)

        level = attrs['level'] if 'level' in attrs else getattr(instance, 'level', None)
        role = attrs['role'] if 'role' in attrs else getattr(instance, 'role', None)
        is_super = (
            attrs['is_super_admin'] if 'is_super_admin' in attrs
            else getattr(instance, 'is_super_admin', False)
        )
        supervisor = (
            attrs['reports_to'] if 'reports_to' in attrs
            else getattr(instance, 'reports_to', None)
        )

        # The HR role always gets the HR page.
        if role == 'hr':
            attrs['can_hr'] = True

        # Admins see everything, so they never sit under a supervisor.
        if role == 'admin' or is_super:
            if supervisor is not None:
                attrs['reports_to'] = None
            supervisor = None

        if level is None:
            if supervisor is not None:
                attrs['reports_to'] = None
            if instance and instance.direct_reports.exists():
                raise serializers.ValidationError({
                    "level": "This user has people reporting to them. Reassign them before removing the level."
                })
            return attrs

        if supervisor is not None:
            if instance and supervisor.pk == instance.pk:
                raise serializers.ValidationError({"reports_to": "A user cannot report to themselves."})
            if supervisor.role == 'admin' or supervisor.is_super_admin:
                raise serializers.ValidationError({
                    "reports_to": "Admins already see everything. Choose an Office-level supervisor instead."
                })
            if not supervisor.active_user:
                raise serializers.ValidationError({"reports_to": "The selected supervisor is inactive."})
            if supervisor.level is None or supervisor.level >= level:
                raise serializers.ValidationError({
                    "reports_to": f"The supervisor must have a level lower than {level}."
                })

        if instance and instance.direct_reports.filter(level__lte=level).exists():
            raise serializers.ValidationError({
                "level": "People reporting to this user must stay at a higher level number than theirs."
            })
        return attrs


class CreateUserSerializer(HierarchyValidationMixin, serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "name", "email", "role", "password",
            "leads_sub_department", "level", "reports_to",
        ] + PERMISSION_FIELDS

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UpdateUserSerializer(HierarchyValidationMixin, serializers.ModelSerializer):
    """Used for PUT/PATCH — does NOT change password."""

    class Meta:
        model = User
        fields = [
            "name", "email", "role", "active_user",
            "leads_sub_department", "level", "reports_to",
        ] + PERMISSION_FIELDS

    def validate_email(self, value):
        qs = User.objects.filter(email__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()


class ChangePasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, min_length=6)


class ActivityLogSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = ActivityLog
        fields = "__all__"


class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = ["id", "date", "check_in_time", "check_out_time"]
