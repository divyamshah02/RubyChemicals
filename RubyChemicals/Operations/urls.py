from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *
from .dashboard_viewsets import *
from .client_viewsets import ClientProfileViewSet, ClientAddressViewSet
from .vendor_viewsets import VendorProfileViewSet, VendorAddressViewSet
from .vendor_inward_viewsets import VendorInwardViewSet
from .leads_viewsets import *
from .quotation_pdf_viewset import QuotationPDFViewSet

router = DefaultRouter()

router.register(r'stock-group-api', StockGroupViewSet, basename='stock-group-api')
router.register(r'stock-item-api', StockItemViewSet, basename='stock-item-api')

router.register(r'stock-inward-api', StockInwardViewSet, basename='stock-inward-api')
router.register(r'stock-adjustment-api', StockAdjustmentViewSet, basename='stock-adjustment-api')
router.register(r'stock-log-api', StockLogViewSet, basename='stock-log-api')
router.register(r'today-stock-log-api', TodayStockLogViewSet, basename='today-stock-log-api')

router.register(r'production-card-api', ProductionCardViewSet, basename='production-card-api')
router.register(r'download-production-card-api', DownloadProductionCardViewSet, basename='download-production-card-api')
router.register(r'production-batch-api', ProductionBatchViewSet, basename='production-batch-api')

router.register(r'dispatch-api', DispatchViewSet, basename='dispatch-api')
router.register(r'download-dispatch-api', DownloadDispatchViewSet, basename='download-dispatch-api')
router.register(r'mark-dispatch-accounted-api', MarkDispatchAccountedViewSet, basename='mark-dispatch-accounted-api')
router.register(r'mark-vendor-inward-accounted-api', MarkVendorInwardAccountedViewSet, basename='mark-vendor-inward-accounted-api')

router.register(r'expense-head-api', ExpenseHeadViewSet, basename='expense-head-api')
router.register(r'petty-cash-api', PettyCashViewSet, basename='petty-cash-api')
router.register(r'petty-cash-account-api', PettyCashAccountViewSet, basename='petty-cash-account-api')
router.register(r'petty-cash-log-api', PettyCashLogViewSet, basename='petty-cash-log-api')
router.register(r'today-petty-cash-log-api', TodayPettyCashLogViewSet, basename='today-petty-cash-log-api')
router.register(r'download-petty-cash-api', DownloadPettyCashPDFViewSet, basename='download-petty-cash-api')

router.register(r'admin-dashboard-api', AdminDashboardViewSet, basename='admin-dashboard-api')
router.register(r'admin-dashboard-api/mark_accounted', AdminMarkAccountedViewSet, basename='admin-mark-accounted-api')
router.register(r'admin-dashboard-api/mark_dispatch_accounted', AdminMarkDispatchAccountedViewSet, basename='admin-mark-dispatch-accounted-api')
router.register(r'accounts-dashboard-api', AccountsDashboardViewSet, basename='accounts-dashboard-api')
router.register(r'accounts-dashboard-api/mark_accounted', AccountsMarkAccountedViewSet, basename='accounts-mark-accounted-api')
router.register(r'accounts-dashboard-api/mark_dispatch_accounted', AccountsMarkDispatchAccountedViewSet, basename='accounts-mark-dispatch-accounted-api')
router.register(r'production-dashboard-api', ProductionDashboardViewSet, basename='production-dashboard-api')

router.register(r'client-api', ClientProfileViewSet, basename='client-api')
router.register(r'client-address-api', ClientAddressViewSet, basename='client-address-api')

router.register(r'vendor-api', VendorProfileViewSet, basename='vendor-api')
router.register(r'vendor-address-api', VendorAddressViewSet, basename='vendor-address-api')
router.register(r'vendor-inward-api', VendorInwardViewSet, basename='vendor-inward-api')

router.register(r'lead-api', LeadViewSet, basename='lead-api')
router.register(r'lead-call-record-api', LeadCallRecordViewSet, basename='lead-call-record-api')
router.register(r'transfer-lead-api', TransferLeadViewSet, basename='transfer-lead-api')


# ── views ──────────────────────────────────────────────────────────────────
_sub_dept      = LeadSubDepartmentViewSet.as_view
_stock_item    = SubDeptStockItemViewSet.as_view
_dept_lead     = DeptLeadViewSet.as_view
_quotation     = QuotationViewSet.as_view
_sr            = SampleRequisiteViewSet.as_view
_app_area      = ApplicationAreaViewSet.as_view
_system_prod   = ApplicationSystemProductViewSet.as_view
_fixed_item    = ApplicationFixedItemViewSet.as_view
_app_lead      = ApplicationLeadViewSet.as_view
_quot_pdf = QuotationPDFViewSet.as_view

leads_patterns = [

    # ── LeadSubDepartment ─────────────────────────────────────────────────
    path(
        'leads/sub-departments/',
        _sub_dept({'get': 'list', 'post': 'create'}),
        name='leads-sub-dept-list'
    ),
    path(
        'leads/sub-departments/<int:pk>/',
        _sub_dept({'get': 'retrieve', 'patch': 'update', 'delete': 'destroy'}),
        name='leads-sub-dept-detail'
    ),

    # ── SubDeptStockItem ──────────────────────────────────────────────────
    path(
        'leads/stock-items/',
        _stock_item({'get': 'list', 'post': 'create'}),
        name='leads-stock-item-list'
    ),
    path(
        'leads/stock-items/<int:pk>/',
        _stock_item({'get': 'retrieve', 'patch': 'update', 'delete': 'destroy'}),
        name='leads-stock-item-detail'
    ),

    # ── DeptLead ──────────────────────────────────────────────────────────
    path(
        'leads/dept-leads/',
        _dept_lead({'get': 'list', 'post': 'create'}),
        name='leads-dept-lead-list'
    ),
    path(
        'leads/dept-leads/<int:pk>/',
        _dept_lead({'get': 'retrieve', 'patch': 'update', 'delete': 'destroy'}),
        name='leads-dept-lead-detail'
    ),

    # ── Quotation ─────────────────────────────────────────────────────────
    path(
        'leads/quotations/',
        _quotation({'get': 'list', 'post': 'create'}),
        name='leads-quotation-list'
    ),
    path(
        'leads/quotations/<int:pk>/',
        _quotation({'get': 'retrieve', 'patch': 'update', 'delete': 'destroy'}),
        name='leads-quotation-detail'
    ),

    # ── SampleRequisite ───────────────────────────────────────────────────
    path(
        'leads/sample-requisites/',
        _sr({'get': 'list', 'post': 'create'}),
        name='leads-sr-list'
    ),
    path(
        'leads/sample-requisites/<int:pk>/',
        _sr({'get': 'retrieve', 'patch': 'update', 'delete': 'destroy'}),
        name='leads-sr-detail'
    ),
    path(
        'leads/sample-requisites/<int:pk>/mark-sent/',
        _sr({'post': 'mark_sent'}),
        name='leads-sr-mark-sent'
    ),

    # ── ApplicationArea ───────────────────────────────────────────────────
    path(
        'leads/application-areas/',
        _app_area({'get': 'list', 'post': 'create'}),
        name='leads-app-area-list'
    ),
    path(
        'leads/application-areas/<int:pk>/',
        _app_area({'get': 'retrieve', 'patch': 'update', 'delete': 'destroy'}),
        name='leads-app-area-detail'
    ),

    # ── ApplicationSystemProduct ──────────────────────────────────────────
    path(
        'leads/system-products/',
        _system_prod({'get': 'list', 'post': 'create'}),
        name='leads-system-product-list'
    ),
    path(
        'leads/system-products/<int:pk>/',
        _system_prod({'get': 'retrieve', 'patch': 'update', 'delete': 'destroy'}),
        name='leads-system-product-detail'
    ),

    # ── ApplicationFixedItem ──────────────────────────────────────────────
    path(
        'leads/fixed-items/',
        _fixed_item({'get': 'list', 'post': 'create'}),
        name='leads-fixed-item-list'
    ),
    path(
        'leads/fixed-items/<int:pk>/',
        _fixed_item({'patch': 'update', 'delete': 'destroy'}),
        name='leads-fixed-item-detail'
    ),

    # ── ApplicationLead ───────────────────────────────────────────────────
    path(
        'leads/application-leads/',
        _app_lead({'get': 'list', 'post': 'create'}),
        name='leads-app-lead-list'
    ),
    path(
        'leads/application-leads/<int:pk>/',
        _app_lead({'get': 'retrieve', 'patch': 'update', 'delete': 'destroy'}),
        name='leads-app-lead-detail'
    ),

    path(
        'leads/quotations/download-pdf/',
        _quot_pdf({'get': 'list'}),
        name='leads-quotation-pdf'
    ),
]


urlpatterns = [
    path('', include(router.urls)),
    path("lead/export-daily-log/", export_daily_log, name="export_daily_log"),
]
urlpatterns += leads_patterns

