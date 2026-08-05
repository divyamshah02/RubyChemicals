from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction
from django.utils import timezone
from django.db.models import Q

from .models import (
    Lead, LeadCallRecord,
    LeadSubDepartment, SubDeptStockItem,
    Quotation, QuotationItem,
    SampleRequisite, SampleRequisiteItem,
    ApplicationArea, ApplicationSystemProduct,
    ApplicationSystemProductItem, ApplicationFixedItem,
    ApplicationLead,
)
from .serializers import (
    LeadSubDepartmentSerializer,
    SubDeptStockItemSerializer,
    LeadSerializer, LeadListSerializer,
    QuotationSerializer, QuotationListSerializer, QuotationItemSerializer,
    SampleRequisiteSerializer, SampleRequisiteListSerializer,
    SampleRequisiteItemSerializer,
    ApplicationAreaSerializer, ApplicationAreaListSerializer,
    ApplicationSystemProductSerializer, ApplicationSystemProductItemSerializer,
    ApplicationFixedItemSerializer, ApplicationLeadSerializer,
)
from UserDetail.models import ActivityLog
from utils.decorators import handle_exceptions, check_authentication


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _has_leads_access(user):
    return user.is_super_admin or user.has_plugin_access('can_leads') or user.role == 'sales'


def _std_response(success, data=None, error=None, http_status=200):
    return Response({
        "success": success,
        "user_not_logged_in": False,
        "user_unauthorized": False,
        "data": data,
        "error": error,
    }, status=http_status)


def _is_admin(user):
    return user.is_super_admin or user.role == 'admin'


def _user_sub_dept(user):
    """Return the user's assigned leads sub-department or None."""
    return getattr(user, 'leads_sub_department', None)


# ─────────────────────────────────────────────────────────────────────────────
# 1. LeadSubDepartmentViewSet
# ─────────────────────────────────────────────────────────────────────────────

class LeadSubDepartmentViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        """List all active sub-departments (visible to all authenticated users)."""
        depts = LeadSubDepartment.objects.filter(is_active=True)
        return _std_response(True, LeadSubDepartmentSerializer(depts, many=True).data)

    @handle_exceptions
    @check_authentication()
    def retrieve(self, request, pk=None):
        try:
            dept = LeadSubDepartment.objects.get(pk=pk)
            return _std_response(True, LeadSubDepartmentSerializer(dept).data)
        except LeadSubDepartment.DoesNotExist:
            return _std_response(False, error="Sub-department not found", http_status=404)

    @handle_exceptions
    @check_authentication(required_role='admin')
    def create(self, request):
        serializer = LeadSubDepartmentSerializer(data=request.data)
        if not serializer.is_valid():
            return _std_response(False, error=serializer.errors, http_status=400)
        dept = serializer.save()
        ActivityLog.objects.create(
            user=request.user, action="CREATE",
            model_name="LeadSubDepartment", record_id=str(dept.id),
            description=f"Created sub-department {dept.name}"
        )
        return _std_response(True, LeadSubDepartmentSerializer(dept).data, http_status=201)

    @handle_exceptions
    @check_authentication(required_role='admin')
    def update(self, request, pk=None):
        try:
            dept = LeadSubDepartment.objects.get(pk=pk)
        except LeadSubDepartment.DoesNotExist:
            return _std_response(False, error="Sub-department not found", http_status=404)
        serializer = LeadSubDepartmentSerializer(dept, data=request.data, partial=True)
        if not serializer.is_valid():
            return _std_response(False, error=serializer.errors, http_status=400)
        serializer.save()
        return _std_response(True, serializer.data)

    @handle_exceptions
    @check_authentication(required_role='admin')
    def destroy(self, request, pk=None):
        try:
            dept = LeadSubDepartment.objects.get(pk=pk)
            dept.is_active = False
            dept.save()
            return _std_response(True, {"id": dept.id})
        except LeadSubDepartment.DoesNotExist:
            return _std_response(False, error="Sub-department not found", http_status=404)


# ─────────────────────────────────────────────────────────────────────────────
# 2. SubDeptStockItemViewSet
# ─────────────────────────────────────────────────────────────────────────────

class SubDeptStockItemViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        """
        List stock items for a sub-department.
        Params: ?sub_department=<id>  (required for non-admin users)
        """
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)

        sub_dept_id = request.query_params.get('sub_department')

        if not sub_dept_id:
            if not _is_admin(request.user):
                sub_dept = _user_sub_dept(request.user)
                if not sub_dept:
                    return _std_response(False, error="sub_department parameter required", http_status=400)
                sub_dept_id = sub_dept.id
            else:
                items = SubDeptStockItem.objects.filter(is_active=True).select_related('sub_department')
                return _std_response(True, SubDeptStockItemSerializer(items, many=True).data)

        items = SubDeptStockItem.objects.filter(
            sub_department_id=sub_dept_id, is_active=True
        ).select_related('sub_department')
        return _std_response(True, SubDeptStockItemSerializer(items, many=True).data)

    @handle_exceptions
    @check_authentication()
    def retrieve(self, request, pk=None):
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)
        try:
            item = SubDeptStockItem.objects.get(pk=pk, is_active=True)
            return _std_response(True, SubDeptStockItemSerializer(item).data)
        except SubDeptStockItem.DoesNotExist:
            return _std_response(False, error="Item not found", http_status=404)

    @handle_exceptions
    @check_authentication()
    def create(self, request):
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)
        serializer = SubDeptStockItemSerializer(data=request.data)
        if not serializer.is_valid():
            return _std_response(False, error=serializer.errors, http_status=400)
        item = serializer.save()
        ActivityLog.objects.create(
            user=request.user, action="CREATE",
            model_name="SubDeptStockItem", record_id=str(item.id),
            description=f"Created stock item {item.product_name} for {item.sub_department.name}"
        )
        return _std_response(True, SubDeptStockItemSerializer(item).data, http_status=201)

    @handle_exceptions
    @check_authentication()
    def update(self, request, pk=None):
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)
        try:
            item = SubDeptStockItem.objects.get(pk=pk)
        except SubDeptStockItem.DoesNotExist:
            return _std_response(False, error="Item not found", http_status=404)
        serializer = SubDeptStockItemSerializer(item, data=request.data, partial=True)
        if not serializer.is_valid():
            return _std_response(False, error=serializer.errors, http_status=400)
        serializer.save()
        return _std_response(True, serializer.data)

    @handle_exceptions
    @check_authentication()
    def destroy(self, request, pk=None):
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)
        try:
            item = SubDeptStockItem.objects.get(pk=pk)
            item.is_active = False
            item.save()
            return _std_response(True, {"id": item.id})
        except SubDeptStockItem.DoesNotExist:
            return _std_response(False, error="Item not found", http_status=404)


# ─────────────────────────────────────────────────────────────────────────────
# 3. LeadViewSet  (was DeptLeadViewSet — now operates on the Lead model)
#    URL prefix remains: /leads/dept-leads/  (backward-compatible)
# ─────────────────────────────────────────────────────────────────────────────

class DeptLeadViewSet(viewsets.ViewSet):
    """
    Thin alias kept so urls.py / frontend paths do not need changing.
    Internally operates entirely on the Lead model.
    Sub-department scoping applied for non-admin users.
    """

    def _scoped_qs(self, user):
        """Return queryset scoped to user's sub-department unless admin."""
        qs = Lead.objects.filter(is_active=True).select_related(
            'sub_department', 'created_by'
        )
        if _is_admin(user):
            return qs
        sub_dept = _user_sub_dept(user)
        if sub_dept:
            return qs.filter(sub_department=sub_dept)
        # If user has no sub-dept assigned, fall back to showing all leads
        # that have a sub_department (i.e. the new-style leads)
        return qs.filter(sub_department__isnull=False)

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)

        qs = self._scoped_qs(request.user)

        sub_dept_id = request.query_params.get('sub_department')
        status_val  = request.query_params.get('status')
        q           = request.query_params.get('q', '')
        user_id_val = request.query_params.get('user_id')

        if sub_dept_id:
            qs = qs.filter(sub_department_id=sub_dept_id)
        if status_val:
            qs = qs.filter(lead_status=status_val)
        if q:
            qs = qs.filter(
                Q(party_name__icontains=q) |
                Q(contact_person__icontains=q) |
                Q(mobile_number__icontains=q)
            )
        if user_id_val:
            qs = qs.filter(created_by__user_id=user_id_val)

        return _std_response(True, LeadListSerializer(qs, many=True).data)

    @handle_exceptions
    @check_authentication()
    def retrieve(self, request, pk=None):
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)
        try:
            lead = Lead.objects.select_related(
                'sub_department', 'created_by'
            ).get(pk=pk, is_active=True)
            return _std_response(True, LeadSerializer(lead).data)
        except Lead.DoesNotExist:
            return _std_response(False, error="Lead not found", http_status=404)

    @handle_exceptions
    @check_authentication()
    def create(self, request):
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)

        data = request.data.copy()

        # Auto-assign sub_department from user profile if not provided
        if not data.get('sub_department'):
            sub_dept = _user_sub_dept(request.user)
            if sub_dept:
                data['sub_department'] = sub_dept.id

        serializer = LeadSerializer(data=data)
        if not serializer.is_valid():
            return _std_response(False, error=serializer.errors, http_status=400)

        lead = serializer.save(created_by=request.user)
        ActivityLog.objects.create(
            user=request.user, action="CREATE",
            model_name="Lead", record_id=str(lead.lead_id),
            description=f"Created lead {lead.lead_id} - {lead.party_name}"
        )
        return _std_response(True, LeadSerializer(lead).data, http_status=201)

    @handle_exceptions
    @check_authentication()
    def update(self, request, pk=None):
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)
        try:
            lead = Lead.objects.get(pk=pk, is_active=True)
        except Lead.DoesNotExist:
            return _std_response(False, error="Lead not found", http_status=404)

        serializer = LeadSerializer(lead, data=request.data, partial=True)
        if not serializer.is_valid():
            return _std_response(False, error=serializer.errors, http_status=400)
        lead = serializer.save()
        ActivityLog.objects.create(
            user=request.user, action="UPDATE",
            model_name="Lead", record_id=str(lead.lead_id),
            description=f"Updated lead {lead.lead_id}"
        )
        return _std_response(True, LeadSerializer(lead).data)

    @handle_exceptions
    @check_authentication()
    def destroy(self, request, pk=None):
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)
        try:
            lead = Lead.objects.get(pk=pk, is_active=True)
            lead.is_active = False
            lead.save()
            ActivityLog.objects.create(
                user=request.user, action="DELETE",
                model_name="Lead", record_id=str(lead.lead_id),
                description=f"Deleted lead {lead.lead_id}"
            )
            return _std_response(True, {"lead_id": lead.lead_id})
        except Lead.DoesNotExist:
            return _std_response(False, error="Lead not found", http_status=404)


# ─────────────────────────────────────────────────────────────────────────────
# 4. QuotationViewSet
# ─────────────────────────────────────────────────────────────────────────────

class QuotationViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)

        qs = Quotation.objects.filter(is_active=True).select_related(
            'lead', 'lead__sub_department', 'created_by'
        )

        if not _is_admin(request.user):
            sub_dept = _user_sub_dept(request.user)
            if sub_dept:
                qs = qs.filter(lead__sub_department=sub_dept)

        lead_id = request.query_params.get('lead')
        if lead_id:
            qs = qs.filter(lead_id=lead_id)

        return _std_response(True, QuotationListSerializer(qs, many=True).data)

    @handle_exceptions
    @check_authentication()
    def retrieve(self, request, pk=None):
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)
        try:
            q = Quotation.objects.prefetch_related('items__stock_item').get(pk=pk)
            return _std_response(True, QuotationSerializer(q).data)
        except Quotation.DoesNotExist:
            return _std_response(False, error="Quotation not found", http_status=404)

    # @handle_exceptions
    # @check_authentication()
    # def create(self, request):
    #     """
    #     Create a quotation with line items.

    #     Expected payload:
    #     {
    #       "lead": <lead pk (integer id, not lead_id)>,
    #       "quotation_date": "YYYY-MM-DD",
    #       "status": "draft",
    #       "billing_address": "...",
    #       "shipping_address": "...",
    #       "notes": "...",
    #       "items": [
    #         {"stock_item": <id>, "quantity": 2, "rate": 500.00, "uom": "NOS", "description": ""},
    #         ...
    #       ]
    #     }
    #     """
    #     if not _has_leads_access(request.user):
    #         return _std_response(False, error="Unauthorized", http_status=403)

    #     items_data = request.data.get('items', [])
    #     serializer = QuotationSerializer(data=request.data)
    #     if not serializer.is_valid():
    #         return _std_response(False, error=serializer.errors, http_status=400)

    #     with transaction.atomic():
    #         quotation = serializer.save(created_by=request.user)
    #         for item_data in items_data:
    #             stock_item = SubDeptStockItem.objects.get(pk=item_data['stock_item'])
    #             uom = item_data.get('uom') or stock_item.uom
    #             QuotationItem.objects.create(
    #                 quotation=quotation,
    #                 stock_item=stock_item,
    #                 quantity=item_data.get('quantity', 1),
    #                 rate=item_data.get('rate', stock_item.rate or 0),
    #                 uom=uom,
    #                 description=item_data.get('description', ''),
    #             )

    #     ActivityLog.objects.create(
    #         user=request.user, action="CREATE",
    #         model_name="Quotation", record_id=quotation.quotation_no,
    #         description=f"Created quotation {quotation.quotation_no}"
    #     )
    #     q = Quotation.objects.prefetch_related('items__stock_item').get(pk=quotation.pk)
    #     return _std_response(True, QuotationSerializer(q).data, http_status=201)

    @handle_exceptions
    @check_authentication()
    def create(self, request):
        """
        Create a quotation with items.

        Each item in ``items`` may be:
        • a catalogue item:  {"stock_item": <id>, "quantity": 1, "rate": 100, "uom": "NOS"}
        • a free-text item:  {"product_name": "Custom", "hsn_code": "...", "quantity": 1, "rate": 100, "uom": "NOS", "warranty": "1Y"}
        """
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)

        items_data = request.data.get('items', [])
        serializer = QuotationSerializer(data=request.data)
        if not serializer.is_valid():
            return _std_response(False, error=serializer.errors, http_status=400)

        with transaction.atomic():
            qt = serializer.save(created_by=request.user)
            for item_data in items_data:
                stock_item_id = item_data.get('stock_item')
                stock_item = None
                if stock_item_id:
                    stock_item = SubDeptStockItem.objects.get(pk=stock_item_id)
                    uom      = item_data.get('uom') or stock_item.uom
                    rate     = item_data.get('rate', stock_item.rate)
                    hsn_code = item_data.get('hsn_code', stock_item.hsn_code)
                    warranty = item_data.get('warranty', stock_item.warranty or '')
                    pname    = ''
                else:
                    uom      = item_data.get('uom', '')
                    rate     = item_data.get('rate', 0)
                    hsn_code = item_data.get('hsn_code', '')
                    warranty = item_data.get('warranty', '')
                    pname    = item_data.get('product_name', '')

                QuotationItem.objects.create(
                    quotation    = qt,
                    stock_item   = stock_item,
                    product_name = pname,
                    hsn_code     = hsn_code,
                    quantity     = item_data.get('quantity', 1),
                    rate         = rate,
                    uom          = uom,
                    warranty     = warranty,
                    scope        = item_data.get('scope', ''),   # ← ADD THIS
                    application_area = item_data.get('application_area', None),
                    description  = item_data.get('description', ''),
                )

        ActivityLog.objects.create(
            user=request.user, action="CREATE",
            model_name="Quotation", record_id=qt.quotation_no,
            description=f"Created Quotation {qt.quotation_no}"
        )
        qt = Quotation.objects.prefetch_related('items__stock_item').get(pk=qt.pk)
        return _std_response(True, QuotationSerializer(qt).data, http_status=201)


    @handle_exceptions
    @check_authentication()
    def update(self, request, pk=None):
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)
        try:
            qt = Quotation.objects.get(pk=pk, is_active=True)
        except Quotation.DoesNotExist:
            return _std_response(False, error="Quotation not found", http_status=404)

        items_data = request.data.get('items', None)
        serializer = QuotationSerializer(qt, data=request.data, partial=True)
        if not serializer.is_valid():
            return _std_response(False, error=serializer.errors, http_status=400)

        with transaction.atomic():
            qt = serializer.save()
            if items_data is not None:
                qt.items.all().update(is_active=False)
                for item_data in items_data:
                    stock_item_id = item_data.get('stock_item')
                    stock_item = None
                    if stock_item_id:
                        stock_item = SubDeptStockItem.objects.get(pk=stock_item_id)
                        uom      = item_data.get('uom') or stock_item.uom
                        rate     = item_data.get('rate', stock_item.rate)
                        hsn_code = item_data.get('hsn_code', stock_item.hsn_code)
                        warranty = item_data.get('warranty', stock_item.warranty or '')
                        pname    = ''
                    else:
                        uom      = item_data.get('uom', '')
                        rate     = item_data.get('rate', 0)
                        hsn_code = item_data.get('hsn_code', '')
                        warranty = item_data.get('warranty', '')
                        pname    = item_data.get('product_name', '')

                    QuotationItem.objects.create(
                        quotation    = qt,
                        stock_item   = stock_item,
                        product_name = pname,
                        hsn_code     = hsn_code,
                        quantity     = item_data.get('quantity', 1),
                        rate         = rate,
                        uom          = uom,
                        warranty     = warranty,
                        scope        = item_data.get('scope', ''),   # ← ADD THIS
                        application_area = item_data.get('application_area', None),
                        description  = item_data.get('description', ''),
                    )

        qt = Quotation.objects.prefetch_related('items__stock_item').get(pk=qt.pk)
        return _std_response(True, QuotationSerializer(qt).data)

    # @handle_exceptions
    # @check_authentication()
    # def update(self, request, pk=None):
    #     if not _has_leads_access(request.user):
    #         return _std_response(False, error="Unauthorized", http_status=403)
    #     try:
    #         quotation = Quotation.objects.get(pk=pk, is_active=True)
    #     except Quotation.DoesNotExist:
    #         return _std_response(False, error="Quotation not found", http_status=404)

    #     items_data = request.data.get('items', None)
    #     serializer = QuotationSerializer(quotation, data=request.data, partial=True)
    #     if not serializer.is_valid():
    #         return _std_response(False, error=serializer.errors, http_status=400)

    #     with transaction.atomic():
    #         quotation = serializer.save()
    #         if items_data is not None:
    #             quotation.items.all().update(is_active=False)
    #             for item_data in items_data:
    #                 stock_item = SubDeptStockItem.objects.get(pk=item_data['stock_item'])
    #                 uom = item_data.get('uom') or stock_item.uom
    #                 QuotationItem.objects.create(
    #                     quotation=quotation,
    #                     stock_item=stock_item,
    #                     quantity=item_data.get('quantity', 1),
    #                     rate=item_data.get('rate', stock_item.rate or 0),
    #                     uom=uom,
    #                     description=item_data.get('description', ''),
    #                 )

    #     q = Quotation.objects.prefetch_related('items__stock_item').get(pk=quotation.pk)
    #     return _std_response(True, QuotationSerializer(q).data)

    @handle_exceptions
    @check_authentication()
    def destroy(self, request, pk=None):
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)
        try:
            quotation = Quotation.objects.get(pk=pk)
            quotation.is_active = False
            quotation.save()
            return _std_response(True, {"quotation_no": quotation.quotation_no})
        except Quotation.DoesNotExist:
            return _std_response(False, error="Quotation not found", http_status=404)


# ─────────────────────────────────────────────────────────────────────────────
# 5. SampleRequisiteViewSet
# ─────────────────────────────────────────────────────────────────────────────

class SampleRequisiteViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)

        qs = SampleRequisite.objects.filter(is_active=True).select_related(
            'lead', 'lead__sub_department', 'created_by'
        )

        if not _is_admin(request.user):
            sub_dept = _user_sub_dept(request.user)
            if sub_dept:
                qs = qs.filter(lead__sub_department=sub_dept)

        lead_id   = request.query_params.get('lead')
        sr_status = request.query_params.get('status')
        if lead_id:
            qs = qs.filter(lead_id=lead_id)
        if sr_status:
            qs = qs.filter(status=sr_status)

        return _std_response(True, SampleRequisiteListSerializer(qs, many=True).data)

    @handle_exceptions
    @check_authentication()
    def retrieve(self, request, pk=None):
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)
        try:
            sr = SampleRequisite.objects.prefetch_related('items__stock_item').get(pk=pk)
            return _std_response(True, SampleRequisiteSerializer(sr).data)
        except SampleRequisite.DoesNotExist:
            return _std_response(False, error="Sample Requisite not found", http_status=404)

    @handle_exceptions
    @check_authentication()
    def create(self, request):
        """
        Create an SR with items.

        Expected payload:
        {
          "lead": <lead pk>,
          "sr_date": "YYYY-MM-DD",
          "delivery_address": "...",
          "contact_name": "...",
          "contact_number": "...",
          "notes": "...",
          "items": [
            {"stock_item": <id>, "quantity": 1, "uom": "NOS", "notes": ""},
            ...
          ]
        }
        """
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)

        items_data = request.data.get('items', [])
        serializer = SampleRequisiteSerializer(data=request.data)
        if not serializer.is_valid():
            return _std_response(False, error=serializer.errors, http_status=400)

        with transaction.atomic():
            sr = serializer.save(created_by=request.user)
            for item_data in items_data:
                stock_item = SubDeptStockItem.objects.get(pk=item_data['stock_item'])
                uom = item_data.get('uom') or stock_item.uom
                SampleRequisiteItem.objects.create(
                    sample_requisite=sr,
                    stock_item=stock_item,
                    quantity=item_data.get('quantity', 1),
                    uom=uom,
                    notes=item_data.get('notes', ''),
                )

        ActivityLog.objects.create(
            user=request.user, action="CREATE",
            model_name="SampleRequisite", record_id=sr.sr_no,
            description=f"Created SR {sr.sr_no}"
        )
        sr = SampleRequisite.objects.prefetch_related('items__stock_item').get(pk=sr.pk)
        return _std_response(True, SampleRequisiteSerializer(sr).data, http_status=201)

    @handle_exceptions
    @check_authentication()
    def update(self, request, pk=None):
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)
        try:
            sr = SampleRequisite.objects.get(pk=pk, is_active=True)
        except SampleRequisite.DoesNotExist:
            return _std_response(False, error="SR not found", http_status=404)

        items_data = request.data.get('items', None)
        serializer = SampleRequisiteSerializer(sr, data=request.data, partial=True)
        if not serializer.is_valid():
            return _std_response(False, error=serializer.errors, http_status=400)

        with transaction.atomic():
            sr = serializer.save()
            if items_data is not None:
                sr.items.all().update(is_active=False)
                for item_data in items_data:
                    stock_item = SubDeptStockItem.objects.get(pk=item_data['stock_item'])
                    uom = item_data.get('uom') or stock_item.uom
                    SampleRequisiteItem.objects.create(
                        sample_requisite=sr,
                        stock_item=stock_item,
                        quantity=item_data.get('quantity', 1),
                        uom=uom,
                        notes=item_data.get('notes', ''),
                    )

        sr = SampleRequisite.objects.prefetch_related('items__stock_item').get(pk=sr.pk)
        return _std_response(True, SampleRequisiteSerializer(sr).data)

    @handle_exceptions
    @check_authentication()
    def destroy(self, request, pk=None):
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)
        try:
            sr = SampleRequisite.objects.get(pk=pk)
            sr.is_active = False
            sr.save()
            return _std_response(True, {"sr_no": sr.sr_no})
        except SampleRequisite.DoesNotExist:
            return _std_response(False, error="SR not found", http_status=404)

    @handle_exceptions
    @check_authentication()
    @action(detail=True, methods=['post'], url_path='mark-sent')
    def mark_sent(self, request, pk=None):
        """
        Factory endpoint: mark the SR status as sent / partial_sent
        and optionally record qty_sent per item.

        Payload:
        {
          "status": "sent" | "partial_sent",
          "factory_remarks": "...",
          "items": [
            {"sr_item_id": <id>, "qty_sent": 2},
            ...
          ]
        }
        """
        try:
            sr = SampleRequisite.objects.prefetch_related('items').get(pk=pk)
        except SampleRequisite.DoesNotExist:
            return _std_response(False, error="SR not found", http_status=404)

        new_status = request.data.get('status', 'sent')
        if new_status not in ('sent', 'partial_sent'):
            return _std_response(False, error="Invalid status. Use 'sent' or 'partial_sent'.", http_status=400)

        with transaction.atomic():
            sr.status = new_status
            sr.factory_remarks = request.data.get('factory_remarks', sr.factory_remarks)
            if new_status == 'sent' and not sr.sent_to_factory_at:
                sr.sent_to_factory_at = timezone.now()
            sr.save()

            items_data = request.data.get('items', [])
            for item_upd in items_data:
                try:
                    sr_item = sr.items.get(id=item_upd['sr_item_id'])
                    sr_item.qty_sent = item_upd.get('qty_sent', sr_item.qty_sent)
                    sr_item.save()
                except SampleRequisiteItem.DoesNotExist:
                    pass

        ActivityLog.objects.create(
            user=request.user, action="SR_MARK_SENT",
            model_name="SampleRequisite", record_id=sr.sr_no,
            description=f"SR {sr.sr_no} marked as {new_status} by factory"
        )
        sr = SampleRequisite.objects.prefetch_related('items__stock_item').get(pk=sr.pk)
        return _std_response(True, SampleRequisiteSerializer(sr).data)


# ─────────────────────────────────────────────────────────────────────────────
# 6. ApplicationAreaViewSet
# ─────────────────────────────────────────────────────────────────────────────

class ApplicationAreaViewSet(viewsets.ViewSet):

    # @handle_exceptions
    # @check_authentication()
    # def list(self, request):
    #     if not _has_leads_access(request.user):
    #         return _std_response(False, error="Unauthorized", http_status=403)

    #     qs = ApplicationArea.objects.filter(is_active=True).select_related(
    #         'sub_department'
    #     ).prefetch_related(
    #         'system_products__items__stock_item',
    #         'fixed_items__stock_item'
    #     )

    #     sub_dept_id = request.query_params.get('sub_department')
    #     if sub_dept_id:
    #         qs = qs.filter(sub_department_id=sub_dept_id)
    #     elif not _is_admin(request.user):
    #         sub_dept = _user_sub_dept(request.user)
    #         if sub_dept:
    #             qs = qs.filter(sub_department=sub_dept)

    #     return _std_response(True, ApplicationAreaListSerializer(qs, many=True).data)

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)

        qs = ApplicationArea.objects.filter(is_active=True).select_related(
            'sub_department'
        ).prefetch_related(
            'system_products__items__stock_item',
            'fixed_items__stock_item'
        )

        sub_dept_id = request.query_params.get('sub_department')
        if sub_dept_id:
            qs = qs.filter(sub_department_id=sub_dept_id)
        elif not _is_admin(request.user):
            sub_dept = _user_sub_dept(request.user)
            if sub_dept:
                qs = qs.filter(sub_department=sub_dept)

        # Use full serializer (not list serializer) so system_products + fixed_items come through
        print(ApplicationAreaSerializer(qs, many=True).data)
        return _std_response(True, ApplicationAreaSerializer(qs, many=True).data)

    @handle_exceptions
    @check_authentication()
    def retrieve(self, request, pk=None):
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)
        try:
            area = ApplicationArea.objects.prefetch_related(
                'system_products__items__stock_item',
                'fixed_items__stock_item'
            ).get(pk=pk)
            return _std_response(True, ApplicationAreaSerializer(area).data)
        except ApplicationArea.DoesNotExist:
            return _std_response(False, error="Application area not found", http_status=404)

    @handle_exceptions
    @check_authentication()
    def create(self, request):
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)
        serializer = ApplicationAreaSerializer(data=request.data)
        if not serializer.is_valid():
            return _std_response(False, error=serializer.errors, http_status=400)
        area = serializer.save()
        return _std_response(True, ApplicationAreaSerializer(area).data, http_status=201)

    @handle_exceptions
    @check_authentication()
    def update(self, request, pk=None):
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)
        try:
            area = ApplicationArea.objects.get(pk=pk)
        except ApplicationArea.DoesNotExist:
            return _std_response(False, error="Application area not found", http_status=404)
        serializer = ApplicationAreaSerializer(area, data=request.data, partial=True)
        if not serializer.is_valid():
            return _std_response(False, error=serializer.errors, http_status=400)
        serializer.save()
        return _std_response(True, serializer.data)

    @handle_exceptions
    @check_authentication()
    def destroy(self, request, pk=None):
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)
        try:
            area = ApplicationArea.objects.get(pk=pk)
            area.is_active = False
            area.save()
            return _std_response(True, {"id": area.id})
        except ApplicationArea.DoesNotExist:
            return _std_response(False, error="Application area not found", http_status=404)


# ─────────────────────────────────────────────────────────────────────────────
# 7. ApplicationSystemProductViewSet
# ─────────────────────────────────────────────────────────────────────────────

class ApplicationSystemProductViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)

        qs = ApplicationSystemProduct.objects.filter(
            is_active=True
        ).prefetch_related('items__stock_item').select_related('application_area')

        area_id = request.query_params.get('application_area')
        if area_id:
            qs = qs.filter(application_area_id=area_id)

        return _std_response(True, ApplicationSystemProductSerializer(qs, many=True).data)

    @handle_exceptions
    @check_authentication()
    def retrieve(self, request, pk=None):
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)
        try:
            sp = ApplicationSystemProduct.objects.prefetch_related(
                'items__stock_item'
            ).get(pk=pk)
            return _std_response(True, ApplicationSystemProductSerializer(sp).data)
        except ApplicationSystemProduct.DoesNotExist:
            return _std_response(False, error="System product not found", http_status=404)

    @handle_exceptions
    @check_authentication()
    def create(self, request):
        """
        Create a system product with items.

        Payload:
        {
          "application_area": <id>,
          "name": "Full Bathroom Pack",
          "description": "...",
          "items": [
            {"stock_item": <id>, "quantity": 1, "uom": "NOS"},
            {"product_name": "Custom Item", "rate": 200, "quantity": 2}
          ]
        }
        """
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)

        items_data = request.data.get('items', [])
        serializer = ApplicationSystemProductSerializer(data=request.data)
        if not serializer.is_valid():
            return _std_response(False, error=serializer.errors, http_status=400)

        with transaction.atomic():
            sp = ApplicationSystemProduct.objects.create(
                application_area_id=request.data['application_area'],
                name=request.data['name'],
                description=request.data.get('description', ''),
            )
            for item_data in items_data:
                stock_item_id = item_data.get('stock_item')
                if stock_item_id:
                    stock_item = SubDeptStockItem.objects.get(pk=stock_item_id)
                    ApplicationSystemProductItem.objects.create(
                        system_product=sp,
                        stock_item=stock_item,
                        quantity=item_data.get('quantity', 1),
                        uom=item_data.get('uom') or stock_item.uom,
                        rate=item_data.get('rate', stock_item.rate),
                        hsn_code=item_data.get('hsn_code', stock_item.hsn_code),
                    )
                else:
                    ApplicationSystemProductItem.objects.create(
                        system_product=sp,
                        product_name=item_data.get('product_name', ''),
                        quantity=item_data.get('quantity', 1),
                        uom=item_data.get('uom', ''),
                        rate=item_data.get('rate'),
                        hsn_code=item_data.get('hsn_code'),
                    )

        sp = ApplicationSystemProduct.objects.prefetch_related(
            'items__stock_item'
        ).get(pk=sp.pk)
        return _std_response(True, ApplicationSystemProductSerializer(sp).data, http_status=201)

    @handle_exceptions
    @check_authentication()
    def update(self, request, pk=None):
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)
        try:
            sp = ApplicationSystemProduct.objects.get(pk=pk)
        except ApplicationSystemProduct.DoesNotExist:
            return _std_response(False, error="System product not found", http_status=404)

        items_data = request.data.get('items', None)
        if 'name' in request.data:
            sp.name = request.data['name']
        if 'description' in request.data:
            sp.description = request.data['description']
        if 'is_active' in request.data:
            sp.is_active = request.data['is_active']
        sp.save()

        if items_data is not None:
            sp.items.all().update(is_active=False)
            for item_data in items_data:
                stock_item_id = item_data.get('stock_item')
                if stock_item_id:
                    stock_item = SubDeptStockItem.objects.get(pk=stock_item_id)
                    ApplicationSystemProductItem.objects.create(
                        system_product=sp,
                        stock_item=stock_item,
                        quantity=item_data.get('quantity', 1),
                        uom=item_data.get('uom') or stock_item.uom,
                        rate=item_data.get('rate', stock_item.rate),
                        hsn_code=item_data.get('hsn_code', stock_item.hsn_code),
                    )
                else:
                    ApplicationSystemProductItem.objects.create(
                        system_product=sp,
                        product_name=item_data.get('product_name', ''),
                        quantity=item_data.get('quantity', 1),
                        uom=item_data.get('uom', ''),
                        rate=item_data.get('rate'),
                        hsn_code=item_data.get('hsn_code'),
                    )

        sp = ApplicationSystemProduct.objects.prefetch_related('items__stock_item').get(pk=sp.pk)
        return _std_response(True, ApplicationSystemProductSerializer(sp).data)

    @handle_exceptions
    @check_authentication()
    def destroy(self, request, pk=None):
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)
        try:
            sp = ApplicationSystemProduct.objects.get(pk=pk)
            sp.is_active = False
            sp.save()
            return _std_response(True, {"id": sp.id})
        except ApplicationSystemProduct.DoesNotExist:
            return _std_response(False, error="System product not found", http_status=404)


# ─────────────────────────────────────────────────────────────────────────────
# 8. ApplicationFixedItemViewSet
# ─────────────────────────────────────────────────────────────────────────────

class ApplicationFixedItemViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)

        area_id = request.query_params.get('application_area')
        qs = ApplicationFixedItem.objects.filter(is_active=True).select_related(
            'application_area', 'stock_item'
        )
        if area_id:
            qs = qs.filter(application_area_id=area_id)

        return _std_response(True, ApplicationFixedItemSerializer(qs, many=True).data)

    @handle_exceptions
    @check_authentication()
    def create(self, request):
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)

        data = request.data
        stock_item_id = data.get('stock_item')
        area_id = data.get('application_area')

        if not area_id:
            return _std_response(False, error="application_area required", http_status=400)

        try:
            area = ApplicationArea.objects.get(pk=area_id)
        except ApplicationArea.DoesNotExist:
            return _std_response(False, error="Application area not found", http_status=404)

        stock_item = None
        if stock_item_id:
            try:
                stock_item = SubDeptStockItem.objects.get(pk=stock_item_id)
            except SubDeptStockItem.DoesNotExist:
                return _std_response(False, error="Stock item not found", http_status=404)

        fixed = ApplicationFixedItem.objects.create(
            application_area=area,
            stock_item=stock_item,
            product_name=stock_item.product_name,
            hsn_code=stock_item.hsn_code,
            rate=stock_item.rate,
            uom=data.get('uom', stock_item.uom if stock_item else ''),
            quantity=data.get('quantity', 1),
        )
        return _std_response(True, ApplicationFixedItemSerializer(fixed).data, http_status=201)

    @handle_exceptions
    @check_authentication()
    def update(self, request, pk=None):
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)
        try:
            fixed = ApplicationFixedItem.objects.get(pk=pk)
        except ApplicationFixedItem.DoesNotExist:
            return _std_response(False, error="Fixed item not found", http_status=404)

        for field in ('product_name', 'hsn_code', 'rate', 'uom', 'quantity', 'is_active'):
            if field in request.data:
                setattr(fixed, field, request.data[field])
        fixed.save()
        return _std_response(True, ApplicationFixedItemSerializer(fixed).data)

    @handle_exceptions
    @check_authentication()
    def destroy(self, request, pk=None):
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)
        try:
            fixed = ApplicationFixedItem.objects.get(pk=pk)
            fixed.is_active = False
            fixed.save()
            return _std_response(True, {"id": fixed.id})
        except ApplicationFixedItem.DoesNotExist:
            return _std_response(False, error="Fixed item not found", http_status=404)


# ─────────────────────────────────────────────────────────────────────────────
# 9. ApplicationLeadViewSet
#    OneToOne extension on Lead (not DeptLead)
# ─────────────────────────────────────────────────────────────────────────────

class ApplicationLeadViewSet(viewsets.ViewSet):
    """
    Manage the ApplicationLead extension for a Lead.
    A Lead can have at most one ApplicationLead (OneToOne).
    """

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)

        qs = ApplicationLead.objects.select_related(
            'lead', 'application_area', 'lead__sub_department'
        ).prefetch_related('selected_system_products__items__stock_item')

        lead_id = request.query_params.get('lead')
        if lead_id:
            qs = qs.filter(lead_id=lead_id)

        return _std_response(True, ApplicationLeadSerializer(qs, many=True).data)

    @handle_exceptions
    @check_authentication()
    def retrieve(self, request, pk=None):
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)
        try:
            al = ApplicationLead.objects.select_related(
                'lead', 'application_area'
            ).prefetch_related(
                'selected_system_products__items__stock_item',
                'application_area__fixed_items__stock_item'
            ).get(pk=pk)
            return _std_response(True, ApplicationLeadSerializer(al).data)
        except ApplicationLead.DoesNotExist:
            return _std_response(False, error="Application lead not found", http_status=404)

    @handle_exceptions
    @check_authentication()
    def create(self, request):
        """
        Attach application detail to a Lead.

        Payload:
        {
          "lead": <lead pk>,
          "application_area": <id>,
          "selected_system_products": [<sp_id>, ...],
          "notes": "..."
        }
        """
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)

        serializer = ApplicationLeadSerializer(data=request.data)
        if not serializer.is_valid():
            return _std_response(False, error=serializer.errors, http_status=400)

        al = serializer.save()
        al = ApplicationLead.objects.prefetch_related(
            'selected_system_products__items__stock_item',
            'application_area__fixed_items__stock_item'
        ).get(pk=al.pk)
        return _std_response(True, ApplicationLeadSerializer(al).data, http_status=201)

    @handle_exceptions
    @check_authentication()
    def update(self, request, pk=None):
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)
        try:
            al = ApplicationLead.objects.get(pk=pk)
        except ApplicationLead.DoesNotExist:
            return _std_response(False, error="Application lead not found", http_status=404)

        serializer = ApplicationLeadSerializer(al, data=request.data, partial=True)
        if not serializer.is_valid():
            return _std_response(False, error=serializer.errors, http_status=400)
        al = serializer.save()
        al = ApplicationLead.objects.prefetch_related(
            'selected_system_products__items__stock_item',
            'application_area__fixed_items__stock_item'
        ).get(pk=al.pk)
        return _std_response(True, ApplicationLeadSerializer(al).data)

    @handle_exceptions
    @check_authentication()
    def destroy(self, request, pk=None):
        if not _has_leads_access(request.user):
            return _std_response(False, error="Unauthorized", http_status=403)
        try:
            al = ApplicationLead.objects.get(pk=pk)
            al.delete()
            return _std_response(True, {"id": pk})
        except ApplicationLead.DoesNotExist:
            return _std_response(False, error="Application lead not found", http_status=404)
