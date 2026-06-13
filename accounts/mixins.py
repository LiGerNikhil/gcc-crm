from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse_lazy


class ActiveUserRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_active:
            messages.error(request, "Your account has been deactivated.")
            return redirect("accounts:login")
        try:
            profile = request.user.profile
            if not profile.is_active:
                messages.error(request, "Your profile has been deactivated.")
                return redirect("accounts:login")
        except AttributeError:
            pass
        return super().dispatch(request, *args, **kwargs)


class RoleRequiredMixin(UserPassesTestMixin):
    allowed_roles = []

    def test_func(self):
        if not self.request.user.is_authenticated:
            return False
        # Superusers bypass all role checks
        if self.request.user.is_superuser:
            return True
        try:
            role_code = self.request.user.profile.role.role_code
            return role_code in self.allowed_roles
        except AttributeError:
            return False

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect("accounts:login")
        messages.error(self.request, "You do not have permission to access this page.")
        return redirect("accounts:dashboard")


class SuperAdminRequiredMixin(RoleRequiredMixin):
    allowed_roles = ["SUPER_ADMIN"]

    def handle_no_permission(self):
        messages.error(
            self.request,
            "Only Super Administrators can access this page.",
        )
        return redirect("accounts:dashboard")


class AdminOrTeamLeadRequiredMixin(RoleRequiredMixin):
    allowed_roles = ["SUPER_ADMIN", "MANAGER", "TEAM_LEAD"]

    def handle_no_permission(self):
        messages.error(
            self.request,
            "You do not have sufficient privileges to access this page.",
        )
        return redirect("accounts:dashboard")


class ManagerRequiredMixin(RoleRequiredMixin):
    allowed_roles = ["SUPER_ADMIN", "MANAGER"]

    def handle_no_permission(self):
        messages.error(
            self.request,
            "Only Managers and Super Admins can access this page.",
        )
        return redirect("accounts:dashboard")


class ManagerOrTeamLeadRequiredMixin(RoleRequiredMixin):
    allowed_roles = ["SUPER_ADMIN", "MANAGER", "TEAM_LEAD"]

    def handle_no_permission(self):
        messages.error(
            self.request,
            "You do not have sufficient privileges to access this page.",
        )
        return redirect("accounts:dashboard")


class CallerRequiredMixin(RoleRequiredMixin):
    allowed_roles = ["SUPER_ADMIN", "MANAGER", "TEAM_LEAD", "ARO", "CALLER"]


class DataEntryRequiredMixin(RoleRequiredMixin):
    allowed_roles = ["SUPER_ADMIN", "MANAGER", "TEAM_LEAD", "DATA_ENTRY"]
