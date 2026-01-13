from rest_framework import viewsets, status
from rest_framework.response import Response
from django.contrib.auth import authenticate, login, logout
from .models import User, ActivityLog
from .serializers import UserSerializer, CreateUserSerializer
from utils.decorators import handle_exceptions, check_authentication


class LoginViewSet(viewsets.ViewSet):

    @handle_exceptions
    def create(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        print(email, password)

        if not email or not password:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Email and password are required"
            }, status=400)

        user = authenticate(request, username=email, password=password)

        if not user or not user.active_user:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Invalid credentials"
            }, status=401)

        login(request, user)

        ActivityLog.objects.create(
            user=user,
            action="LOGIN",
            model_name="User",
            record_id=user.user_id,
            description="User logged in"
        )

        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": UserSerializer(user).data,
            "error": None
        }, status=200)


class LogoutViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication
    def create(self, request):

        ActivityLog.objects.create(
            user=request.user,
            action="LOGOUT",
            model_name="User",
            record_id=request.user.user_id,
            description="User logged out"
        )

        logout(request)

        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": True,
            "error": None
        }, status=200)


class UserViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication(required_role="admin")
    def create(self, request):
        serializer = CreateUserSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": serializer.errors
            }, status=400)

        user = serializer.save()

        ActivityLog.objects.create(
            user=request.user,
            action="CREATE",
            model_name="User",
            record_id=user.user_id,
            description=f"Created user {user.email}"
        )

        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": UserSerializer(user).data,
            "error": None
        }, status=201)

    @handle_exceptions
    @check_authentication(required_role="admin")
    def list(self, request):
        users = User.objects.all().order_by("-created_at")
        data = UserSerializer(users, many=True).data

        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": data,
            "error": None
        }, status=200)



class MeViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication
    def list(self, request):
        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": UserSerializer(request.user).data,
            "error": None
        }, status=200)


class ActivityLogViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication(required_role="admin")
    def list(self, request):
        logs = ActivityLog.objects.all().order_by("-created_at")[:200]

        data = [{
            "user": log.user.name if log.user else None,
            "action": log.action,
            "model": log.model_name,
            "record_id": log.record_id,
            "description": log.description,
            "created_at": log.created_at
        } for log in logs]

        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": data,
            "error": None
        }, status=200)
