from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *
from .asset_views import HRAssetViewSet
from .hr_views import (
    HREmployeeViewSet,
    HRAttendanceViewSet,
    HRLeaveViewSet,
    HRUniversalLeaveViewSet,
    HRLeaveApplicationViewSet,
    HRLeaveQuotaViewSet,
    HRPayrollViewSet,
    HRReimbursementViewSet,
    MyProfileViewSet,
    MyAttendanceViewSet,
    MyLeaveViewSet,
    MyReimbursementViewSet,
    MyPayrollViewSet,
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
router.register(r'hr-leave-application-api', HRLeaveApplicationViewSet, basename='hr-leave-application-api')
router.register(r'hr-leave-quota-api', HRLeaveQuotaViewSet, basename='hr-leave-quota-api')
router.register(r'hr-payroll-api', HRPayrollViewSet, basename='hr-payroll-api')
router.register(r'hr-reimbursement-api', HRReimbursementViewSet, basename='hr-reimbursement-api')
router.register(r'hr-asset-api', HRAssetViewSet, basename='hr-asset-api')

# Employee self-service (profile page)
router.register(r'my-profile-api', MyProfileViewSet, basename='my-profile-api')
router.register(r'my-attendance-api', MyAttendanceViewSet, basename='my-attendance-api')
router.register(r'my-leave-api', MyLeaveViewSet, basename='my-leave-api')
router.register(r'my-reimbursement-api', MyReimbursementViewSet, basename='my-reimbursement-api')
router.register(r'my-payroll-api', MyPayrollViewSet, basename='my-payroll-api')


urlpatterns = [
    path('', include(router.urls)),
]
