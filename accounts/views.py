from django.contrib.auth import (
    login as auth_login, logout as auth_logout, update_session_auth_hash,
)
from django.contrib.auth.views import (
    PasswordResetView as AuthPasswordResetView,
    PasswordResetConfirmView as AuthPasswordResetConfirmView,
    PasswordResetDoneView as AuthPasswordResetDoneView,
    PasswordResetCompleteView as AuthPasswordResetCompleteView,
)
from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import ListView, TemplateView

from .forms import (
    LoginForm, CustomPasswordChangeForm,
    UserCreateForm, UserUpdateForm, UserActivationForm,
)
from .mixins import (
    SuperAdminRequiredMixin, ActiveUserRequiredMixin,
    RoleRequiredMixin, AdminOrTeamLeadRequiredMixin,
)
from .models import User, UserProfile, Role


class LoginView(View):
    template_name = "accounts/login.html"
    form_class = LoginForm

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("accounts:dashboard")
        form = self.form_class()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = self.form_class(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            if not form.cleaned_data.get("remember_me"):
                request.session.set_expiry(0)
            messages.success(
                request, _(f"Welcome back, {user.get_full_name() or user.username}!")
            )
            next_url = request.GET.get("next")
            if next_url:
                return redirect(next_url)
            return redirect("accounts:dashboard")
        return render(request, self.template_name, {"form": form})


class LogoutView(View):
    def get(self, request):
        auth_logout(request)
        messages.info(request, _("You have been logged out successfully."))
        return redirect("accounts:login")

    def post(self, request):
        return self.get(request)


class DashboardView(ActiveUserRequiredMixin, TemplateView):
    template_name = "accounts/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        try:
            profile = user.profile
            role_code = profile.role.role_code if profile.role else None
        except UserProfile.DoesNotExist:
            profile = None
            role_code = None
        context["role_code"] = role_code
        context["profile"] = profile
        context["total_users"] = User.objects.filter(is_active=True).count()
        context["team_size"] = UserProfile.objects.filter(
            manager=profile
        ).count() if profile else 0

        if role_code in ("SUPER_ADMIN", "MANAGER"):
            from analytics.services import (
                get_dashboard_kpi, get_daily_leads,
                get_source_wise_stats, get_employee_metrics,
                get_lead_metrics,
            )
            context["kpi"] = get_dashboard_kpi()
            context["daily_leads"] = get_daily_leads()
            context["source_stats"] = get_source_wise_stats()
            context["employee_metrics"] = get_employee_metrics()
            context["lead_metrics"] = get_lead_metrics()

        if profile and role_code == "MANAGER":
            context["sub_team_leads"] = UserProfile.objects.filter(
                manager=profile, is_active=True, role__role_code="TEAM_LEAD"
            )
            context["sub_aros"] = UserProfile.objects.filter(
                manager__in=UserProfile.objects.filter(manager=profile, is_active=True),
                is_active=True, role__role_code__in=["ARO", "CALLER"],
            )

        # ── Work Queue context for TL / ARO / CALLER ──
        if profile and role_code == "TEAM_LEAD":
            from documents.models import WorkItem, WorkNote
            my_aros = User.objects.filter(
                profile__manager=profile,
                profile__role__role_code__in=["ARO", "CALLER"],
                is_active=True,
            )
            team_ids = [user.id] + [u.id for u in my_aros]
            team_items = WorkItem.objects.filter(assigned_to_id__in=team_ids).exclude(
                status__in=["CLOSED", "REJECTED"]
            ).select_related("batch", "assigned_to").order_by("-assigned_at")

            context["tl_total_items"] = team_items.count()
            context["tl_assigned_count"] = team_items.filter(status="ASSIGNED").count()
            context["tl_completed_count"] = team_items.filter(status="COMPLETED").count()
            context["tl_feedback_count"] = WorkNote.objects.filter(
                work_item__in=team_items, is_feedback=True
            ).count()
            context["tl_recent_items"] = team_items[:10]

        elif profile and role_code in ("ARO", "CALLER"):
            from documents.models import WorkItem
            aro_items = WorkItem.objects.filter(
                assigned_to=user
            ).exclude(status__in=["CLOSED", "REJECTED"]).select_related(
                "batch"
            ).order_by("-assigned_at")
            context["aro_recent_items"] = aro_items[:10]

        return context


class ProfileView(ActiveUserRequiredMixin, TemplateView):
    template_name = "accounts/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        try:
            profile = user.profile
            role_code = profile.role.role_code if profile.role else None
        except UserProfile.DoesNotExist:
            profile = None
            role_code = None

        context["profile_user"] = user
        context["profile"] = profile
        context["role_code"] = role_code

        if profile and role_code == "MANAGER":
            context["sub_team_leads"] = UserProfile.objects.filter(
                manager=profile, is_active=True, role__role_code="TEAM_LEAD"
            )
            context["sub_aros"] = UserProfile.objects.filter(
                manager__in=UserProfile.objects.filter(manager=profile, is_active=True),
                is_active=True, role__role_code__in=["ARO", "CALLER"],
            )
        elif profile and role_code == "TEAM_LEAD":
            context["sub_aros"] = UserProfile.objects.filter(
                manager=profile, is_active=True, role__role_code__in=["ARO", "CALLER"],
            )

        if profile and role_code in ("SUPER_ADMIN", "MANAGER", "TEAM_LEAD"):
            from analytics.services import get_dashboard_kpi
            context["kpi"] = get_dashboard_kpi()

        return context


class PasswordChangeView(ActiveUserRequiredMixin, View):
    template_name = "accounts/password_change_form.html"
    form_class = CustomPasswordChangeForm

    def get(self, request):
        form = self.form_class(request.user)
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = self.form_class(request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(
                request, _("Your password has been changed successfully.")
            )
            return redirect("accounts:password_change_done")
        return render(request, self.template_name, {"form": form})


class PasswordChangeDoneView(ActiveUserRequiredMixin, TemplateView):
    template_name = "accounts/password_change_done.html"


class PasswordResetView(AuthPasswordResetView):
    template_name = "accounts/password_reset_form.html"
    email_template_name = "accounts/password_reset_email.html"
    subject_template_name = "accounts/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")

    def form_valid(self, form):
        messages.success(
            self.request,
            _("If an account with that email exists, a reset link has been sent."),
        )
        return super().form_valid(form)


class PasswordResetDoneView(AuthPasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class PasswordResetConfirmView(AuthPasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:password_reset_complete")

    def form_valid(self, form):
        messages.success(
            self.request,
            _("Your password has been reset successfully. Please log in."),
        )
        return super().form_valid(form)


class PasswordResetCompleteView(AuthPasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"


class UserListView(SuperAdminRequiredMixin, ListView):
    model = User
    template_name = "accounts/user_list.html"
    context_object_name = "users"
    paginate_by = 20

    def get_queryset(self):
        qs = User.objects.select_related("profile__role").all()
        search = self.request.GET.get("search")
        role_filter = self.request.GET.get("role")
        status_filter = self.request.GET.get("status")
        if search:
            qs = qs.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )
        if role_filter:
            qs = qs.filter(profile__role__role_code=role_filter)
        if status_filter == "active":
            qs = qs.filter(is_active=True)
        elif status_filter == "inactive":
            qs = qs.filter(is_active=False)
        return qs.order_by("-date_joined")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["roles"] = Role.objects.filter(is_active=True)
        context["search"] = self.request.GET.get("search", "")
        context["role_filter"] = self.request.GET.get("role", "")
        context["status_filter"] = self.request.GET.get("status", "")
        return context


class UserCreateView(SuperAdminRequiredMixin, View):
    template_name = "accounts/user_form.html"
    form_class = UserCreateForm

    def get(self, request):
        form = self.form_class()
        return render(request, self.template_name, {"form": form, "is_create": True})

    def post(self, request):
        form = self.form_class(data=request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(
                request,
                _(f"User {user.get_full_name() or user.username} created successfully."),
            )
            return redirect("accounts:user_list")
        return render(request, self.template_name, {"form": form, "is_create": True})


class UserUpdateView(SuperAdminRequiredMixin, View):
    template_name = "accounts/user_form.html"
    form_class = UserUpdateForm

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        form = self.form_class(instance=user)
        return render(
            request, self.template_name,
            {"form": form, "is_create": False, "edit_user": user},
        )

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        form = self.form_class(instance=user, data=request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(
                request,
                _(f"User {user.get_full_name() or user.username} updated successfully."),
            )
            return redirect("accounts:user_list")
        return render(
            request, self.template_name,
            {"form": form, "is_create": False, "edit_user": user},
        )


class UserActivateView(SuperAdminRequiredMixin, View):
    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        form = UserActivationForm(initial={
            "user_id": user.pk,
            "action": "deactivate" if user.is_active else "activate",
        })
        return render(
            request, "accounts/user_confirm_activation.html",
            {"form": form, "target_user": user},
        )

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        form = UserActivationForm(data=request.POST)
        if form.is_valid():
            action = form.cleaned_data["action"]
            if action == "activate":
                user.is_active = True
                msg = _("User activated successfully.")
            else:
                user.is_active = False
                msg = _("User deactivated successfully.")
            user.save()
            messages.success(request, msg)
        else:
            messages.error(request, _("Invalid request."))
        return redirect("accounts:user_list")
