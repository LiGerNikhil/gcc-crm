from rest_framework.permissions import BasePermission, SAFE_METHODS


def _has_role(user, roles):
    try:
        role = user.profile.role.role_code
        if isinstance(roles, list):
            return role in roles
        return role == roles
    except Exception:
        return False


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


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return _has_role(request.user, ["SUPER_ADMIN", "TEAM_LEAD"])


class IsSelfOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        if _has_role(request.user, "SUPER_ADMIN"):
            return True
        if hasattr(obj, "user"):
            return obj.user == request.user
        return obj == request.user


class IsAssignedOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        if _has_role(request.user, "SUPER_ADMIN"):
            return True
        return getattr(obj, "assigned_to", None) == request.user
