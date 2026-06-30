from rest_framework import viewsets, status
from rest_framework.response import Response

from django.utils.dateparse import parse_date
from django.http import HttpResponse

from utils.decorators import handle_exceptions
from django.shortcuts import render, redirect
from functools import wraps
from django.contrib.auth import authenticate, login, logout
from Operations.models import *


# ── Decorators ────────────────────────────────────────────────────────────────

def check_authentication(required_role=None, required_permission=None):
    """
    Checks that:
      1. The user is authenticated (redirect to login if not).
      2. Optionally that user.role is in required_role.
      3. Optionally that the user has a plugin permission OR is_super_admin.

    Parameters
    ----------
    required_role : str | list | None
        If provided, user.role must be in this value.
    required_permission : str | None
        A field name on the User model, e.g. 'can_production'.
        If provided, user must have that field == True OR be a super_admin.
        Non-compliant authenticated users are redirected to the dashboard.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(self, request, *args, **kwargs):
            user = request.user

            # ── 1. Authentication check ──────────────────────────────────
            if not user.is_authenticated:
                return redirect('login-list')

            # ── 2. Role check ────────────────────────────────────────────
            if required_role:
                allowed_roles = (
                    required_role
                    if isinstance(required_role, (list, tuple, set))
                    else [required_role]
                )
                if getattr(user, "role", None) not in allowed_roles:
                    return Response(
                        {
                            "success": False,
                            "user_not_logged_in": False,
                            "user_unauthorized": True,
                            "data": None,
                            "error": f"User role must be one of {allowed_roles}"
                        },
                        status=status.HTTP_403_FORBIDDEN
                    )

            # ── 3. Plugin permission check ───────────────────────────────
            if required_permission:
                has_access = (
                    getattr(user, "is_super_admin", False) or
                    bool(getattr(user, required_permission, False))
                )
                if not has_access:
                    # Redirect to the dashboard instead of showing an error page
                    return redirect('admin-dashboard-list')

            return view_func(self, request, *args, **kwargs)

        return _wrapped_view
    return decorator


# ── Page views ────────────────────────────────────────────────────────────────

class LoginViewSet(viewsets.ViewSet):

    @handle_exceptions
    def list(self, request):
        return render(request, 'login.html')


class AdminDashboardViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        return render(request, 'admin_dashboard.html')


class AccountsDashboardViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        return render(request, 'accounts_dashboard.html')


class ProductionDashboardViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        return render(request, 'production_dashboard.html')


class StockGroupViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        return render(request, 'stock_groups.html')


class StockItemViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication(required_permission='can_stock_items')
    def list(self, request):
        return render(request, 'stock_item.html')


class StockInwardViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication(required_permission='can_stock_inwards')
    def list(self, request):
        return render(request, 'stock_inward.html')


class ProductionViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication(required_permission='can_production')
    def list(self, request):
        return render(request, 'production.html')


class DispatchViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication(required_permission='can_dispatch')
    def list(self, request):
        return render(request, 'dispatch.html')


class ClientManagementViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication(required_permission='can_client_management')
    def list(self, request):
        return render(request, 'client_management.html')


class PettyCashViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication(required_permission='can_petty_cash')
    def list(self, request):
        return render(request, 'petty_cash.html')


class VendorManagementViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication(required_permission='can_vendor_management')
    def list(self, request):
        return render(request, 'vendor_management.html')


class LeadsViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication(required_permission='can_leads')
    def list(self, request):
        return render(request, 'leads.html')


# ── Role Manager page ─────────────────────────────────────────────────────────

class RoleManagerViewSet(viewsets.ViewSet):
    """
    Renders the Role Manager HTML page.
    Only accessible to users who are super-admin or have the admin role.
    """

    @handle_exceptions
    @check_authentication(required_role="admin")
    def list(self, request):
        return render(request, 'role_manager.html')


# ── Misc / test viewset ───────────────────────────────────────────────────────

class ExtraAddStockDetails(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):

        stock_groups = ['AIWON CONSTRUCTION CHEMICALS',
        'CONTRACT MANUFACTURING',
        'KRIFIX',
        'PACKING MATERIALS',
        'RAW MATERIAL',
        'RUBY CHEMICALS',
        'SAMPLE',
        'SEMI FINISHED',
        'TECHNONICOL',
        'TRADING']

        stock_items = [
    {"stock_name": "AWON BOND - 40 KGS", "stock_group": "AIWON CONSTRUCTION CHEMICALS", "uom": "BAGS", "hsn": "38245090", "gst": "18"},
{"stock_name": "NIRAFLEX - 30 KGS", "stock_group": "AIWON CONSTRUCTION CHEMICALS", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "NIRAGROUT - 25 KGS", "stock_group": "AIWON CONSTRUCTION CHEMICALS", "uom": "BAGS", "hsn": "38244090", "gst": "18"},
]

        return Response({"success": True, "data": stock_items, "error": None}, status=200)
