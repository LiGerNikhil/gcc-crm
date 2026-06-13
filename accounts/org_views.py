from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import TemplateView

from .models import User, UserProfile, Role
from .mixins import (
    SuperAdminRequiredMixin, ActiveUserRequiredMixin,
    AdminOrTeamLeadRequiredMixin,
)


# ------------------------------------------------------------------ #
#  ORG TREE
# ------------------------------------------------------------------ #
class OrganizationTreeView(ActiveUserRequiredMixin, TemplateView):
    template_name = "accounts/org/org_tree.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        profile = getattr(user, "profile", None)
        role_code = profile.role.role_code if profile and profile.role else None

        data = UserProfile.objects.select_related("user", "role", "manager__user").filter(
            is_active=True,
            role__role_code__in=["MANAGER", "TEAM_LEAD", "ARO", "CALLER"],
        )

        if role_code == "MANAGER":
            data = data.filter(Q(manager=profile) | Q(pk=profile.pk))
        elif role_code == "TEAM_LEAD":
            data = data.filter(Q(manager=profile) | Q(pk=profile.pk))
        elif role_code in ("ARO", "CALLER", "DATA_ENTRY"):
            data = data.filter(pk=profile.pk) if profile else data.none()

        managers = data.filter(role__role_code="MANAGER") if role_code == "SUPER_ADMIN" else data.filter(
            Q(role__role_code="MANAGER") & Q(manager=profile)
        ) if role_code == "MANAGER" else data.filter(pk=profile.pk)

        unassigned = data.filter(
            manager__isnull=True, role__role_code__in=["TEAM_LEAD", "ARO", "CALLER"],
        ) if role_code == "SUPER_ADMIN" else data.none()

        context["role_code"] = role_code
        context["managers"] = managers
        context["unassigned"] = unassigned
        context["profiles"] = {p.pk: p for p in data}
        return context


# ------------------------------------------------------------------ #
#  CREATE MANAGER
# ------------------------------------------------------------------ #
class ManagerCreateView(SuperAdminRequiredMixin, View):
    template_name = "accounts/org/manager_form.html"

    def get(self, request):
        from .org_forms import ManagerCreateForm
        form = ManagerCreateForm()
        return render(request, self.template_name, {"form": form, "is_create": True})

    def post(self, request):
        from .org_forms import ManagerCreateForm
        form = ManagerCreateForm(data=request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, _(f"Manager {user.get_full_name() or user.username} created."))
            return redirect("org:org_tree")
        return render(request, self.template_name, {"form": form, "is_create": True})


class ManagerUpdateView(SuperAdminRequiredMixin, View):
    template_name = "accounts/org/manager_form.html"

    def get(self, request, pk):
        from .org_forms import ManagerUpdateForm
        profile = get_object_or_404(UserProfile.objects.select_related("user"), pk=pk)
        form = ManagerUpdateForm(instance=profile.user)
        return render(request, self.template_name, {"form": form, "is_create": False, "edit_user": profile.user})

    def post(self, request, pk):
        from .org_forms import ManagerUpdateForm
        profile = get_object_or_404(UserProfile.objects.select_related("user"), pk=pk)
        form = ManagerUpdateForm(instance=profile.user, data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _(f"Manager {profile.user.get_full_name() or profile.user.username} updated."))
            return redirect("org:org_tree")
        return render(request, self.template_name, {"form": form, "is_create": False, "edit_user": profile.user})


class ManagerDetailView(AdminOrTeamLeadRequiredMixin, TemplateView):
    template_name = "accounts/org/manager_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs["pk"]
        profile = get_object_or_404(
            UserProfile.objects.select_related("user", "role"),
            pk=pk, role__role_code="MANAGER",
        )
        team_leads = UserProfile.objects.select_related("user", "role").filter(
            manager=profile, is_active=True
        ).annotate(
            aro_count=Count("subordinates", filter=Q(subordinates__role__role_code__in=["ARO", "CALLER"], subordinates__is_active=True))
        )
        aros = UserProfile.objects.select_related("user", "role", "manager__user").filter(
            manager__in=team_leads, is_active=True,
            role__role_code__in=["ARO", "CALLER"],
        )
        context["manager"] = profile
        context["team_leads"] = team_leads
        context["aros"] = aros
        return context


# ------------------------------------------------------------------ #
#  CREATE TEAM LEAD
# ------------------------------------------------------------------ #
class TeamLeadCreateView(SuperAdminRequiredMixin, View):
    template_name = "accounts/org/teamlead_form.html"

    def get(self, request):
        from .org_forms import TeamLeadCreateForm
        form = TeamLeadCreateForm()
        return render(request, self.template_name, {"form": form, "is_create": True})

    def post(self, request):
        from .org_forms import TeamLeadCreateForm
        form = TeamLeadCreateForm(data=request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, _(f"Team Lead {user.get_full_name() or user.username} created."))
            return redirect("org:org_tree")
        return render(request, self.template_name, {"form": form, "is_create": True})


class TeamLeadUpdateView(SuperAdminRequiredMixin, View):
    template_name = "accounts/org/teamlead_form.html"

    def get(self, request, pk):
        from .org_forms import TeamLeadUpdateForm
        profile = get_object_or_404(UserProfile.objects.select_related("user"), pk=pk)
        form = TeamLeadUpdateForm(instance=profile.user)
        return render(request, self.template_name, {"form": form, "is_create": False, "edit_user": profile.user})

    def post(self, request, pk):
        from .org_forms import TeamLeadUpdateForm
        profile = get_object_or_404(UserProfile.objects.select_related("user"), pk=pk)
        form = TeamLeadUpdateForm(instance=profile.user, data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _(f"Team Lead {profile.user.get_full_name() or profile.user.username} updated."))
            return redirect("org:org_tree")
        return render(request, self.template_name, {"form": form, "is_create": False, "edit_user": profile.user})


class TeamLeadDetailView(AdminOrTeamLeadRequiredMixin, TemplateView):
    template_name = "accounts/org/teamlead_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs["pk"]
        profile = get_object_or_404(
            UserProfile.objects.select_related("user", "role", "manager__user"),
            pk=pk, role__role_code="TEAM_LEAD",
        )
        aros = UserProfile.objects.select_related("user", "role").filter(
            manager=profile, is_active=True,
            role__role_code__in=["ARO", "CALLER"],
        )
        from leads.models import Lead
        assigned_leads = Lead.objects.filter(assigned_to=profile.user, is_deleted=False)
        recent_calls = []
        try:
            recent_calls = assigned_leads[:0]
        except Exception:
            pass
        context["team_lead"] = profile
        context["aros"] = aros
        context["assigned_leads_count"] = assigned_leads.count()
        return context


# ------------------------------------------------------------------ #
#  CREATE ARO
# ------------------------------------------------------------------ #
class AROCreateView(SuperAdminRequiredMixin, View):
    template_name = "accounts/org/aro_form.html"

    def get(self, request):
        from .org_forms import AROCreateForm
        form = AROCreateForm()
        return render(request, self.template_name, {"form": form, "is_create": True})

    def post(self, request):
        from .org_forms import AROCreateForm
        form = AROCreateForm(data=request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, _(f"ARO {user.get_full_name() or user.username} created."))
            return redirect("org:org_tree")
        return render(request, self.template_name, {"form": form, "is_create": True})


class AROUpdateView(SuperAdminRequiredMixin, View):
    template_name = "accounts/org/aro_form.html"

    def get(self, request, pk):
        from .org_forms import AROUpdateForm
        profile = get_object_or_404(UserProfile.objects.select_related("user"), pk=pk)
        form = AROUpdateForm(instance=profile.user)
        return render(request, self.template_name, {"form": form, "is_create": False, "edit_user": profile.user})

    def post(self, request, pk):
        from .org_forms import AROUpdateForm
        profile = get_object_or_404(UserProfile.objects.select_related("user"), pk=pk)
        form = AROUpdateForm(instance=profile.user, data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _(f"ARO {profile.user.get_full_name() or profile.user.username} updated."))
            return redirect("org:org_tree")
        return render(request, self.template_name, {"form": form, "is_create": False, "edit_user": profile.user})


class ARODetailView(AdminOrTeamLeadRequiredMixin, TemplateView):
    template_name = "accounts/org/aro_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs["pk"]
        profile = get_object_or_404(
            UserProfile.objects.select_related("user", "role", "manager__user"),
            pk=pk, role__role_code__in=["ARO", "CALLER"],
        )
        from leads.models import Lead
        assigned_leads = Lead.objects.filter(assigned_to=profile.user, is_deleted=False)
        context["aro"] = profile
        context["assigned_leads"] = assigned_leads.select_related("batch__campaign__bank_source").order_by("-created_at")[:20]
        context["assigned_leads_count"] = assigned_leads.count()
        return context
