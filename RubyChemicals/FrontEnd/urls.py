from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()

router.register(r'login', LoginViewSet, basename='login')
router.register(r'logout', LogoutViewSet, basename='logout')
router.register(r'', AdminDashboardViewSet, basename='home')
router.register(r'admin-dashboard', AdminDashboardViewSet, basename='admin-dashboard')
router.register(r'accounts-dashboard', AccountsDashboardViewSet, basename='accounts-dashboard')
router.register(r'production-dashboard', ProductionDashboardViewSet, basename='production-dashboard')

router.register(r'stock-groups', StockGroupViewSet, basename='stock-groups')
router.register(r'stock-items', StockItemViewSet, basename='stock-items')
router.register(r'stock-inwards', StockInwardViewSet, basename='stock-inwards')
router.register(r'production', ProductionViewSet, basename='production')
router.register(r'dispatch', DispatchViewSet, basename='dispatch')
router.register(r'client-management', ClientManagementViewSet, basename='client-management')
router.register(r'vendor-management', VendorManagementViewSet, basename='vendor-management')
router.register(r'petty-cash', PettyCashViewSet, basename='petty-cash')
router.register(r'leads', LeadsViewSet, basename='leads')
router.register(r'lead-sub-dept-mgmt', LeadSubDeptMngmtViewSet, basename='lead-sub-dept-mgmt')

# Role Manager — accessible to admin role only
router.register(r'role-manager', RoleManagerViewSet, basename='role-manager')

router.register(r'test-api', ExtraAddStockDetails, basename='test-api')

urlpatterns = [
    path('', include(router.urls)),
]
