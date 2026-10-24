"""
UserDetail/hr_views.py
──────────────────────
API endpoints for the HR page: employee profiles, attendance report,
per-employee leaves and company-wide (universal) leaves.

Access: HR role / `can_hr` permission, admins and super-admins.
"""

import json
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from functools import wraps

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from .hr_serializers import (
    EmergencyContactSerializer,
    EmployeeDetailSerializer,
    LeaveApplicationSerializer,
    LeaveSerializer,
    PayrollSerializer,
    ReimbursementSerializer,
    UniversalLeaveSerializer,
)
from .leave_utils import (
    QUOTA_TYPES,
    WEEKLY_OFF_WEEKDAYS,
    check_quota,
    daterange,
    day_weight,
    eligible_dates,
    employee_detail_for,
    holiday_dates,
    leave_balance,
)
from .models import (
    ActivityLog,
    Attendance,
    EmergencyContact,
    EmployeeDetail,
    Leave,
    LeaveApplication,
    Payroll,
    Reimbursement,
    UniversalLeave,
    User,
)
from . import payroll_utils
from .payroll_utils import PayrollError
from utils.create_salary_slip_pdf import generate_salary_slip

HALF_DAY_CUTOFF = time(12, 0)   # first check-in after this time is a half day
MAX_RANGE_DAYS = 366
MAX_APPLICATION_DAYS = 31       # longest single leave application
MAX_BACKDATE_DAYS = 7           # employees may apply for up to a week in the past


# ── Helpers ──────────────────────────────────────────────────────────────────

def ok(data=None, http_status=status.HTTP_200_OK, **extra):
    return Response({"success": True, "data": data, "error": None, **extra}, status=http_status)


def fail(error, http_status=status.HTTP_400_BAD_REQUEST, errors=None):
    return Response(
        {"success": False, "data": None, "error": error, "errors": errors},
        status=http_status,
    )


def flatten_errors(errors):
    """Turns DRF error dicts into one readable line."""
    parts = []
    for field, messages in errors.items():
        if isinstance(messages, (list, tuple)):
            messages = ' '.join(str(m) for m in messages)
        parts.append(f"{field.replace('_', ' ').title()}: {messages}")
    return ' | '.join(parts)


def has_hr_access(user):
    return bool(
        user.is_authenticated and (
            user.is_super_admin or user.role == 'admin' or user.role == 'hr' or user.can_hr
        )
    )


def hr_access_required(view_func):
    @wraps(view_func)
    def wrapped(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.active_user:
            return fail("Authentication required.", status.HTTP_401_UNAUTHORIZED)
        if not has_hr_access(request.user):
            return fail("You do not have access to the HR module.", status.HTTP_403_FORBIDDEN)
        return view_func(self, request, *args, **kwargs)
    return wrapped


def employee_users():
    """Everyone HR manages: all users except admins."""
    return User.objects.filter(is_super_admin=False).exclude(role='admin')


def ensure_employee_details():
    """Creates a blank profile for any user that does not have one yet."""
    missing = employee_users().filter(employee_detail__isnull=True)
    EmployeeDetail.objects.bulk_create(
        [EmployeeDetail(user=u, full_name=u.name) for u in missing]
    )


def employee_queryset():
    return (
        EmployeeDetail.objects
        .filter(user__in=employee_users())
        .select_related('user', 'reporting_to')
        .prefetch_related('emergency_contacts', 'user__held_assets')
    )


def log_action(request, action, record_id, description):
    ActivityLog.objects.create(
        user=request.user,
        action=action,
        model_name='HR',
        record_id=str(record_id),
        description=description,
    )


def parse_range(request, default_days=None):
    """Returns (start, end, error). Defaults to the current month."""
    today = timezone.localdate()
    start = parse_date(request.query_params.get('from_date') or '')
    end = parse_date(request.query_params.get('to_date') or '')
    if request.query_params.get('from_date') and not start:
        return None, None, "Invalid from_date."
    if request.query_params.get('to_date') and not end:
        return None, None, "Invalid to_date."
    if not start and not end:
        start = today.replace(day=1)
        end = today
    elif not start:
        start = end.replace(day=1)
    elif not end:
        end = today
    if start > end:
        return None, None, "From date cannot be after to date."
    if (end - start).days > MAX_RANGE_DAYS:
        return None, None, f"Date range cannot exceed {MAX_RANGE_DAYS} days."
    return start, end, None


def local_iso(value):
    return timezone.localtime(value).isoformat() if value else None


def build_attendance_rows(user, start, end, records=None, leaves=None, holidays=None):
    """
    One row per calendar day with check-in/out, status and flags.

    `records`, `leaves` and `holidays` are dicts keyed by date. Pass them in when
    building many users at once to avoid a query per user; otherwise they are loaded here.
    """
    today = timezone.localdate()
    detail = getattr(user, 'employee_detail', None)
    joining = detail.joining_date if detail else None
    if joining and start < joining:
        start = joining

    if records is None:
        records = {a.date: a for a in Attendance.objects.filter(user=user, date__range=(start, end))}
    if leaves is None:
        leaves = {l.date: l for l in Leave.objects.filter(user=user, date__range=(start, end))}
    if holidays is None:
        holidays = {h.date: h for h in UniversalLeave.objects.filter(date__range=(start, end))}

    rows = []
    summary = {
        'present': 0, 'half_day': 0, 'absent': 0, 'leave_days': 0.0,
        'holidays': 0, 'weekly_off': 0, 'forgot_checkout': 0, 'worked_minutes': 0,
    }

    for day in daterange(start, end) if start <= end else []:
        record = records.get(day)
        leave = leaves.get(day)
        holiday = holidays.get(day)
        weekly_off = day.weekday() in WEEKLY_OFF_WEEKDAYS

        check_in = timezone.localtime(record.check_in_time) if record and record.check_in_time else None
        check_out = timezone.localtime(record.check_out_time) if record and record.check_out_time else None

        row = {
            'date': day.isoformat(),
            'weekday': day.strftime('%a'),
            'check_in': local_iso(record.check_in_time) if record else None,
            'check_out': local_iso(record.check_out_time) if record else None,
            'worked_minutes': None,
            'is_half_day': False,
            'forgot_checkout': False,
            'in_progress': False,
            'leave': (
                {
                    'type': leave.get_leave_type_display(),
                    'day_type': leave.day_type,
                    'reason': leave.reason,
                } if leave else None
            ),
            'holiday': holiday.title if holiday else None,
            'status': None,
        }

        if check_in:
            row['is_half_day'] = check_in.time() > HALF_DAY_CUTOFF
            if check_out:
                minutes = max(int((check_out - check_in).total_seconds() // 60), 0)
                row['worked_minutes'] = minutes
                summary['worked_minutes'] += minutes
            elif day < today:
                row['forgot_checkout'] = True
                summary['forgot_checkout'] += 1
            else:
                row['in_progress'] = True
            row['status'] = 'half_day' if row['is_half_day'] else 'present'
            summary['half_day' if row['is_half_day'] else 'present'] += 1
        elif holiday:
            row['status'] = 'holiday'
            summary['holidays'] += 1
        elif leave:
            row['status'] = 'leave' if leave.day_type == 'full' else 'half_leave'
        elif weekly_off:
            row['status'] = 'weekly_off'
            summary['weekly_off'] += 1
        elif day > today:
            continue
        elif day == today:
            row['status'] = 'not_checked_in'
        else:
            row['status'] = 'absent'
            summary['absent'] += 1

        if leave:
            summary['leave_days'] += 1.0 if leave.day_type == 'full' else 0.5

        rows.append(row)

    return rows, summary


# ── Employee profiles ────────────────────────────────────────────────────────

class HREmployeeViewSet(viewsets.ViewSet):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def _serialize(self, request, queryset, many=False):
        return EmployeeDetailSerializer(queryset, many=many, context={'request': request}).data

    @hr_access_required
    def list(self, request):
        ensure_employee_details()
        employees = employee_queryset().order_by('user__name')
        return ok(self._serialize(request, employees, many=True))

    @hr_access_required
    def retrieve(self, request, pk=None):
        ensure_employee_details()
        detail = employee_queryset().filter(user_id=pk).first()
        if not detail:
            return fail("Employee not found.", status.HTTP_404_NOT_FOUND)
        return ok(self._serialize(request, detail))

    @hr_access_required
    def partial_update(self, request, pk=None):
        """PATCH /hr-employee-api/<user pk>/ — multipart (files) or JSON."""
        ensure_employee_details()
        detail = employee_queryset().filter(user_id=pk).first()
        if not detail:
            return fail("Employee not found.", status.HTTP_404_NOT_FOUND)
        locked = exited_lock(request, detail.user)
        if locked:
            return locked

        contacts = None
        raw_contacts = request.data.get('emergency_contacts')
        if raw_contacts is not None:
            try:
                contacts = json.loads(raw_contacts) if isinstance(raw_contacts, str) else raw_contacts
            except ValueError:
                return fail("Emergency contacts are not valid JSON.")
            if not isinstance(contacts, list):
                return fail("Emergency contacts must be a list.")
            contact_serializer = EmergencyContactSerializer(data=contacts, many=True)
            if not contact_serializer.is_valid():
                for index, errors in enumerate(contact_serializer.errors):
                    if errors:
                        return fail(f"Emergency contact {index + 1}: {flatten_errors(errors)}",
                                    errors=contact_serializer.errors)
            contacts = contact_serializer.validated_data

        serializer = EmployeeDetailSerializer(
            detail, data=request.data, partial=True, context={'request': request}
        )
        if not serializer.is_valid():
            return fail(flatten_errors(serializer.errors), errors=serializer.errors)

        with transaction.atomic():
            serializer.save()
            if contacts is not None:
                detail.emergency_contacts.all().delete()
                EmergencyContact.objects.bulk_create(
                    [EmergencyContact(employee=detail, **c) for c in contacts]
                )

        log_action(request, 'Updated employee details', detail.user_id, f"Updated profile of {detail.user.name}")
        refreshed = employee_queryset().get(pk=detail.pk)
        return ok(self._serialize(request, refreshed))

    update = partial_update

    @action(detail=True, methods=['post'], url_path='exit')
    @hr_access_required
    def mark_exit(self, request, pk=None):
        """
        POST {last_working_day, exit_intent, remarks?}
        Marks the employee as exited and deactivates the login. After this only an admin
        can change the employee's records.
        """
        ensure_employee_details()
        detail = employee_queryset().filter(user_id=pk).first()
        if not detail:
            return fail("Employee not found.", status.HTTP_404_NOT_FOUND)
        if detail.user_id == request.user.pk:
            return fail("You cannot mark your own account as exited.", status.HTTP_403_FORBIDDEN)
        if detail.is_exited:
            return fail("This employee has already exited.")

        last_day = parse_date(str(request.data.get('last_working_day') or ''))
        if not last_day:
            return fail("Last working day is required.")
        if detail.joining_date and last_day < detail.joining_date:
            return fail("Last working day cannot be before the joining date.")
        if (last_day - timezone.localdate()).days > 366:
            return fail("Last working day is too far in the future.")

        intent = (request.data.get('exit_intent') or '').strip()
        if intent not in dict(EmployeeDetail.EXIT_INTENT_CHOICES):
            return fail("Choose a valid exit intent.")
        remarks = (request.data.get('remarks') or '').strip()
        if intent == 'other' and not remarks:
            return fail("Please add remarks when the exit intent is Other.")

        with transaction.atomic():
            detail.is_exited = True
            detail.last_working_day = last_day
            detail.exit_intent = intent
            detail.exit_remarks = remarks[:1000]
            detail.exited_at = timezone.now()
            detail.exited_by = request.user
            detail.save()
            detail.user.active_user = False
            detail.user.save(update_fields=['active_user'])

        log_action(
            request, 'Marked employee exited', detail.user_id,
            f"{detail.user.name} exited ({detail.get_exit_intent_display()}), last working day {last_day}",
        )
        refreshed = employee_queryset().get(pk=detail.pk)
        return ok(self._serialize(request, refreshed))

    @action(detail=True, methods=['post'], url_path='reactivate')
    @hr_access_required
    def reactivate(self, request, pk=None):
        """POST — admin only. Reverses an exit and restores the login."""
        if not is_admin_user(request.user):
            return fail("Only an admin can reverse an exit.", status.HTTP_403_FORBIDDEN)
        detail = employee_queryset().filter(user_id=pk).first()
        if not detail:
            return fail("Employee not found.", status.HTTP_404_NOT_FOUND)
        if not detail.is_exited:
            return fail("This employee has not exited.")

        with transaction.atomic():
            detail.is_exited = False
            detail.last_working_day = None
            detail.exit_intent = ''
            detail.exit_remarks = ''
            detail.exited_at = None
            detail.exited_by = None
            detail.save()
            detail.user.active_user = True
            detail.user.save(update_fields=['active_user'])

        log_action(request, 'Reversed employee exit', detail.user_id, f"Reactivated {detail.user.name}")
        refreshed = employee_queryset().get(pk=detail.pk)
        return ok(self._serialize(request, refreshed))


# ── Attendance report ────────────────────────────────────────────────────────

class HRAttendanceViewSet(viewsets.ViewSet):

    def _everyone_on(self, request):
        """GET ?date=YYYY-MM-DD (default today) — one row per active employee for that day."""
        raw = request.query_params.get('date')
        day = parse_date(raw) if raw else timezone.localdate()
        if not day:
            return fail("Invalid date.")

        users = list(
            employee_users().filter(active_user=True)
            .select_related('employee_detail').order_by('name')
        )
        records = {a.user_id: a for a in Attendance.objects.filter(date=day)}
        leaves = {l.user_id: l for l in Leave.objects.filter(date=day)}
        holidays = {h.date: h for h in UniversalLeave.objects.filter(date=day)}

        today = timezone.localdate()
        counts = {
            'total': len(users), 'present': 0, 'half_day': 0, 'absent': 0, 'on_leave': 0,
            'not_checked_in': 0, 'holiday': 0, 'weekly_off': 0, 'forgot_checkout': 0,
        }
        rows = []
        for user in users:
            detail = getattr(user, 'employee_detail', None)
            user_rows, _ = build_attendance_rows(
                user, day, day,
                records={day: records[user.pk]} if user.pk in records else {},
                leaves={day: leaves[user.pk]} if user.pk in leaves else {},
                holidays=holidays,
            )
            row = user_rows[0] if user_rows else {
                'date': day.isoformat(), 'weekday': day.strftime('%a'),
                'check_in': None, 'check_out': None, 'worked_minutes': None,
                'is_half_day': False, 'forgot_checkout': False, 'in_progress': False,
                'leave': None, 'holiday': None,
                'status': 'upcoming' if day > today else 'not_joined',
            }
            row['user'] = {
                'id': user.pk, 'name': user.name, 'user_code': user.user_id,
                'department': detail.department if detail else '',
                'position': detail.position if detail else '',
            }
            rows.append(row)

            status_key = row['status']
            if status_key in ('leave', 'half_leave'):
                counts['on_leave'] += 1
            elif status_key in counts:
                counts[status_key] += 1
            if row['forgot_checkout']:
                counts['forgot_checkout'] += 1

        return ok({
            'mode': 'day',
            'date': day.isoformat(),
            'half_day_cutoff': HALF_DAY_CUTOFF.strftime('%H:%M'),
            'rows': rows,
            'counts': counts,
        })

    @hr_access_required
    def list(self, request):
        """
        GET                          — every employee for today
        GET ?date=                   — every employee for one date
        GET ?user_id=<pk>&from_date=&to_date= — day-by-day attendance for one employee
        """
        user_pk = request.query_params.get('user_id')
        if not user_pk or user_pk == 'all':
            return self._everyone_on(request)
        user = employee_users().filter(pk=user_pk).select_related('employee_detail').first()
        if not user:
            return fail("Employee not found.", status.HTTP_404_NOT_FOUND)

        start, end, error = parse_range(request)
        if error:
            return fail(error)

        rows, summary = build_attendance_rows(user, start, end)
        return ok({
            'user': {'id': user.pk, 'name': user.name, 'user_code': user.user_id},
            'from_date': start.isoformat(),
            'to_date': end.isoformat(),
            'half_day_cutoff': HALF_DAY_CUTOFF.strftime('%H:%M'),
            'rows': rows,
            'summary': summary,
        })


def is_admin_user(user):
    return bool(user.is_super_admin or user.role == 'admin')


def exited_lock(request, user):
    """
    A 403 response when `user` has exited and the caller is not an admin, else None.
    Once an employee is marked exited only an admin may change their records.
    """
    detail = getattr(user, 'employee_detail', None)
    if detail is not None and detail.is_exited and not is_admin_user(request.user):
        return fail("This employee has exited. Only an admin can change their records.", status.HTTP_403_FORBIDDEN)
    return None


# ── Leaves ───────────────────────────────────────────────────────────────────

class HRLeaveViewSet(viewsets.ViewSet):

    @hr_access_required
    def list(self, request):
        """GET ?user_id=&from_date=&to_date=&leave_type="""
        leaves = Leave.objects.filter(user__in=employee_users()).select_related('user', 'created_by')

        user_pk = request.query_params.get('user_id')
        if user_pk:
            leaves = leaves.filter(user_id=user_pk)
        leave_type = request.query_params.get('leave_type')
        if leave_type:
            leaves = leaves.filter(leave_type=leave_type)
        start = parse_date(request.query_params.get('from_date') or '')
        end = parse_date(request.query_params.get('to_date') or '')
        if start:
            leaves = leaves.filter(date__gte=start)
        if end:
            leaves = leaves.filter(date__lte=end)

        return ok(LeaveSerializer(leaves.order_by('-date', 'user__name'), many=True).data)

    @hr_access_required
    def create(self, request):
        """
        POST {user_id, from_date, to_date?, leave_type, day_type, reason}
        Weekly offs, company holidays and days that already have a leave are skipped.
        """
        data = request.data
        user = employee_users().filter(pk=data.get('user_id')).first()
        if not user:
            return fail("Choose a valid employee.")
        locked = exited_lock(request, user)
        if locked:
            return locked

        start = parse_date(str(data.get('from_date') or ''))
        end = parse_date(str(data.get('to_date') or '')) or start
        if not start:
            return fail("From date is required.")
        if end < start:
            return fail("To date cannot be before from date.")
        if (end - start).days > 92:
            return fail("A single leave entry can cover at most 93 days.")

        leave_type = data.get('leave_type') or 'casual'
        day_type = data.get('day_type') or 'full'
        if leave_type not in dict(Leave.LEAVE_TYPE_CHOICES):
            return fail("Invalid leave type.")
        if day_type not in dict(Leave.DAY_TYPE_CHOICES):
            return fail("Invalid day type.")
        if day_type == 'half' and start != end:
            return fail("A half-day leave can only be added for a single date.")

        holidays = {h.date: h.title for h in UniversalLeave.objects.filter(date__range=(start, end))}
        existing = set(Leave.objects.filter(user=user, date__range=(start, end)).values_list('date', flat=True))

        created, skipped = [], []
        with transaction.atomic():
            for day in daterange(start, end):
                if day in existing:
                    skipped.append({'date': day.isoformat(), 'reason': 'Leave already added'})
                elif day in holidays:
                    skipped.append({'date': day.isoformat(), 'reason': f"Company holiday: {holidays[day]}"})
                elif day.weekday() in WEEKLY_OFF_WEEKDAYS:
                    skipped.append({'date': day.isoformat(), 'reason': 'Weekly off'})
                else:
                    created.append(Leave(
                        user=user, date=day, leave_type=leave_type, day_type=day_type,
                        reason=(data.get('reason') or '').strip()[:255], created_by=request.user,
                    ))
            Leave.objects.bulk_create(created)

        if not created:
            reason = skipped[0]['reason'] if skipped else 'No eligible days'
            return fail(f"No leave was added. {reason}.", errors={'skipped': skipped})

        log_action(request, 'Added leave', user.pk, f"Added {len(created)} leave day(s) for {user.name}")
        return ok(
            {'created': len(created), 'skipped': skipped},
            status.HTTP_201_CREATED,
        )

    @hr_access_required
    def destroy(self, request, pk=None):
        leave = Leave.objects.filter(pk=pk, user__in=employee_users()).select_related('user').first()
        if not leave:
            return fail("Leave not found.", status.HTTP_404_NOT_FOUND)
        locked = exited_lock(request, leave.user)
        if locked:
            return locked
        name, day = leave.user.name, leave.date
        leave.delete()
        log_action(request, 'Removed leave', pk, f"Removed leave of {name} on {day}")
        return ok({'deleted': True})


class HRUniversalLeaveViewSet(viewsets.ViewSet):
    """Company-wide holidays — apply to every employee."""

    @hr_access_required
    def list(self, request):
        holidays = UniversalLeave.objects.all().order_by('-date')
        return ok(UniversalLeaveSerializer(holidays, many=True).data)

    @hr_access_required
    def create(self, request):
        """POST {from_date, to_date?, title}"""
        title = (request.data.get('title') or '').strip()
        start = parse_date(str(request.data.get('from_date') or ''))
        end = parse_date(str(request.data.get('to_date') or '')) or start
        if not title:
            return fail("Title is required.")
        if not start:
            return fail("From date is required.")
        if end < start:
            return fail("To date cannot be before from date.")
        if (end - start).days > 92:
            return fail("A single entry can cover at most 93 days.")

        existing = set(UniversalLeave.objects.filter(date__range=(start, end)).values_list('date', flat=True))
        new_days = [d for d in daterange(start, end) if d not in existing]
        if not new_days:
            return fail("Holidays already exist for every selected date.")

        UniversalLeave.objects.bulk_create(
            [UniversalLeave(date=d, title=title[:150], created_by=request.user) for d in new_days]
        )
        log_action(request, 'Added universal leave', start, f"Added holiday '{title}' for {len(new_days)} day(s)")
        return ok(
            {'created': len(new_days), 'skipped': len(existing)},
            status.HTTP_201_CREATED,
        )

    @hr_access_required
    def destroy(self, request, pk=None):
        holiday = UniversalLeave.objects.filter(pk=pk).first()
        if not holiday:
            return fail("Holiday not found.", status.HTTP_404_NOT_FOUND)
        title, day = holiday.title, holiday.date
        holiday.delete()
        log_action(request, 'Removed universal leave', pk, f"Removed holiday '{title}' on {day}")
        return ok({'deleted': True})


# ── Employee self-service (profile page) ─────────────────────────────────────

def login_required_api(view_func):
    """Any signed-in user. Everything under it only ever touches request.user."""
    @wraps(view_func)
    def wrapped(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.active_user:
            return fail("Authentication required.", status.HTTP_401_UNAUTHORIZED)
        return view_func(self, request, *args, **kwargs)
    return wrapped


def parse_month(request):
    """(year, month) from ?year=&month=, defaulting to the current month."""
    today = timezone.localdate()
    try:
        year = int(request.query_params.get('year') or today.year)
        month = int(request.query_params.get('month') or today.month)
        date(year, month, 1)
    except (TypeError, ValueError):
        return today.year, today.month
    return year, month


class MyProfileViewSet(viewsets.ViewSet):

    @login_required_api
    def list(self, request):
        """GET — the signed-in user's employee details and this month's leave balance."""
        detail = employee_detail_for(request.user)
        detail = (
            EmployeeDetail.objects.select_related('user', 'reporting_to')
            .prefetch_related('emergency_contacts', 'user__held_assets').get(pk=detail.pk)
        )
        year, month = parse_month(request)
        return ok({
            'user': {
                'id': request.user.pk,
                'name': request.user.name,
                'user_code': request.user.user_id,
                'role': request.user.role,
            },
            'employee': EmployeeDetailSerializer(detail, context={'request': request}).data,
            'balance': leave_balance(request.user, year, month, detail),
            'month_label': date(year, month, 1).strftime('%B %Y'),
        })


class MyAttendanceViewSet(viewsets.ViewSet):

    @login_required_api
    def list(self, request):
        """GET ?from_date=&to_date= — the signed-in user's day-by-day attendance."""
        start, end, error = parse_range(request)
        if error:
            return fail(error)
        user = User.objects.select_related('employee_detail').get(pk=request.user.pk)
        rows, summary = build_attendance_rows(user, start, end)
        return ok({
            'from_date': start.isoformat(),
            'to_date': end.isoformat(),
            'half_day_cutoff': HALF_DAY_CUTOFF.strftime('%H:%M'),
            'rows': rows,
            'summary': summary,
        })


class MyLeaveViewSet(viewsets.ViewSet):

    @login_required_api
    def list(self, request):
        """GET ?year=&month= — my applications, leave days taken and the month's balance."""
        year, month = parse_month(request)
        applications = LeaveApplication.objects.filter(user=request.user).select_related('user', 'reviewed_by')
        leaves = Leave.objects.filter(user=request.user).select_related('user', 'created_by').order_by('-date')[:120]
        return ok({
            'applications': LeaveApplicationSerializer(applications, many=True).data,
            'leaves': LeaveSerializer(leaves, many=True).data,
            'balance': leave_balance(request.user, year, month),
            'month_label': date(year, month, 1).strftime('%B %Y'),
        })

    @login_required_api
    def create(self, request):
        """POST {from_date, to_date?, leave_type, day_type, reason}"""
        data = request.data
        today = timezone.localdate()

        start = parse_date(str(data.get('from_date') or ''))
        end = parse_date(str(data.get('to_date') or '')) or start
        if not start:
            return fail("Choose the leave date.")
        if end < start:
            return fail("To date cannot be before from date.")
        if start < today - timedelta(days=MAX_BACKDATE_DAYS):
            return fail(f"You can apply for leave up to {MAX_BACKDATE_DAYS} days in the past. Ask HR to add older leaves.")
        if (end - start).days + 1 > MAX_APPLICATION_DAYS:
            return fail(f"A single application can cover at most {MAX_APPLICATION_DAYS} days.")

        leave_type = data.get('leave_type') or 'casual'
        day_type = data.get('day_type') or 'full'
        if leave_type not in dict(LeaveApplication.TYPE_CHOICES):
            return fail("Invalid leave type.")
        if day_type not in dict(LeaveApplication.DAY_TYPE_CHOICES):
            return fail("Invalid day type.")
        if day_type == 'half' and start != end:
            return fail("A half-day leave can only be applied for a single date.")
        reason = (data.get('reason') or '').strip()
        if not reason:
            return fail("Please give a reason for the leave.")

        days = eligible_dates(start, end)
        if not days:
            return fail("The selected dates are weekly offs or company holidays, so no leave is needed.")

        taken = set(Leave.objects.filter(user=request.user, date__range=(start, end)).values_list('date', flat=True))
        clash = [d for d in days if d in taken]
        for application in LeaveApplication.objects.filter(
            user=request.user, status='pending', from_date__lte=end, to_date__gte=start,
        ):
            clash += [d for d in eligible_dates(application.from_date, application.to_date) if start <= d <= end]
        if clash:
            first = sorted(set(clash))[0]
            return fail(f"You already have a leave or a pending application for {first.strftime('%d %b %Y')}.")

        error = check_quota(request.user, leave_type, days, day_type)
        if error:
            return fail(error)

        application = LeaveApplication.objects.create(
            user=request.user, from_date=start, to_date=end, leave_type=leave_type,
            day_type=day_type, reason=reason[:255], days=day_weight(day_type) * len(days),
        )
        return ok(LeaveApplicationSerializer(application).data, status.HTTP_201_CREATED)

    @login_required_api
    def destroy(self, request, pk=None):
        """DELETE ��� withdraw one of my pending applications."""
        application = LeaveApplication.objects.filter(pk=pk, user=request.user).first()
        if not application:
            return fail("Application not found.", status.HTTP_404_NOT_FOUND)
        if application.status != 'pending':
            return fail("Only pending applications can be withdrawn. Ask HR to remove an approved leave.")
        application.status = 'cancelled'
        application.save(update_fields=['status'])
        return ok({'cancelled': True})


# ── HR: leave applications and monthly quotas ────────────────────────────────

class HRLeaveApplicationViewSet(viewsets.ViewSet):

    @hr_access_required
    def list(self, request):
        """GET ?status=pending|approved|rejected|cancelled&user_id= (default: everything)"""
        applications = LeaveApplication.objects.select_related('user', 'reviewed_by')
        status_filter = request.query_params.get('status')
        if status_filter:
            applications = applications.filter(status=status_filter)
        user_pk = request.query_params.get('user_id')
        if user_pk:
            applications = applications.filter(user_id=user_pk)

        data = LeaveApplicationSerializer(applications[:300], many=True).data
        for item, application in zip(data, applications[:300]):
            item['left_after_approval'] = None
            if application.status == 'pending' and application.leave_type in QUOTA_TYPES:
                balance = leave_balance(application.user, application.from_date.year, application.from_date.month)
                item['left_after_approval'] = balance[application.leave_type]['available']
        pending_count = LeaveApplication.objects.filter(status='pending').count()
        return ok(data, pending_count=pending_count)

    def _review(self, request, pk, new_status):
        application = LeaveApplication.objects.select_related('user').filter(pk=pk).first()
        if not application:
            return fail("Application not found.", status.HTTP_404_NOT_FOUND)
        if application.status != 'pending':
            return fail(f"This application is already {application.get_status_display().lower()}.")
        if application.user_id == request.user.pk and not (request.user.is_super_admin or request.user.role == 'admin'):
            return fail("You cannot review your own leave application.", status.HTTP_403_FORBIDDEN)
        locked = exited_lock(request, application.user)
        if locked:
            return locked

        note = (request.data.get('note') or '').strip()[:255]
        created = 0
        with transaction.atomic():
            if new_status == 'approved':
                dates = eligible_dates(application.from_date, application.to_date)
                existing = set(Leave.objects.filter(
                    user=application.user, date__range=(application.from_date, application.to_date),
                ).values_list('date', flat=True))
                rows = [
                    Leave(
                        user=application.user, date=day, leave_type=application.leave_type,
                        day_type=application.day_type, reason=application.reason, created_by=request.user,
                    )
                    for day in dates if day not in existing
                ]
                Leave.objects.bulk_create(rows)
                created = len(rows)
            application.status = new_status
            application.reviewed_by = request.user
            application.reviewed_at = timezone.now()
            application.review_note = note
            application.save()

        log_action(
            request, f"Leave {new_status}", application.pk,
            f"{new_status.title()} leave of {application.user.name} ({application.from_date} to {application.to_date})",
        )
        return ok({'status': new_status, 'leave_days_created': created})

    @action(detail=True, methods=['post'])
    @hr_access_required
    def approve(self, request, pk=None):
        return self._review(request, pk, 'approved')

    @action(detail=True, methods=['post'])
    @hr_access_required
    def reject(self, request, pk=None):
        return self._review(request, pk, 'rejected')


class HRLeaveQuotaViewSet(viewsets.ViewSet):
    """Monthly casual / sick leave allowance per employee."""

    @hr_access_required
    def list(self, request):
        """GET ?year=&month= — every active employee's allowance and usage for the month."""
        ensure_employee_details()
        year, month = parse_month(request)
        users = employee_users().filter(active_user=True).select_related('employee_detail').order_by('name')
        data = []
        for user in users:
            detail = user.employee_detail
            data.append({
                'user_id': user.pk,
                'name': user.name,
                'user_code': user.user_id,
                'department': detail.department,
                'position': detail.position,
                'casual_quota': float(detail.monthly_casual_leaves),
                'sick_quota': float(detail.monthly_sick_leaves),
                'balance': leave_balance(user, year, month, detail),
            })
        return ok(data, month_label=date(year, month, 1).strftime('%B %Y'))

    @hr_access_required
    def partial_update(self, request, pk=None):
        """PATCH {casual: n, sick: n} — pk is the user pk. Values are 0-31 in steps of 0.5."""
        user = employee_users().filter(pk=pk).first()
        if not user:
            return fail("Employee not found.", status.HTTP_404_NOT_FOUND)
        locked = exited_lock(request, user)
        if locked:
            return locked
        detail = employee_detail_for(user)

        values = {}
        for key, field in (('casual', 'monthly_casual_leaves'), ('sick', 'monthly_sick_leaves')):
            if request.data.get(key) in (None, ''):
                continue
            try:
                value = Decimal(str(request.data.get(key)))
            except InvalidOperation:
                return fail(f"{key.title()} leaves must be a number.")
            if value < 0 or value > 31 or (value * 2) % 1 != 0:
                return fail(f"{key.title()} leaves must be between 0 and 31, in steps of 0.5.")
            values[field] = value
        if not values:
            return fail("Nothing to update.")

        for field, value in values.items():
            setattr(detail, field, value)
        detail.save(update_fields=[*values.keys(), 'updated_at'])
        log_action(
            request, 'Updated leave quota', user.pk,
            f"Set monthly leaves for {user.name}: casual {detail.monthly_casual_leaves}, sick {detail.monthly_sick_leaves}",
        )
        today = timezone.localdate()
        return ok({
            'casual_quota': float(detail.monthly_casual_leaves),
            'sick_quota': float(detail.monthly_sick_leaves),
            'balance': leave_balance(user, today.year, today.month, detail),
        })


# ── Payroll ──────────────────────────────────────────────────────────────────

def _receipt_url(request, reimbursement):
    if not reimbursement.receipt:
        return None
    return request.build_absolute_uri(reimbursement.receipt.url)


def serialize_calculation(request, result):
    """Turns payroll_utils.compute() output into JSON-safe data for the HR preview."""
    included = result['included_reimbursements']
    return {
        'components': {name: float(value) for name, value in result['components'].items()},
        'total_salary': float(result['total_salary']),
        'per_day_rate': float(result['per_day_rate']),
        'lines': [{
            'leave_id': line['leave_id'],
            'date': line['date'].isoformat(),
            'leave_type': line['leave_type'],
            'leave_type_display': line['leave_type_display'],
            'day_type': line['day_type'],
            'days': float(line['days']),
            'reason': line['reason'],
            'amount': float(line['amount']),
            'is_extra': line['is_extra'],
            'deduct': line['deduct'],
        } for line in result['lines']],
        'leave_days_deducted': float(result['leave_days_deducted']),
        'leave_deduction': float(result['leave_deduction']),
        'tds_applicable': result['tds_applicable'],
        'tds_deducted': float(result['tds_deducted']),
        'salary_for_month': float(result['salary_for_month']),
        'reimbursements': [{
            'id': r.pk,
            'expense_date': r.expense_date.isoformat(),
            'description': r.description,
            'amount': float(r.amount),
            'receipt_url': _receipt_url(request, r),
            'included': r.pk in included,
        } for r in result['reimbursements']],
        'reimbursement_total': float(result['reimbursement_total']),
        'adjustment': float(result['adjustment']),
        'net_payable': float(result['net_payable']),
    }


def parse_payroll_inputs(request, existing=None):
    """
    Reads {deduct, reimbursement_ids, adjustment, adjustment_note, notes} from the body.
    Anything the caller leaves out falls back to what was saved on `existing`, so
    re-opening a generated payroll shows the same decisions HR made before.
    Returns (inputs, error).
    """
    data = request.data

    deduct_map = None
    raw_deduct = data.get('deduct')
    if isinstance(raw_deduct, dict):
        try:
            deduct_map = {int(k): bool(v) for k, v in raw_deduct.items()}
        except (TypeError, ValueError):
            return None, "Invalid leave selection."
    elif existing is not None:
        deduct_map = {line.leave_id: line.deduct for line in existing.leave_lines.all() if line.leave_id}

    raw_ids = data.get('reimbursement_ids')
    if isinstance(raw_ids, list):
        try:
            reimbursement_ids = [int(pk) for pk in raw_ids]
        except (TypeError, ValueError):
            return None, "Invalid reimbursement selection."
    elif existing is not None:
        reimbursement_ids = list(existing.reimbursements.values_list('pk', flat=True))
    else:
        reimbursement_ids = None

    raw_adjustment = data.get('adjustment')
    if raw_adjustment in (None, ''):
        adjustment = existing.adjustment_amount if existing is not None and 'adjustment' not in data else Decimal('0')
    else:
        try:
            adjustment = Decimal(str(raw_adjustment))
        except InvalidOperation:
            return None, "Adjustment must be a number."
        if abs(adjustment) > Decimal('99999999'):
            return None, "Adjustment is too large."

    note = data.get('adjustment_note')
    notes = data.get('notes')
    return {
        'deduct_map': deduct_map,
        'reimbursement_ids': reimbursement_ids,
        'adjustment': adjustment,
        'adjustment_note': existing.adjustment_note if note is None and existing is not None else (note or ''),
        'notes': existing.notes if notes is None and existing is not None else (notes or ''),
    }, None


def payroll_period(request):
    """(year, month) taken from the body, then the query string, else the current month."""
    today = timezone.localdate()
    source = request.data if request.method in ('POST', 'PATCH') else request.query_params
    try:
        year = int(source.get('year') or today.year)
        month = int(source.get('month') or today.month)
        date(year, month, 1)
    except (TypeError, ValueError):
        return None, None
    return year, month


def slip_response(payroll):
    pdf = generate_salary_slip(payroll)
    response = HttpResponse(pdf, content_type='application/pdf')
    filename = f"Salary_Slip_{payroll.user.user_id}_{payroll.year}-{payroll.month:02d}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


class HRPayrollViewSet(viewsets.ViewSet):
    """Monthly payroll: employee overview, preview, generate, mark paid, salary slip."""

    parser_classes = [JSONParser, FormParser, MultiPartParser]

    @hr_access_required
    def list(self, request):
        """GET ?year=&month= — every employee with this month's payroll state."""
        ensure_employee_details()
        year, month = payroll_period(request)
        if year is None:
            return fail("Choose a valid month.")
        first = date(year, month, 1)
        last = (first.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)

        payrolls = {p.user_id: p for p in Payroll.objects.filter(year=year, month=month)}
        pending = {
            row['user']: row
            for row in Reimbursement.objects.filter(payroll__isnull=True)
            .values('user').annotate(count=Count('id'), total=Sum('amount'))
        }

        rows = []
        users = employee_users().select_related('employee_detail').order_by('name')
        for user in users:
            detail = user.employee_detail
            payroll = payrolls.get(user.pk)
            if detail.joining_date and detail.joining_date > last and not payroll:
                continue
            if detail.is_exited and detail.last_working_day and detail.last_working_day < first and not payroll:
                continue
            pend = pending.get(user.pk)
            rows.append({
                'user_id': user.pk,
                'name': user.name,
                'user_code': user.user_id,
                'department': detail.department,
                'position': detail.position,
                'is_exited': detail.is_exited,
                'total_salary': float(detail.total_salary),
                'salary_set': detail.total_salary > 0,
                'payroll': {
                    'id': payroll.pk,
                    'status': payroll.status,
                    'status_display': payroll.get_status_display(),
                    'net_payable': float(payroll.net_payable),
                    'paid_on': payroll.paid_on.isoformat() if payroll.paid_on else None,
                } if payroll else None,
                'pending_reimbursements': pend['count'] if pend else 0,
                'pending_reimbursement_total': float(pend['total']) if pend else 0,
            })

        generated = [r['payroll'] for r in rows if r['payroll']]
        return ok(rows, month_label=first.strftime('%B %Y'), summary={
            'employees': len(rows),
            'generated': len(generated),
            'paid': sum(1 for p in generated if p['status'] == 'paid'),
            'net_total': round(sum(p['net_payable'] for p in generated), 2),
        })

    @hr_access_required
    def retrieve(self, request, pk=None):
        payroll = (
            Payroll.objects.select_related('user', 'generated_by')
            .prefetch_related('leave_lines', 'reimbursements').filter(pk=pk).first()
        )
        if not payroll:
            return fail("Payroll not found.", status.HTTP_404_NOT_FOUND)
        return ok(PayrollSerializer(payroll, context={'request': request}).data)

    @action(detail=False, methods=['post'])
    @hr_access_required
    def preview(self, request):
        """POST {user, year, month, deduct?, reimbursement_ids?, adjustment?} — calculates, saves nothing."""
        user = employee_users().filter(pk=request.data.get('user')).select_related('employee_detail').first()
        if not user:
            return fail("Employee not found.", status.HTTP_404_NOT_FOUND)
        year, month = payroll_period(request)
        if year is None:
            return fail("Choose a valid month.")

        existing = Payroll.objects.filter(user=user, year=year, month=month).first()
        inputs, error = parse_payroll_inputs(request, existing)
        if error:
            return fail(error)
        try:
            result = payroll_utils.compute(
                user, year, month, inputs['deduct_map'], inputs['reimbursement_ids'],
                inputs['adjustment'], existing=existing,
            )
        except PayrollError as exc:
            return fail(str(exc))

        data = serialize_calculation(request, result)
        data['existing'] = {
            'id': existing.pk,
            'status': existing.status,
            'adjustment_note': existing.adjustment_note,
            'notes': existing.notes,
        } if existing else None
        return ok(data, month_label=date(year, month, 1).strftime('%B %Y'))

    @action(detail=False, methods=['post'])
    @hr_access_required
    def generate(self, request):
        """POST — same body as preview plus {adjustment_note, notes}. Saves the payroll."""
        user = employee_users().filter(pk=request.data.get('user')).select_related('employee_detail').first()
        if not user:
            return fail("Employee not found.", status.HTTP_404_NOT_FOUND)
        locked = exited_lock(request, user)
        if locked:
            return locked
        year, month = payroll_period(request)
        if year is None:
            return fail("Choose a valid month.")

        existing = Payroll.objects.filter(user=user, year=year, month=month).first()
        inputs, error = parse_payroll_inputs(request, existing)
        if error:
            return fail(error)
        try:
            payroll = payroll_utils.generate(
                user, year, month, request.user,
                deduct_map=inputs['deduct_map'],
                reimbursement_ids=inputs['reimbursement_ids'],
                adjustment=inputs['adjustment'],
                adjustment_note=inputs['adjustment_note'],
                notes=inputs['notes'],
            )
        except PayrollError as exc:
            return fail(str(exc))

        log_action(
            request, 'Generated payroll', payroll.pk,
            f"{user.name} {year}-{month:02d}: net payable {payroll.net_payable}",
        )
        payroll = (
            Payroll.objects.select_related('user', 'generated_by')
            .prefetch_related('leave_lines', 'reimbursements').get(pk=payroll.pk)
        )
        return ok(
            PayrollSerializer(payroll, context={'request': request}).data,
            http_status=status.HTTP_200_OK if existing else status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['get'])
    @hr_access_required
    def history(self, request):
        """GET ?user= — every payroll generated for one employee, newest first."""
        user = employee_users().filter(pk=request.query_params.get('user')).first()
        if not user:
            return fail("Employee not found.", status.HTTP_404_NOT_FOUND)
        payrolls = Payroll.objects.filter(user=user).select_related('user', 'generated_by')
        data = [{
            'id': p.pk,
            'year': p.year,
            'month': p.month,
            'month_label': date(p.year, p.month, 1).strftime('%B %Y'),
            'total_salary': float(p.total_salary),
            'net_payable': float(p.net_payable),
            'status': p.status,
            'status_display': p.get_status_display(),
            'paid_on': p.paid_on.isoformat() if p.paid_on else None,
        } for p in payrolls]
        return ok(data)

    @action(detail=True, methods=['post'])
    @hr_access_required
    def mark_paid(self, request, pk=None):
        """POST {paid_on?} — locks the payroll. Defaults to today."""
        payroll = Payroll.objects.select_related('user').filter(pk=pk).first()
        if not payroll:
            return fail("Payroll not found.", status.HTTP_404_NOT_FOUND)
        locked = exited_lock(request, payroll.user)
        if locked:
            return locked
        if payroll.status == 'paid':
            return fail("This payroll is already marked paid.")

        raw = request.data.get('paid_on')
        paid_on = parse_date(str(raw)) if raw else timezone.localdate()
        if not paid_on:
            return fail("Invalid paid date.")
        if paid_on > timezone.localdate():
            return fail("Paid date cannot be in the future.")

        payroll.status = 'paid'
        payroll.paid_on = paid_on
        payroll.save(update_fields=['status', 'paid_on', 'updated_at'])
        log_action(request, 'Marked payroll paid', payroll.pk, f"{payroll.user.name} {payroll.year}-{payroll.month:02d} paid on {paid_on}")
        return ok({'id': payroll.pk, 'status': payroll.status, 'paid_on': paid_on.isoformat()})

    @action(detail=True, methods=['post'])
    @hr_access_required
    def reopen(self, request, pk=None):
        """POST — admins only. Moves a paid payroll back to generated so it can be corrected."""
        if not is_admin_user(request.user):
            return fail("Only an admin can reopen a paid payroll.", status.HTTP_403_FORBIDDEN)
        payroll = Payroll.objects.select_related('user').filter(pk=pk).first()
        if not payroll:
            return fail("Payroll not found.", status.HTTP_404_NOT_FOUND)
        if payroll.status != 'paid':
            return fail("This payroll is not marked paid.")
        payroll.status = 'generated'
        payroll.paid_on = None
        payroll.save(update_fields=['status', 'paid_on', 'updated_at'])
        log_action(request, 'Reopened payroll', payroll.pk, f"{payroll.user.name} {payroll.year}-{payroll.month:02d} reopened")
        return ok({'id': payroll.pk, 'status': payroll.status})

    @action(detail=True, methods=['get'])
    @hr_access_required
    def slip(self, request, pk=None):
        """GET — the salary slip as a PDF."""
        payroll = (
            Payroll.objects.select_related('user', 'user__employee_detail', 'generated_by')
            .prefetch_related('leave_lines', 'reimbursements').filter(pk=pk).first()
        )
        if not payroll:
            return fail("Payroll not found.", status.HTTP_404_NOT_FOUND)
        return slip_response(payroll)

    @hr_access_required
    def destroy(self, request, pk=None):
        """DELETE — removes an unpaid payroll; its reimbursements become payable again."""
        payroll = Payroll.objects.select_related('user').filter(pk=pk).first()
        if not payroll:
            return fail("Payroll not found.", status.HTTP_404_NOT_FOUND)
        locked = exited_lock(request, payroll.user)
        if locked:
            return locked
        label = f"{payroll.user.name} {payroll.year}-{payroll.month:02d}"
        try:
            payroll_utils.delete_payroll(payroll)
        except PayrollError as exc:
            return fail(str(exc))
        log_action(request, 'Deleted payroll', pk, f"Deleted payroll for {label}")
        return ok({'deleted': True})


class HRReimbursementViewSet(viewsets.ViewSet):
    """HR view of reimbursement claims, with the option to add one on an employee's behalf."""

    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @hr_access_required
    def list(self, request):
        """GET ?user=&status=unpaid|paid|all"""
        queryset = Reimbursement.objects.select_related('user', 'payroll')
        user_pk = request.query_params.get('user')
        if user_pk:
            queryset = queryset.filter(user_id=user_pk)
        state = request.query_params.get('status', 'unpaid')
        if state == 'unpaid':
            queryset = queryset.filter(payroll__isnull=True)
        elif state == 'paid':
            queryset = queryset.filter(payroll__isnull=False)
        data = ReimbursementSerializer(queryset[:300], many=True, context={'request': request}).data
        return ok(data)

    @hr_access_required
    def create(self, request):
        """POST multipart {user, expense_date, description, amount, receipt}"""
        user = employee_users().filter(pk=request.data.get('user')).select_related('employee_detail').first()
        if not user:
            return fail("Employee not found.", status.HTTP_404_NOT_FOUND)
        locked = exited_lock(request, user)
        if locked:
            return locked
        serializer = ReimbursementSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return fail(flatten_errors(serializer.errors), errors=serializer.errors)
        if not request.FILES.get('receipt'):
            return fail("Attach the receipt photo.")
        reimbursement = serializer.save(user=user)
        log_action(
            request, 'Added reimbursement', reimbursement.pk,
            f"{user.name}: {reimbursement.amount} for {reimbursement.description[:60]}",
        )
        return ok(ReimbursementSerializer(reimbursement, context={'request': request}).data, status.HTTP_201_CREATED)

    @hr_access_required
    def destroy(self, request, pk=None):
        reimbursement = Reimbursement.objects.select_related('user').filter(pk=pk).first()
        if not reimbursement:
            return fail("Reimbursement not found.", status.HTTP_404_NOT_FOUND)
        locked = exited_lock(request, reimbursement.user)
        if locked:
            return locked
        if reimbursement.payroll_id:
            return fail("This reimbursement is already part of a payroll. Delete or regenerate that payroll first.")
        reimbursement.receipt.delete(save=False)
        reimbursement.delete()
        log_action(request, 'Deleted reimbursement', pk, f"Deleted reimbursement of {reimbursement.user.name}")
        return ok({'deleted': True})


class MyReimbursementViewSet(viewsets.ViewSet):
    """An employee's own reimbursement claims."""

    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @login_required_api
    def list(self, request):
        queryset = Reimbursement.objects.filter(user=request.user).select_related('payroll')
        data = ReimbursementSerializer(queryset[:200], many=True, context={'request': request}).data
        unpaid = queryset.filter(payroll__isnull=True).aggregate(total=Sum('amount'), count=Count('id'))
        return ok(data, unpaid_total=float(unpaid['total'] or 0), unpaid_count=unpaid['count'])

    @login_required_api
    def create(self, request):
        """POST multipart {expense_date, description, amount, receipt}"""
        serializer = ReimbursementSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return fail(flatten_errors(serializer.errors), errors=serializer.errors)
        if not request.FILES.get('receipt'):
            return fail("Attach a photo of the receipt.")
        reimbursement = serializer.save(user=request.user)
        return ok(ReimbursementSerializer(reimbursement, context={'request': request}).data, status.HTTP_201_CREATED)

    @login_required_api
    def destroy(self, request, pk=None):
        reimbursement = Reimbursement.objects.filter(pk=pk, user=request.user).first()
        if not reimbursement:
            return fail("Reimbursement not found.", status.HTTP_404_NOT_FOUND)
        if reimbursement.payroll_id:
            return fail("This reimbursement is already part of a payroll and cannot be withdrawn.")
        reimbursement.receipt.delete(save=False)
        reimbursement.delete()
        return ok({'deleted': True})


class MyPayrollViewSet(viewsets.ViewSet):
    """An employee's own salary slips. Only payrolls HR has marked paid are visible."""

    @login_required_api
    def list(self, request):
        payrolls = Payroll.objects.filter(user=request.user, status='paid').select_related('user')
        data = [{
            'id': p.pk,
            'year': p.year,
            'month': p.month,
            'month_label': date(p.year, p.month, 1).strftime('%B %Y'),
            'total_salary': float(p.total_salary),
            'leave_deduction': float(p.leave_deduction),
            'tds_deducted': float(p.tds_deducted),
            'reimbursement_total': float(p.reimbursement_total),
            'net_payable': float(p.net_payable),
            'paid_on': p.paid_on.isoformat() if p.paid_on else None,
        } for p in payrolls]
        return ok(data)

    @action(detail=True, methods=['get'])
    @login_required_api
    def slip(self, request, pk=None):
        payroll = (
            Payroll.objects.select_related('user', 'user__employee_detail', 'generated_by')
            .prefetch_related('leave_lines', 'reimbursements')
            .filter(pk=pk, user=request.user, status='paid').first()
        )
        if not payroll:
            return fail("Salary slip not found.", status.HTTP_404_NOT_FOUND)
        return slip_response(payroll)
