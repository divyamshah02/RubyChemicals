from rest_framework import serializers
from .models import User, ActivityLog

# All plugin permission fields — shared across serializers
PERMISSION_FIELDS = [
    "is_super_admin",
    "can_stock_items",
    "can_vendor_management",
    "can_production",
    "can_dispatch",
    "can_client_management",
    "can_petty_cash",
    "can_leads",
]


class UserSerializer(serializers.ModelSerializer):
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
        ] + PERMISSION_FIELDS


class CreateUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["name", "email", "role", "password"] + PERMISSION_FIELDS

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


class UpdateUserSerializer(serializers.ModelSerializer):
    """Used for PUT/PATCH — does NOT change password."""

    class Meta:
        model = User
        fields = ["name", "email", "role", "active_user"] + PERMISSION_FIELDS

    def validate_email(self, value):
        # Allow the same user to keep their email; block if another user has it
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
