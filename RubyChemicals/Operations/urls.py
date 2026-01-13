from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()

router.register(r'stock-group-api', StockGroupViewSet, basename='stock-group-api')
router.register(r'stock-item-api', StockItemViewSet, basename='stock-item-api')

router.register(r'stock-inward-api', StockInwardViewSet, basename='stock-inward-api')
router.register(r'stock-adjustment-api', StockAdjustmentViewSet, basename='stock-adjustment-api')

router.register(r'production-api', ProductionBatchViewSet, basename='production-api')

router.register(r'dispatch-api', DispatchViewSet, basename='dispatch-api')

router.register(r'expense-head-api', ExpenseHeadViewSet, basename='expense-head-api')
router.register(r'petty-cash-api', PettyCashViewSet, basename='petty-cash-api')

urlpatterns = [
    path('', include(router.urls)),
]
