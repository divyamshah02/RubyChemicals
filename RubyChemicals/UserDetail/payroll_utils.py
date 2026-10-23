"""
UserDetail/payroll_utils.py
───────────────────────────
Monthly payroll calculation shared by the HR preview and the final generation.

Rules
  • TOTAL SALARY = basic + DA + HRA + LTA + EPF + gratuity + ESIC (monthly).
  • One leave day is deducted at TOTAL SALARY / 30, regardless of how many days the
    calendar month has. A half day is deducted at half of that.
  • A leave is pre-ticked for deduction only when it is *extra*: unpaid leave, or casual /
    sick leave beyond the month's quota. HR can tick or untick every leave individually.
  • TDS is deducted only when the employee is marked TDS applicable.
  • Unpaid reimbursements can be added to the month, individually chosen by HR.
  • HR can add a signed manual adjustment with a note.
  • A generated payroll is a snapshot; later salary changes never alter it.
"""

from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone

from .leave_utils import QUOTA_TYPES, day_weight, employee_detail_for, month_bounds, monthly_quota
from .models import Leave, Payroll, PayrollLeaveLine, Reimbursement

DAYS_IN_PAYROLL_MONTH = Decimal('30')
CENT = Decimal('0.01')
ZERO = Decimal('0')


class PayrollError(Exception):
    """Raised for any problem the HR user should read as a plain message."""


def money(value):
    return Decimal(value or 0).quantize(CENT, rounding=ROUND_HALF_UP)


def validate_period(detail, year, month):
    """Raises PayrollError if a payroll cannot be run for this employee and month."""
    if not (2000 <= year <= 2100) or not (1 <= month <= 12):
        raise PayrollError("Choose a valid month.")

    first, last = month_bounds(year, month)
    today = timezone.localdate()
    if (year, month) > (today.year, today.month):
        raise PayrollError("Payroll cannot be generated for a future month.")
    if detail.joining_date and last < detail.joining_date:
        raise PayrollError("The employee had not joined yet in this month.")
    if detail.is_exited and detail.last_working_day and first > detail.last_working_day:
        raise PayrollError("The employee had already exited before this month.")
    if detail.total_salary <= 0:
        raise PayrollError("Salary structure is not set for this employee. Add it in Employee details first.")


def build_leave_lines(user, detail, year, month):
    """
    One entry per leave in the month, oldest first, with the default deduct decision.
    Quota is consumed in date order, so the *later* leaves are the extra ones.
    """
    first, last = month_bounds(year, month)
    rate = money(detail.total_salary / DAYS_IN_PAYROLL_MONTH)
    remaining = {leave_type: monthly_quota(detail, leave_type) for leave_type in QUOTA_TYPES}

    lines = []
    for leave in Leave.objects.filter(user=user, date__range=(first, last)).order_by('date'):
        weight = day_weight(leave.day_type)
        if leave.leave_type in QUOTA_TYPES:
            if weight <= remaining[leave.leave_type]:
                remaining[leave.leave_type] -= weight
                extra = False
            else:
                remaining[leave.leave_type] = ZERO
                extra = True
        else:
            extra = leave.leave_type == 'unpaid'

        lines.append({
            'leave_id': leave.pk,
            'date': leave.date,
            'leave_type': leave.leave_type,
            'leave_type_display': leave.get_leave_type_display(),
            'day_type': leave.day_type,
            'days': weight,
            'reason': leave.reason,
            'amount': money(rate * weight),
            'is_extra': extra,
            'deduct': extra,
        })
    return lines, rate


def unpaid_reimbursements(user, payroll=None):
    """Reimbursements not yet paid out (plus those already on `payroll`, when regenerating)."""
    queryset = Reimbursement.objects.filter(user=user)
    if payroll is not None:
        from django.db.models import Q
        queryset = queryset.filter(Q(payroll__isnull=True) | Q(payroll=payroll))
    else:
        queryset = queryset.filter(payroll__isnull=True)
    return queryset.order_by('expense_date', 'created_at')


def compute(user, year, month, deduct_map=None, reimbursement_ids=None, adjustment=0, existing=None):
    """
    Pure calculation (nothing is saved).

    deduct_map        {leave_id: bool} overriding the default decision per leave
    reimbursement_ids iterable of reimbursement pks to include; None means include all unpaid
    adjustment        signed manual amount added to the payable total
    """
    detail = employee_detail_for(user)
    validate_period(detail, year, month)

    lines, rate = build_leave_lines(user, detail, year, month)
    deduct_map = deduct_map or {}
    for line in lines:
        if line['leave_id'] in deduct_map:
            line['deduct'] = bool(deduct_map[line['leave_id']])

    reimbursements = list(unpaid_reimbursements(user, existing))
    if reimbursement_ids is None:
        included = {r.pk for r in reimbursements}
    else:
        included = {int(pk) for pk in reimbursement_ids}
        unknown = included - {r.pk for r in reimbursements}
        if unknown:
            raise PayrollError("One of the selected reimbursements is not available for this employee.")

    components = {name: money(getattr(detail, name)) for name in detail.SALARY_COMPONENTS}
    total_salary = sum(components.values(), ZERO)

    leave_days = sum((line['days'] for line in lines if line['deduct']), ZERO)
    leave_deduction = sum((line['amount'] for line in lines if line['deduct']), ZERO)
    tds = money(detail.tds_amount) if detail.tds_applicable else ZERO

    salary_for_month = max(total_salary - leave_deduction - tds, ZERO)
    reimbursement_total = sum((money(r.amount) for r in reimbursements if r.pk in included), ZERO)
    adjustment = money(adjustment)
    net_payable = max(salary_for_month + reimbursement_total + adjustment, ZERO)

    return {
        'detail': detail,
        'components': components,
        'total_salary': total_salary,
        'per_day_rate': rate,
        'lines': lines,
        'leave_days_deducted': leave_days,
        'leave_deduction': leave_deduction,
        'tds_applicable': detail.tds_applicable,
        'tds_deducted': tds,
        'salary_for_month': salary_for_month,
        'reimbursements': reimbursements,
        'included_reimbursements': included,
        'reimbursement_total': reimbursement_total,
        'adjustment': adjustment,
        'net_payable': net_payable,
    }


@transaction.atomic
def generate(user, year, month, generated_by, deduct_map=None, reimbursement_ids=None,
             adjustment=0, adjustment_note='', notes=''):
    """Creates the payroll, or re-generates it while it is still unpaid."""
    payroll = Payroll.objects.select_for_update().filter(user=user, year=year, month=month).first()
    if payroll and payroll.status == 'paid':
        raise PayrollError("This payroll is already marked paid and can no longer be changed.")

    result = compute(user, year, month, deduct_map, reimbursement_ids, adjustment, existing=payroll)
    if result['adjustment'] != 0 and not (adjustment_note or '').strip():
        raise PayrollError("Add a note explaining the manual adjustment.")

    fields = {
        **result['components'],
        'total_salary': result['total_salary'],
        'per_day_rate': result['per_day_rate'],
        'leave_days_deducted': result['leave_days_deducted'],
        'leave_deduction': result['leave_deduction'],
        'tds_applicable': result['tds_applicable'],
        'tds_deducted': result['tds_deducted'],
        'salary_for_month': result['salary_for_month'],
        'reimbursement_total': result['reimbursement_total'],
        'adjustment_amount': result['adjustment'],
        'adjustment_note': (adjustment_note or '').strip()[:255],
        'net_payable': result['net_payable'],
        'notes': (notes or '').strip()[:255],
        'generated_by': generated_by,
        'generated_at': timezone.now(),
    }

    if payroll:
        for name, value in fields.items():
            setattr(payroll, name, value)
        payroll.save()
        payroll.leave_lines.all().delete()
        payroll.reimbursements.update(payroll=None)
    else:
        payroll = Payroll.objects.create(user=user, year=year, month=month, **fields)

    PayrollLeaveLine.objects.bulk_create([
        PayrollLeaveLine(
            payroll=payroll, leave_id=line['leave_id'], date=line['date'],
            leave_type=line['leave_type'], day_type=line['day_type'], days=line['days'],
            reason=line['reason'], deduct=line['deduct'],
            amount=line['amount'] if line['deduct'] else ZERO,
        )
        for line in result['lines']
    ])
    Reimbursement.objects.filter(pk__in=result['included_reimbursements']).update(payroll=payroll)
    return payroll


@transaction.atomic
def delete_payroll(payroll):
    """Removes an unpaid payroll and frees its reimbursements so they can be paid later."""
    if payroll.status == 'paid':
        raise PayrollError("A paid payroll cannot be deleted.")
    payroll.reimbursements.update(payroll=None)
    payroll.delete()
