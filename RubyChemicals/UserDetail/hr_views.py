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
from django.db.models import Q
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
    UniversalLeave,
    User,
)

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


# ── Employee self-service (profile page) ─────────────────────────────────────

def login_required_api(view_func):
    """Any signed-in user. Everything under it only ever touches request.user."""
    @wraps(view_func)
    def wrapped(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
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
            .prefetch_related('emergency_contacts').get(pk=detail.pk)
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
        """DELETE — withdraw one of my pending applications."""
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
