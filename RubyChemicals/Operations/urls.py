from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *
from .dashboard_viewsets import *
from .client_viewsets import ClientProfileViewSet, ClientAddressViewSet

router = DefaultRouter()

router.register(r'stock-group-api', StockGroupViewSet, basename='stock-group-api')
router.register(r'stock-item-api', StockItemViewSet, basename='stock-item-api')

router.register(r'stock-inward-api', StockInwardViewSet, basename='stock-inward-api')
router.register(r'stock-adjustment-api', StockAdjustmentViewSet, basename='stock-adjustment-api')

router.register(r'production-card-api', ProductionCardViewSet, basename='production-card-api')
router.register(r'production-batch-api', ProductionBatchViewSet, basename='production-batch-api')

router.register(r'dispatch-api', DispatchViewSet, basename='dispatch-api')

router.register(r'expense-head-api', ExpenseHeadViewSet, basename='expense-head-api')
router.register(r'petty-cash-api', PettyCashViewSet, basename='petty-cash-api')

router.register(r'admin-dashboard-api', AdminDashboardViewSet, basename='admin-dashboard-api')
router.register(r'admin-dashboard-api/mark_accounted', AdminMarkAccountedViewSet, basename='admin-mark-accounted-api')
router.register(r'admin-dashboard-api/mark_dispatch_accounted', AdminMarkDispatchAccountedViewSet, basename='admin-mark-dispatch-accounted-api')
router.register(r'accounts-dashboard-api', AccountsDashboardViewSet, basename='accounts-dashboard-api')
router.register(r'accounts-dashboard-api/mark_accounted', AccountsMarkAccountedViewSet, basename='accounts-mark-accounted-api')
router.register(r'accounts-dashboard-api/mark_dispatch_accounted', AccountsMarkDispatchAccountedViewSet, basename='accounts-mark-dispatch-accounted-api')
router.register(r'production-dashboard-api', ProductionDashboardViewSet, basename='production-dashboard-api')

router.register(r'client-api', ClientProfileViewSet, basename='client-api')
router.register(r'client-address-api', ClientAddressViewSet, basename='client-address-api')

urlpatterns = [
    path('', include(router.urls)),
]
