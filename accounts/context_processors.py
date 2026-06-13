from .models import UserProfile


def user_role(request):
    role_code = None
    role_name = None
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            role_code = profile.role.role_code if profile.role else None
            role_name = profile.role.name if profile.role else None
        except UserProfile.DoesNotExist:
            pass
    return {
        "user_role_code": role_code,
        "user_role_name": role_name,
    }
