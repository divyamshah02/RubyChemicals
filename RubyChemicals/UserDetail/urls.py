from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LoginViewSet, LogoutViewSet, UserViewSet, MeViewSet, ActivityLogViewSet

router = DefaultRouter()
router.register(r'login-api', LoginViewSet, basename='login-api')
router.register(r'logout-api', LogoutViewSet, basename='logout-api')
router.register(r'user-api', UserViewSet, basename='user-api')
router.register(r'me-api', MeViewSet, basename='me-api')
router.register(r'logs-api', ActivityLogViewSet, basename='logs-api')

urlpatterns = [
    path('', include(router.urls)),
]
