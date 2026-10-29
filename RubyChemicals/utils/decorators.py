from functools import wraps
from django.contrib.auth import logout
from rest_framework.response import Response
from rest_framework import status
import logging

def _as_list(value):
    if not value:
        return []
    return list(value) if isinstance(value, (list, tuple, set)) else [value]


def handle_exceptions(view_func):
    """Decorator to handle exceptions in API views, with logging."""
    @wraps(view_func)
    def _wrapped_view(self, request, *args, **kwargs):
        try:
            return view_func(self, request, *args, **kwargs)
        except Exception as ex:
            session_info = {}
            if hasattr(request, 'session'):
                session_info = {
                    'session_key': request.session.session_key,
                    'session_expiry': request.session.get_expiry_date(),
                    'session_data': dict(request.session),
                }
            
            # Log detailed error
            # logger.error(
            #     f"Exception in {view_func.__name__}: {str(ex)}\n"
            #     f"User: {request.user if request.user.is_authenticated else 'Anonymous'}\n"
            #     f"Session: {session_info}\n"
            #     f"Path: {request.path}\n"
            #     f"Method: {request.method}\n"
            #     f"Data: {request.data if hasattr(request, 'data') else 'None'}",
            #     exc_info=True
            # )
            # logger.error(ex, exc_info=True)
            print(ex)
            return Response(
                {
                    "success": False,
                    "user_not_logged_in": False,
                    "user_unauthorized": False,
                    # "session_info": session_info,
                    "data": None,
                    "error": str(ex)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    return _wrapped_view

def check_authentication(required_role=None, required_permission=None):
    '''Checks if user is logged in or not.

    required_role / required_permission are optional (str or list). When either
    is given the user passes if ANY of these is true:
      * user.is_super_admin
      * user.role is in required_role
      * the user has at least one of the required_permission flags
        (module permission fields such as "can_stock_items")
    '''
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(self, request, *args, **kwargs):
            user = request.user
            session_info = {}

            if hasattr(request, 'session'):
                session_info = {
                    'session_key': request.session.session_key,
                    'session_expiry': request.session.get_expiry_date(),
                    'session_data_keys': list(request.session.keys()),
                }

            if not user.is_authenticated:
                # logger.warning(f"Unauthenticated access attempt: {request.path}")
                return Response(
                    {
                        "success": False,
                        "user_not_logged_in": True,
                        "user_unauthorized": False,
                        # "session_info": session_info,
                        "data": None,
                        "error": "User not authenticated"
                    }, status=status.HTTP_401_UNAUTHORIZED
                )

            # Deactivated or exited employees lose access immediately, even with a live session.
            if not user.active_user:
                logout(request)
                return Response(
                    {
                        "success": False,
                        "user_not_logged_in": True,
                        "user_unauthorized": False,
                        "data": None,
                        "error": "This account is no longer active."
                    }, status=status.HTTP_401_UNAUTHORIZED
                )

            if required_role or required_permission:
                allowed_roles = _as_list(required_role)
                allowed_permissions = _as_list(required_permission)

                has_access = (
                    getattr(user, "is_super_admin", False)
                    or getattr(user, "role", None) in allowed_roles
                    or any(bool(getattr(user, perm, False)) for perm in allowed_permissions)
                )

                if not has_access:
                    if allowed_permissions:
                        message = "You do not have permission to perform this action."
                    else:
                        message = f"User role must be one of {allowed_roles}"
                    return Response(
                        {
                            "success": False,
                            "user_not_logged_in": False,
                            "user_unauthorized": True,
                            "data": None,
                            "error": message
                        }, status=status.HTTP_403_FORBIDDEN
                    )

            return view_func(self, request, *args, **kwargs)

        return _wrapped_view
    return decorator
