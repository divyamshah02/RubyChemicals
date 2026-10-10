"""
UserDetail/leave_utils.py
─────────────────────────
Leave quota and balance logic shared by the employee (profile) and HR endpoints.

Rules
  • Every employee gets a monthly quota of casual and sick leaves (EmployeeDetail).
  • The quota is per calendar month and does not carry forward.
  • A half day counts as 0.5.
  • Weekly offs and company holidays never consume leave.
  • Used = approved/HR-added `Leave` rows + still-pending applications (reserved).
  • Unpaid leave has no quota.
"""

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from .models import EmployeeDetail, Leave, LeaveApplication, UniversalLeave

WEEKLY_OFF_WEEKDAYS = (6,)   # Sunday (Mon=0)
QUOTA_TYPES = ('casual', 'sick')
HALF = Decimal('0.5')
FULL = Decimal('1')


def daterange(start, end):
    for offset in range((end - start).days + 1):
        yield start + timedelta(days=offset)


def day_weight(day_type):
    return HALF if day_type == 'half' else FULL


def month_bounds(year, month):
    return date(year, month, 1), date(year, month, monthrange(year, month)[1])


def holiday_dates(start, end):
    return set(UniversalLeave.objects.filter(date__range=(start, end)).values_list('date', flat=True))


def eligible_dates(start, end, holidays=None):
    """Days in the range that are neither a weekly off nor a company holiday."""
    if holidays is None:
        holidays = holiday_dates(start, end)
    return [
        day for day in daterange(start, end)
        if day.weekday() not in WEEKLY_OFF_WEEKDAYS and day not in holidays
    ]


def employee_detail_for(user):
    detail, _ = EmployeeDetail.objects.get_or_create(user=user, defaults={'full_name': user.name})
    return detail


def monthly_quota(detail, leave_type):
    value = detail.monthly_casual_leaves if leave_type == 'casual' else detail.monthly_sick_leaves
    return Decimal(value)


def used_in_month(user, leave_type, year, month, exclude_application_id=None):
    """Leave days of `leave_type` taken or reserved in the month."""
    first, last = month_bounds(year, month)

    used = sum(
        (day_weight(day_type) for day_type in Leave.objects.filter(
            user=user, leave_type=leave_type, date__range=(first, last),
        ).values_list('day_type', flat=True)),
        Decimal('0'),
    )

    pending = LeaveApplication.objects.filter(
        user=user, leave_type=leave_type, status='pending',
        from_date__lte=last, to_date__gte=first,
    )
    if exclude_application_id:
        pending = pending.exclude(pk=exclude_application_id)

    holidays = holiday_dates(first, last)
    for application in pending:
        start = max(application.from_date, first)
        end = min(application.to_date, last)
        used += day_weight(application.day_type) * len(eligible_dates(start, end, holidays))
    return used


def leave_balance(user, year, month, detail=None):
    """{'casual': {...}, 'sick': {...}} with quota / used / available as floats."""
    detail = detail or employee_detail_for(user)
    balance = {}
    for leave_type in QUOTA_TYPES:
        quota = monthly_quota(detail, leave_type)
        used = used_in_month(user, leave_type, year, month)
        balance[leave_type] = {
            'quota': float(quota),
            'used': float(used),
            'available': float(max(quota - used, Decimal('0'))),
        }
    return balance


def months_in(days):
    """Ordered unique (year, month) pairs for a list of dates."""
    seen = []
    for day in days:
        key = (day.year, day.month)
        if key not in seen:
            seen.append(key)
    return seen


def check_quota(user, leave_type, days, day_type, exclude_application_id=None):
    """
    Returns an error string if applying for `days` of `leave_type` would exceed a month's
    quota, otherwise None. Unpaid leave is never checked.
    """
    if leave_type not in QUOTA_TYPES:
        return None
    detail = employee_detail_for(user)
    quota = monthly_quota(detail, leave_type)
    weight = day_weight(day_type)

    for year, month in months_in(days):
        requested = weight * sum(1 for d in days if (d.year, d.month) == (year, month))
        used = used_in_month(user, leave_type, year, month, exclude_application_id)
        available = max(quota - used, Decimal('0'))
        if requested > available:
            label = date(year, month, 1).strftime('%B %Y')
            return (
                f"Not enough {leave_type} leave for {label}: you asked for {requested:g} day(s) "
                f"but only {available:g} of {quota:g} is available. "
                f"Choose fewer days or apply for unpaid leave."
            )
    return None
