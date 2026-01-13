from rest_framework import serializers
from .models import User, ActivityLog


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "user_id", "name", "email", "role", "active_user", "created_at"]


class CreateUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["name", "email", "role", "password"]

    def create(self, validated_data):
        user = User(
            name=validated_data["name"],
            email=validated_data["email"],
            role=validated_data["role"]
        )
        user.set_password(validated_data["password"])
        user.save()
        return user


class ActivityLogSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = ActivityLog
        fields = "__all__"
