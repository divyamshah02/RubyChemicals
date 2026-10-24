"""
UserDetail/asset_utils.py
─────────────────────────
All asset state changes (assign, return, transfer, retire) live here so every
change updates the Asset and its AssetAssignment history together, inside one
transaction.
"""

from django.db import IntegrityError, transaction
from django.db.models import Max
from django.utils import timezone

from .models import Asset, AssetAssignment


class AssetError(Exception):
    """A rule was broken; the message is safe to show to the user."""


def create_asset(by, **fields):
    """Creates an asset with the next free code (RBCA001, RBCA002, ...)."""
    for _ in range(5):
        try:
            with transaction.atomic():
                last = Asset.objects.aggregate(top=Max('code_number'))['top'] or 0
                return Asset.objects.create(code_number=last + 1, created_by=by, **fields)
        except IntegrityError:
            # Another request took the same number, or the identifier is taken: re-check.
            clash = Asset.objects.filter(unique_identifier=fields.get('unique_identifier', '')).first()
            if clash and fields.get('unique_identifier'):
                raise AssetError(f"{clash.asset_code} already uses this identifier.")
    raise AssetError("Could not generate an asset code. Please try again.")


def _locked(asset):
    return Asset.objects.select_for_update().get(pk=asset.pk)


def _check_date(value):
    value = value or timezone.localdate()
    if value > timezone.localdate():
        raise AssetError("The date cannot be in the future.")
    return value


def _check_assignee(employee):
    if not employee.active_user:
        raise AssetError(f"{employee.name} is not an active user.")
    detail = getattr(employee, 'employee_detail', None)
    if detail is not None and detail.is_exited:
        raise AssetError(f"{employee.name} has exited, so assets cannot be assigned to them.")


def _open_assignment(asset):
    return asset.assignments.select_for_update().filter(returned_on__isnull=True).first()


def _start(asset, employee, by, on, note):
    _check_assignee(employee)
    last_return = asset.assignments.aggregate(last=Max('returned_on'))['last']
    if last_return and on < last_return:
        raise AssetError(f"This asset was last returned on {last_return:%d-%m-%Y}; choose that date or later.")
    employee_detail = getattr(employee, 'employee_detail', None)
    AssetAssignment.objects.create(
        asset=asset,
        employee=employee,
        employee_name=(employee_detail.full_name if employee_detail and employee_detail.full_name else employee.name),
        assigned_on=on,
        assign_note=note,
        assigned_by=by,
    )
    asset.status = Asset.STATUS_ASSIGNED
    asset.assigned_to = employee
    asset.assigned_on = on
    asset.save(update_fields=['status', 'assigned_to', 'assigned_on', 'updated_at'])


def _end(asset, by, on, note, reason):
    open_row = _open_assignment(asset)
    if open_row is None:
        raise AssetError("This asset is not currently assigned.")
    if on < open_row.assigned_on:
        raise AssetError(f"The asset was assigned on {open_row.assigned_on:%d-%m-%Y}; the date cannot be earlier.")
    open_row.returned_on = on
    open_row.end_reason = reason
    open_row.return_note = note
    open_row.ended_by = by
    open_row.ended_at = timezone.now()
    open_row.save()
    asset.status = Asset.STATUS_AVAILABLE
    asset.assigned_to = None
    asset.assigned_on = None
    asset.save(update_fields=['status', 'assigned_to', 'assigned_on', 'updated_at'])
    return open_row


def assign_asset(asset, employee, by, on=None, note=''):
    on = _check_date(on)
    with transaction.atomic():
        asset = _locked(asset)
        if asset.status == Asset.STATUS_RETIRED:
            raise AssetError("A retired asset cannot be assigned. Reinstate it first.")
        if asset.status == Asset.STATUS_ASSIGNED:
            raise AssetError(f"{asset.asset_code} is already assigned to {asset.assigned_to.name}.")
        _start(asset, employee, by, on, note)
    return asset


def return_asset(asset, by, on=None, note=''):
    on = _check_date(on)
    with transaction.atomic():
        asset = _locked(asset)
        _end(asset, by, on, note, AssetAssignment.END_RETURNED)
    return asset


def transfer_asset(asset, employee, by, on=None, note=''):
    on = _check_date(on)
    with transaction.atomic():
        asset = _locked(asset)
        if asset.status != Asset.STATUS_ASSIGNED:
            raise AssetError("Only an assigned asset can be transferred.")
        if asset.assigned_to_id == employee.pk:
            raise AssetError(f"{asset.asset_code} is already with {employee.name}.")
        _end(asset, by, on, note, AssetAssignment.END_TRANSFERRED)
        _start(asset, employee, by, on, note)
    return asset


def retire_asset(asset, note):
    with transaction.atomic():
        asset = _locked(asset)
        if asset.status == Asset.STATUS_ASSIGNED:
            raise AssetError("Return the asset before retiring it.")
        if asset.status == Asset.STATUS_RETIRED:
            raise AssetError("This asset is already retired.")
        asset.status = Asset.STATUS_RETIRED
        asset.notes = f"{asset.notes}\nRetired: {note}".strip()
        asset.save(update_fields=['status', 'notes', 'updated_at'])
    return asset


def reinstate_asset(asset):
    with transaction.atomic():
        asset = _locked(asset)
        if asset.status != Asset.STATUS_RETIRED:
            raise AssetError("Only a retired asset can be reinstated.")
        asset.status = Asset.STATUS_AVAILABLE
        asset.save(update_fields=['status', 'updated_at'])
    return asset
