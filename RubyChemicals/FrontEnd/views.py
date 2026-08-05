from rest_framework import viewsets, status
from rest_framework.response import Response

from django.utils.dateparse import parse_date
from django.http import HttpResponse

from utils.decorators import handle_exceptions
from django.shortcuts import render, redirect
from functools import wraps
from django.contrib.auth import authenticate, login, logout
from Operations.models import *
from UserDetail.models import User
from django.db.models import Q

# ── Decorators ────────────────────────────────────────────────────────────────

def get_first_permitted_url(user):
    """
    Returns the URL name of the first page the user has access to.
    Dashboard is only for 'accounts' role (or super_admin).
    For all other roles, find the first granted plugin page.
    Falls back to dashboard if nothing is permitted.
    """
    # Accounts role always lands on dashboard
    if getattr(user, 'role', None) == 'accounts' or getattr(user, 'is_super_admin', False):
        return 'admin-dashboard-list'

    # Ordered list of (permission_field, url_name) to check
    PLUGIN_URLS = [
        ('can_stock_items',       'stock-items-list'),
        ('can_vendor_management', 'vendor-management-list'),
        ('can_production',        'production-list'),
        ('can_dispatch',          'dispatch-list'),
        ('can_client_management', 'client-management-list'),
        ('can_petty_cash',        'petty-cash-list'),
        ('can_leads',             'leads-list'),
    ]

    for field, url_name in PLUGIN_URLS:
        if bool(getattr(user, field, False)):
            return url_name

    # No plugins granted — fall back to dashboard
    return 'admin-dashboard-list'


def check_authentication(required_role=None, required_permission=None, dashboard_only=False):
    """
    Checks that:
      1. The user is authenticated (redirect to login if not).
      2. Optionally that user.role is in required_role (returns 403 JSON for API views).
      3. Optionally that the user has a plugin permission OR is_super_admin.
         Non-compliant users are redirected to their first permitted page.
      4. dashboard_only=True: only 'accounts' role and super-admins may access;
         all other roles are redirected to their first permitted plugin page.

    Parameters
    ----------
    required_role : str | list | None
        If provided, user.role must be in this value (used for API endpoints).
    required_permission : str | None
        A field name on the User model, e.g. 'can_production'.
    dashboard_only : bool
        If True, blocks everyone except the 'accounts' role and super-admins.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(self, request, *args, **kwargs):
            user = request.user

            # ── 1. Authentication check ──────────────────────────────────
            if not user.is_authenticated:
                return redirect('login-list')

            # ── 2. Role check (API endpoints) ────────────────────────────
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

            # ── 3. Dashboard-only guard ──────────────────────────────────
            if dashboard_only:
                is_accounts = getattr(user, 'role', None) == 'accounts'
                is_super    = getattr(user, 'is_super_admin', False)
                if not (is_accounts or is_super):
                    return redirect(get_first_permitted_url(user))

            # ── 4. Plugin permission check ───────────────────────────────
            if required_permission:
                has_access = (
                    getattr(user, "is_super_admin", False) or
                    bool(getattr(user, required_permission, False))
                )
                if not has_access:
                    return redirect(get_first_permitted_url(user))

            return view_func(self, request, *args, **kwargs)

        return _wrapped_view
    return decorator


# ── Page views ────────────────────────────────────────────────────────────────

class LoginViewSet(viewsets.ViewSet):

    @handle_exceptions
    def list(self, request):
        return render(request, 'login.html')

class LogoutViewSet(viewsets.ViewSet):

    @handle_exceptions
    def list(self, request):
        logout(request)
        return redirect('login-list')


class AdminDashboardViewSet(viewsets.ViewSet):
    """
    Dashboard is only accessible to the 'accounts' role and super-admins.
    All other roles are redirected to their first permitted plugin page.
    """

    @handle_exceptions
    @check_authentication(dashboard_only=True)
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
    """Stock Inwards shares the same permission as Stock Items."""

    @handle_exceptions
    @check_authentication(required_permission='can_stock_items')
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
        all_users_with_leads_permission = User.objects.filter(
            Q(role='admin') | Q(can_leads=True)
        ).exclude(id=request.user.id)
        is_admin_or_super = request.user.role == 'admin' or request.user.is_super_admin
        return render(request, 'leads.html', {'all_users_with_leads_permission': all_users_with_leads_permission, 'is_admin_or_super': is_admin_or_super})


class LeadSubDeptMngmtViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication(required_permission='can_vendor_management')
    def list(self, request):
        return render(request, 'lead_sub_dept_mgmt.html')


# ── Role Manager page ─────────────────────────────────────────────────────────

class RoleManagerViewSet(viewsets.ViewSet):
    """
    Renders the Role Manager HTML page.
    Only accessible to users who are super-admin OR have the 'admin' role.
    """

    @handle_exceptions
    def list(self, request):
        user = request.user
        if not user.is_authenticated:
            return redirect('login-list')
        if not (getattr(user, 'role', None) == 'admin' or getattr(user, 'is_super_admin', False)):
            return redirect(get_first_permitted_url(user))
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
