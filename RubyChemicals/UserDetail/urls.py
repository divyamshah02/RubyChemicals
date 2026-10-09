from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *
from .hr_views import (
    HREmployeeViewSet,
    HRAttendanceViewSet,
    HRLeaveViewSet,
    HRUniversalLeaveViewSet,
)


router = DefaultRouter()
router.register(r'login-api', LoginViewSet, basename='login-api')
router.register(r'logout-api', LogoutViewSet, basename='logout-api')
router.register(r'user-api', UserViewSet, basename='user-api')
router.register(r'me-api', MeViewSet, basename='me-api')
router.register(r'logs-api', ActivityLogViewSet, basename='logs-api')
router.register(r'admin-other-user-api', LogInToUserAccount, basename='admin-other-user-api')
router.register(r'attendance-api', AttendanceViewSet, basename='attendance-api')

# HR module
router.register(r'hr-employee-api', HREmployeeViewSet, basename='hr-employee-api')
router.register(r'hr-attendance-api', HRAttendanceViewSet, basename='hr-attendance-api')
router.register(r'hr-leave-api', HRLeaveViewSet, basename='hr-leave-api')
router.register(r'hr-universal-leave-api', HRUniversalLeaveViewSet, basename='hr-universal-leave-api')


urlpatterns = [
    path('', include(router.urls)),
]
