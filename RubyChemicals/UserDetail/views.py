from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponse, JsonResponse
from .models import User, ActivityLog
from .serializers import (
    UserSerializer,
    CreateUserSerializer,
    UpdateUserSerializer,
    ChangePasswordSerializer,
    ActivityLogSerializer,
)
from utils.decorators import handle_exceptions, check_authentication


class LoginViewSet(viewsets.ViewSet):

    @handle_exceptions
    def create(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

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

    @handle_exceptions
    @check_authentication(required_role="admin")
    def list(self, request):
        """Check admin login status"""
        user = request.user
        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": {
                "user_id": user.user_id,
                "name": user.name,
                "role": user.role,
                "email": user.email,
                "logged_in": True
            },
            "error": None
        }, status=status.HTTP_200_OK)


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
        user = request.user
        logout(request)
        # Determine the landing page for this user:
        # - 'accounts' role and super-admins go to the dashboard
        # - all other roles go to their first permitted plugin page
        if user.role == 'accounts' or user.is_super_admin:
            redirect_url = '/admin-dashboard/'
        else:
            PLUGIN_URLS = [
                ('can_stock_items',       '/stock-items/'),
                ('can_vendor_management', '/vendor-management/'),
                ('can_production',        '/production/'),
                ('can_dispatch',          '/dispatch/'),
                ('can_client_management', '/client-management/'),
                ('can_petty_cash',        '/petty-cash/'),
                ('can_leads',             '/leads/'),
            ]
            redirect_url = '/admin-dashboard/'  # fallback
            for field, url in PLUGIN_URLS:
                if getattr(user, field, False):
                    redirect_url = url
                    break

        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": {
                **UserSerializer(user).data,
                "redirect_url": redirect_url,
            },
            "error": None
        }, status=200)


class UserViewSet(viewsets.ViewSet):
    """
    CRUD for users. All endpoints require the calling user to be
    an admin OR a super_admin.
    """

    # ── Create ────────────────────────────────────────────────────────────
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

    # ── List ──────────────────────────────────────────────────────────────
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

    # ── Retrieve single ───────────────────────────────────────────────────
    @handle_exceptions
    @check_authentication(required_role="admin")
    def retrieve(self, request, pk=None):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "User not found"
            }, status=404)

        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": UserSerializer(user).data,
            "error": None
        }, status=200)

    # ── Update (PUT / PATCH) ──────────────────────────────────────────────
    @handle_exceptions
    @check_authentication(required_role="admin")
    def update(self, request, pk=None):
        return self._update_user(request, pk, partial=False)

    @handle_exceptions
    @check_authentication(required_role="admin")
    def partial_update(self, request, pk=None):
        return self._update_user(request, pk, partial=True)

    def _update_user(self, request, pk, partial):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "User not found"
            }, status=404)

        serializer = UpdateUserSerializer(user, data=request.data, partial=partial)
        if not serializer.is_valid():
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": serializer.errors
            }, status=400)

        updated_user = serializer.save()

        ActivityLog.objects.create(
            user=request.user,
            action="UPDATE",
            model_name="User",
            record_id=updated_user.user_id,
            description=f"Updated user {updated_user.email}"
        )

        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": UserSerializer(updated_user).data,
            "error": None
        }, status=200)

    # ── Delete ────────────────────────────────────────────────────────────
    @handle_exceptions
    @check_authentication(required_role="admin")
    def destroy(self, request, pk=None):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "User not found"
            }, status=404)

        # Prevent self-deletion
        if user.pk == request.user.pk:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "You cannot delete your own account"
            }, status=400)

        email = user.email
        user_id = user.user_id
        user.delete()

        ActivityLog.objects.create(
            user=request.user,
            action="DELETE",
            model_name="User",
            record_id=user_id,
            description=f"Deleted user {email}"
        )

        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": {"message": "User deleted successfully"},
            "error": None
        }, status=200)

    # ── Change Password ───────────────────────────────────────────────────
    @handle_exceptions
    @check_authentication(required_role="admin")
    @action(detail=True, methods=["post"], url_path="change-password")
    def change_password(self, request, pk=None):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "User not found"
            }, status=404)

        serializer = ChangePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": serializer.errors
            }, status=400)

        user.set_password(serializer.validated_data["new_password"])
        user.save()

        ActivityLog.objects.create(
            user=request.user,
            action="CHANGE_PASSWORD",
            model_name="User",
            record_id=user.user_id,
            description=f"Password changed for {user.email}"
        )

        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": {"message": "Password updated successfully"},
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


class LogInToUserAccount(viewsets.ViewSet):
    @handle_exceptions
    @check_authentication(required_role='admin')
    def list(self, request):
            request_user = request.user
            user_id = request.GET.get('user_id')

            user = User.objects.get(user_id=user_id)

            if request_user.is_staff:
                print('Staff')
                login(request, user)
                request.session.set_expiry(30 * 24 * 60 * 60)

            return redirect('/')            
