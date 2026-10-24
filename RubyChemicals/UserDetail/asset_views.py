"""
UserDetail/asset_views.py
─────────────────────────
HR API for company assets: create / edit, assign, return, transfer, retire and
the full history of who held what and when.

Access: HR role / `can_hr` permission, admins and super-admins.
"""

from django.db.models import Q
from django.utils.dateparse import parse_date
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser

from . import asset_utils
from .asset_utils import AssetError
from .hr_serializers import AssetAssignmentSerializer, AssetSerializer
from .hr_views import employee_users, fail, flatten_errors, hr_access_required, log_action, ok
from .models import Asset, AssetAssignment, User


class HRAssetViewSet(viewsets.ViewSet):
    parser_classes = [JSONParser]

    # ── Helpers ──────────────────────────────────────────────────────────

    def _queryset(self):
        return Asset.objects.select_related('assigned_to')

    def _get(self, pk):
        try:
            return self._queryset().get(pk=pk)
        except (Asset.DoesNotExist, ValueError):
            return None

    @staticmethod
    def _date(request, key='date'):
        """Returns (date_or_None, error). Empty means today."""
        raw = request.data.get(key)
        if not raw:
            return None, None
        parsed = parse_date(str(raw))
        if parsed is None:
            return None, "Enter a valid date."
        return parsed, None

    @staticmethod
    def _employee(raw):
        """Returns (user_or_None, error)."""
        if not raw:
            return None, "Choose an employee."
        try:
            user = employee_users().select_related('employee_detail').get(pk=raw)
        except (User.DoesNotExist, ValueError, TypeError):
            return None, "Employee not found."
        return user, None

    @staticmethod
    def _note(request, key='note'):
        return str(request.data.get(key) or '').strip()[:500]

    def _data(self, asset):
        return AssetSerializer(asset).data

    # ── Collection ───────────────────────────────────────────────────────

    @hr_access_required
    def list(self, request):
        """GET ?status=&type=&assigned_to=&q="""
        assets = self._queryset()

        status_filter = request.query_params.get('status')
        if status_filter:
            assets = assets.filter(status=status_filter)
        type_filter = request.query_params.get('type')
        if type_filter:
            assets = assets.filter(asset_type=type_filter)
        holder = request.query_params.get('assigned_to')
        if holder:
            assets = assets.filter(assigned_to_id=holder)

        search = (request.query_params.get('q') or '').strip()
        if search:
            assets = assets.filter(
                Q(name__icontains=search) | Q(unique_identifier__icontains=search)
                | Q(secondary_identifier__icontains=search) | Q(type_label__icontains=search)
                | Q(assigned_to__name__icontains=search)
            )
        return ok(AssetSerializer(assets, many=True).data)

    @hr_access_required
    def create(self, request):
        """
        POST — creates an asset and generates its code.
        Optional `assign_to` (user id) and `assigned_on` assign it straight away.
        """
        serializer = AssetSerializer(data=request.data)
        if not serializer.is_valid():
            return fail(flatten_errors(serializer.errors), errors=serializer.errors)

        assignee = None
        assigned_on = None
        if request.data.get('assign_to'):
            assignee, error = self._employee(request.data.get('assign_to'))
            if error:
                return fail(error)
            assigned_on, error = self._date(request, 'assigned_on')
            if error:
                return fail(error)

        try:
            asset = asset_utils.create_asset(request.user, **serializer.validated_data)
            if assignee:
                try:
                    asset = asset_utils.assign_asset(
                        asset, assignee, request.user, assigned_on, self._note(request))
                except AssetError:
                    # Keep the asset consistent: no half-created record when assigning fails.
                    asset.delete()
                    raise
        except AssetError as exc:
            return fail(str(exc))

        log_action(request, 'Created asset', asset.asset_code,
                   f"Created {asset.get_asset_type_display()} {asset.asset_code}"
                   + (f" and assigned it to {assignee.name}" if assignee else ""))
        return ok(self._data(asset), status.HTTP_201_CREATED)

    # ── Single asset ─────────────────────────────────────────────────────

    @hr_access_required
    def retrieve(self, request, pk=None):
        """GET — the asset and every assignment it has had."""
        asset = self._get(pk)
        if asset is None:
            return fail("Asset not found.", status.HTTP_404_NOT_FOUND)
        history = asset.assignments.select_related('employee', 'assigned_by', 'ended_by', 'asset')
        return ok({
            'asset': self._data(asset),
            'history': AssetAssignmentSerializer(history, many=True).data,
        })

    @hr_access_required
    def partial_update(self, request, pk=None):
        asset = self._get(pk)
        if asset is None:
            return fail("Asset not found.", status.HTTP_404_NOT_FOUND)
        serializer = AssetSerializer(asset, data=request.data, partial=True)
        if not serializer.is_valid():
            return fail(flatten_errors(serializer.errors), errors=serializer.errors)
        asset = serializer.save()
        log_action(request, 'Updated asset', asset.asset_code, f"Updated details of {asset.asset_code}")
        return ok(self._data(asset))

    @hr_access_required
    def destroy(self, request, pk=None):
        """DELETE — only for an asset that has never been assigned (a data-entry mistake)."""
        asset = self._get(pk)
        if asset is None:
            return fail("Asset not found.", status.HTTP_404_NOT_FOUND)
        if asset.assignments.exists():
            return fail("This asset has assignment history, so it cannot be deleted. Retire it instead.")
        code = asset.asset_code
        asset.delete()
        log_action(request, 'Deleted asset', code, f"Deleted unused asset {code}")
        return ok({'deleted': True})

    # ── Actions ──────────────────────────────────────────────────────────

    def _run(self, request, pk, verb, perform):
        asset = self._get(pk)
        if asset is None:
            return fail("Asset not found.", status.HTTP_404_NOT_FOUND)
        try:
            result = perform(asset)
        except AssetError as exc:
            return fail(str(exc))
        asset = self._get(result.pk)
        log_action(request, f"{verb} asset", asset.asset_code,
                   f"{verb} {asset.asset_code}" + (f" ({asset.assigned_to.name})" if asset.assigned_to_id else ""))
        return ok(self._data(asset))

    @action(detail=True, methods=['post'])
    @hr_access_required
    def assign(self, request, pk=None):
        employee, error = self._employee(request.data.get('employee'))
        if error:
            return fail(error)
        on, error = self._date(request)
        if error:
            return fail(error)
        return self._run(request, pk, 'Assigned', lambda a: asset_utils.assign_asset(
            a, employee, request.user, on, self._note(request)))

    @action(detail=True, methods=['post'])
    @hr_access_required
    def transfer(self, request, pk=None):
        employee, error = self._employee(request.data.get('employee'))
        if error:
            return fail(error)
        on, error = self._date(request)
        if error:
            return fail(error)
        return self._run(request, pk, 'Transferred', lambda a: asset_utils.transfer_asset(
            a, employee, request.user, on, self._note(request)))

    @action(detail=True, methods=['post'], url_path='return')
    @hr_access_required
    def return_asset(self, request, pk=None):
        on, error = self._date(request)
        if error:
            return fail(error)
        return self._run(request, pk, 'Returned', lambda a: asset_utils.return_asset(
            a, request.user, on, self._note(request)))

    @action(detail=True, methods=['post'])
    @hr_access_required
    def retire(self, request, pk=None):
        note = self._note(request)
        if not note:
            return fail("Add a reason for retiring this asset.")
        return self._run(request, pk, 'Retired', lambda a: asset_utils.retire_asset(a, note))

    @action(detail=True, methods=['post'])
    @hr_access_required
    def reinstate(self, request, pk=None):
        return self._run(request, pk, 'Reinstated', asset_utils.reinstate_asset)

    @action(detail=False, methods=['get'], url_path='employee-history')
    @hr_access_required
    def employee_history(self, request):
        """GET ?employee=<user id> — every assignment that employee has had, newest first."""
        rows = (
            AssetAssignment.objects.filter(employee_id=request.query_params.get('employee') or 0)
            .select_related('asset', 'employee', 'assigned_by', 'ended_by')
        )
        return ok(AssetAssignmentSerializer(rows, many=True).data)
