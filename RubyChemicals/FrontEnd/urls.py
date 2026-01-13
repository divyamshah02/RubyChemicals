from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()

router.register(r'stock-groups', StockGroupViewSet, basename='stock-groups')
router.register(r'stock-items', StockItemViewSet, basename='stock-items')
router.register(r'production', ProductionViewSet, basename='production')
router.register(r'dispatch', DispatchViewSet, basename='dispatch')
router.register(r'petty-cash', PettyCashViewSet, basename='petty-cash')


urlpatterns = [
    path('', include(router.urls)),
]
