from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'login-api', LoginViewSet, basename='login-api')
router.register(r'logout-api', LogoutViewSet, basename='logout-api')
router.register(r'user-api', UserViewSet, basename='user-api')
router.register(r'me-api', MeViewSet, basename='me-api')
router.register(r'logs-api', ActivityLogViewSet, basename='logs-api')
router.register(r'admin-other-user-api', LogInToUserAccount, basename='admin-other-user-api')

urlpatterns = [
    path('', include(router.urls)),
]
