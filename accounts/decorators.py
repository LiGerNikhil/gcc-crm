from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def role_required(allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("accounts:login")
            if not request.user.is_active:
                messages.error(request, "Your account has been deactivated.")
                return redirect("accounts:login")
            try:
                role_code = request.user.profile.role.role_code
                if role_code not in allowed_roles:
                    messages.error(
                        request,
                        "You do not have permission to perform this action.",
                    )
                    return redirect("accounts:dashboard")
            except AttributeError:
                messages.error(request, "User profile not found.")
                return redirect("accounts:login")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def super_admin_required(view_func):
    return role_required(["SUPER_ADMIN"])(view_func)


def admin_or_team_lead_required(view_func):
    return role_required(["SUPER_ADMIN", "TEAM_LEAD"])(view_func)


def caller_required(view_func):
    return role_required(["SUPER_ADMIN", "MANAGER", "TEAM_LEAD", "ARO", "CALLER"])(view_func)


def data_entry_required(view_func):
    return role_required(["SUPER_ADMIN", "MANAGER", "TEAM_LEAD", "DATA_ENTRY"])(view_func)
