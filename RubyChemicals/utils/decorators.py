from functools import wraps
from rest_framework.response import Response
from rest_framework import status
import logging

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

def check_authentication(required_role=None):
    '''Checks if user is logged in or not.
    If required_role is passed (as str or list), will check for that as well.'''
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

            if required_role:
                # Convert to list if it's a string
                allowed_roles = required_role if isinstance(required_role, (list, tuple, set)) else [required_role]
                
                if getattr(user, "role", None) not in allowed_roles:
                    # logger.warning(
                    #     f"Unauthorized access: User {user.id} role {user.role} "
                    #     f"required {allowed_roles}"
                    # )
                    return Response(
                        {
                            "success": False,
                            "user_not_logged_in": False,
                            "user_unauthorized": True,
                            "data": None,
                            "error": f"User role must be one of {allowed_roles}"
                        }, status=status.HTTP_403_FORBIDDEN
                    )

            return view_func(self, request, *args, **kwargs)

        return _wrapped_view
    return decorator
