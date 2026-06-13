from rest_framework.permissions import BasePermission


def _has_role(user, roles):
    try:
        role = user.profile.role.role_code
        if isinstance(roles, list):
            return role in roles
        return role == roles
    except Exception:
        return False


class CanImportLeads(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and _has_role(
            request.user, ["SUPER_ADMIN", "TEAM_LEAD", "DATA_ENTRY"]
        )
