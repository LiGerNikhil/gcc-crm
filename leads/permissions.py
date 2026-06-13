from rest_framework.permissions import BasePermission


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and _has_role(request.user, "SUPER_ADMIN")


class IsAdminOrTeamLead(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and _has_role(request.user, ["SUPER_ADMIN", "TEAM_LEAD"])


class IsCaller(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and _has_role(request.user, ["SUPER_ADMIN", "TEAM_LEAD", "CALLER"])


class IsDataEntry(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and _has_role(request.user, ["SUPER_ADMIN", "TEAM_LEAD", "DATA_ENTRY"])


class IsAssignedOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        if _has_role(request.user, "SUPER_ADMIN"):
            return True
        return obj.assigned_to == request.user


def _has_role(user, roles):
    try:
        role = user.profile.role.role_code
        if isinstance(roles, list):
            return role in roles
        return role == roles
    except Exception:
        return False
