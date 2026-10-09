"""
UserDetail/hr_views.py
──────────────────────
API endpoints for the HR page: employee profiles, attendance report,
per-employee leaves and company-wide (universal) leaves.

Access: HR role / `can_hr` permission, admins and super-admins.
"""

import json
from datetime import date, datetime, time, timedelta
from functools import wraps

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status, viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from .hr_serializers import (
    EmergencyContactSerializer,
    EmployeeDetailSerializer,
    LeaveSerializer,
    UniversalLeaveSerializer,
)
from .models import (
    ActivityLog,
    Attendance,
    EmergencyContact,
    EmployeeDetail,
    Leave,
    UniversalLeave,
    User,
)

HALF_DAY_CUTOFF = time(12, 0)   # first check-in after this time is a half day
WEEKLY_OFF_WEEKDAYS = (6,)      # Sunday (Mon=0)
MAX_RANGE_DAYS = 366


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
        if not request.user.is_authenticated:
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
        .prefetch_related('emergency_contacts')
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


def daterange(start, end):
    for offset in range((end - start).days + 1):
        yield start + timedelta(days=offset)


def local_iso(value):
    return timezone.localtime(value).isoformat() if value else None


def build_attendance_rows(user, start, end):
    """One row per calendar day with check-in/out, status and flags."""
    today = timezone.localdate()
    detail = getattr(user, 'employee_detail', None)
    joining = detail.joining_date if detail else None
    if joining and start < joining:
        start = joining

    records = {a.date: a for a in Attendance.objects.filter(user=user, date__range=(start, end))}
    leaves = {l.date: l for l in Leave.objects.filter(user=user, date__range=(start, end))}
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


# ── Attendance report ────────────────────────────────────────────────────────

class HRAttendanceViewSet(viewsets.ViewSet):

    @hr_access_required
    def list(self, request):
        """GET ?user_id=<pk>&from_date=&to_date= — day-by-day attendance for an employee."""
        user_pk = request.query_params.get('user_id')
        if not user_pk:
            return fail("user_id is required.")
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
