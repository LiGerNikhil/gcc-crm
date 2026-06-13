from django.views.generic import ListView, DetailView, CreateView, UpdateView, View, TemplateView, FormView
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.db.models import Q, Count

from accounts.mixins import ActiveUserRequiredMixin, AdminOrTeamLeadRequiredMixin, CallerRequiredMixin
from .models import Lead, LeadNote, FollowUp, LeadAssignment, LeadStatusLog, AssignmentRule, LeadCall
from .forms import (
    LeadForm, LeadNoteForm, FollowUpForm, BulkAssignForm,
    RoundRobinAssignForm, ReassignForm, AssignmentRuleForm, QuickStatusForm, CallForm,
)
from .filters import LeadFilter
from .services import (
    assign_lead_manual, assign_lead_bulk, assign_round_robin,
    reassign_lead, get_assignment_history, get_available_callers,
    get_caller_load, get_assignment_stats, get_lead_timeline,
)


class LeadListView(ActiveUserRequiredMixin, ListView):
    model = Lead
    template_name = "leads/lead_list.html"
    context_object_name = "leads"
    paginate_by = 25

    def get_queryset(self):
        qs = Lead.objects.filter(is_deleted=False).select_related(
            "assigned_to", "batch__campaign__bank_source"
        )
        if self.request.user.profile.role.role_code == "CALLER":
            qs = qs.filter(assigned_to=self.request.user)
        f = LeadFilter(self.request.GET, queryset=qs)
        return f.qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filter"] = LeadFilter(self.request.GET)
        ctx["status_counts"] = (
            Lead.objects.filter(is_deleted=False)
            .values("lead_status")
            .annotate(count=Count("id"))
            .order_by("lead_status")
        )
        return ctx


class LeadDetailView(ActiveUserRequiredMixin, DetailView):
    model = Lead
    template_name = "leads/lead_detail.html"
    context_object_name = "lead"

    def get_queryset(self):
        return Lead.objects.filter(is_deleted=False).select_related(
            "assigned_to", "batch__campaign__bank_source"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        lead = self.object
        ctx["notes"] = lead.lead_notes.select_related("created_by").all()
        ctx["followups"] = lead.lead_followups.select_related("assigned_to", "created_by").all()
        ctx["assignments"] = get_assignment_history(lead=lead)
        ctx["status_logs"] = lead.status_logs.select_related("changed_by").all()
        ctx["note_form"] = LeadNoteForm()
        ctx["followup_form"] = FollowUpForm()
        ctx["status_form"] = QuickStatusForm()
        ctx["reassign_form"] = ReassignForm()
        ctx["bulk_form"] = BulkAssignForm()
        ctx["assignment_stats"] = get_assignment_stats()
        ctx["timeline"] = get_lead_timeline(lead, limit=50)
        ctx["call_form"] = CallForm()
        ctx["calls"] = lead.calls.select_related("caller").all()
        return ctx


class LeadCreateView(AdminOrTeamLeadRequiredMixin, CreateView):
    model = Lead
    form_class = LeadForm
    template_name = "leads/lead_form.html"

    def get_success_url(self):
        return reverse("leads:detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, "Lead created successfully.")
        return super().form_valid(form)


class LeadUpdateView(ActiveUserRequiredMixin, UpdateView):
    model = Lead
    form_class = LeadForm
    template_name = "leads/lead_form.html"

    def get_queryset(self):
        return Lead.objects.filter(is_deleted=False)

    def get_success_url(self):
        return reverse("leads:detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, "Lead updated successfully.")
        return super().form_valid(form)


class LeadDeleteView(AdminOrTeamLeadRequiredMixin, View):
    def post(self, request, pk):
        lead = get_object_or_404(Lead, pk=pk, is_deleted=False)
        lead.is_deleted = True
        lead.deleted_at = timezone.now()
        lead.save(update_fields=["is_deleted", "deleted_at"])
        messages.success(request, "Lead deleted successfully.")
        return redirect("leads:list")


class LeadAssignView(AdminOrTeamLeadRequiredMixin, FormView):
    form_class = BulkAssignForm
    template_name = "leads/lead_assign_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        lead_ids = self.request.GET.getlist("leads") or self.request.POST.getlist("leads")
        ctx["leads"] = Lead.objects.filter(id__in=lead_ids, is_deleted=False)
        ctx["assign_mode"] = "bulk"
        ctx["round_robin_form"] = RoundRobinAssignForm(user=self.request.user)
        return ctx

    def form_valid(self, form):
        lead_ids = self.request.POST.getlist("leads")
        user = form.cleaned_data["assign_to"]
        results = assign_lead_bulk(lead_ids, user, assigned_by=self.request.user)
        success_count = sum(1 for r in results if r["success"])
        messages.success(self.request, f"{success_count} lead(s) assigned successfully.")
        return redirect("leads:list")


class LeadAssignRoundRobinView(AdminOrTeamLeadRequiredMixin, FormView):
    form_class = RoundRobinAssignForm
    template_name = "leads/lead_assign_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        lead_ids = self.request.GET.getlist("leads") or self.request.POST.getlist("leads")
        ctx["leads"] = Lead.objects.filter(id__in=lead_ids, is_deleted=False)
        ctx["assign_mode"] = "round_robin"
        return ctx

    def form_valid(self, form):
        lead_ids = self.request.POST.getlist("leads")
        rule = form.cleaned_data["rule"]
        try:
            results, rule_used = assign_round_robin(
                lead_ids, rule.id, assigned_by=self.request.user
            )
            success_count = sum(1 for r in results if r["success"])
            messages.success(
                self.request,
                f"{success_count} lead(s) assigned via round-robin (rule: {rule_used.name}).",
            )
        except ValueError as e:
            messages.error(self.request, str(e))
        return redirect("leads:list")


class LeadReassignView(AdminOrTeamLeadRequiredMixin, View):
    def post(self, request, pk):
        lead = get_object_or_404(Lead, pk=pk, is_deleted=False)
        form = ReassignForm(request.POST)
        if form.is_valid():
            new_user = form.cleaned_data["assign_to"]
            reason = form.cleaned_data.get("reason", "")
            reassign_lead(lead, new_user, assigned_by=request.user, reason=reason)
            messages.success(request, f"Lead reassigned to {new_user.get_full_name() or new_user.username}.")
        else:
            for error in form.errors.values():
                messages.error(request, error)
        return redirect("leads:detail", pk=pk)


class LeadUpdateStatusView(ActiveUserRequiredMixin, View):
    def post(self, request, pk):
        lead = get_object_or_404(Lead, pk=pk, is_deleted=False)
        form = QuickStatusForm(request.POST)
        if form.is_valid():
            from .services import change_lead_status
            new_status = form.cleaned_data["status"]
            notes = form.cleaned_data.get("notes", "")
            if change_lead_status(lead, new_status, changed_by=request.user, notes=notes):
                messages.success(request, f"Lead status updated to {lead.get_lead_status_display()}.")
            else:
                messages.info(request, "Lead status unchanged.")
        return redirect("leads:detail", pk=pk)


class LeadNoteCreateView(ActiveUserRequiredMixin, View):
    def post(self, request, pk):
        lead = get_object_or_404(Lead, pk=pk, is_deleted=False)
        form = LeadNoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.lead = lead
            note.created_by = request.user
            note.save()
            messages.success(request, "Note added successfully.")
        else:
            for error in form.errors.values():
                messages.error(request, error)
        return redirect("leads:detail", pk=pk)


class FollowUpCreateView(ActiveUserRequiredMixin, View):
    def post(self, request, pk):
        lead = get_object_or_404(Lead, pk=pk, is_deleted=False)
        form = FollowUpForm(request.POST)
        if form.is_valid():
            followup = form.save(commit=False)
            followup.lead = lead
            followup.created_by = request.user
            followup.save()
            messages.success(request, "Follow-up scheduled successfully.")
        else:
            for error in form.errors.values():
                messages.error(request, error)
        return redirect("leads:detail", pk=pk)


class FollowUpCompleteView(ActiveUserRequiredMixin, View):
    def post(self, request, pk, fupk):
        followup = get_object_or_404(FollowUp, pk=fupk, lead_id=pk)
        followup.status = "COMPLETED"
        followup.completed_at = timezone.now()
        followup.save(update_fields=["status", "completed_at"])
        messages.success(request, "Follow-up marked as completed.")
        return redirect("leads:detail", pk=pk)


class LeadTimelineView(ActiveUserRequiredMixin, TemplateView):
    template_name = "leads/lead_timeline.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        lead = get_object_or_404(Lead.objects.filter(is_deleted=False), pk=self.kwargs["pk"])
        ctx["lead"] = lead
        ctx["timeline"] = get_lead_timeline(lead, limit=200)
        return ctx


class LeadCallCreateView(ActiveUserRequiredMixin, CreateView):
    model = LeadCall
    form_class = CallForm

    def form_valid(self, form):
        lead = get_object_or_404(Lead.objects.filter(is_deleted=False), pk=self.kwargs["pk"])
        form.instance.lead = lead
        form.instance.caller = self.request.user
        if not form.instance.call_time:
            form.instance.call_time = timezone.now()
        messages.success(self.request, "Call logged successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("leads:detail", kwargs={"pk": self.kwargs["pk"]})


class AssignmentHistoryView(AdminOrTeamLeadRequiredMixin, ListView):
    model = LeadAssignment
    template_name = "leads/assignment_history.html"
    context_object_name = "assignments"
    paginate_by = 50

    def get_queryset(self):
        qs = LeadAssignment.objects.select_related(
            "lead", "assigned_to", "assigned_by"
        ).all()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(lead__customer_name__icontains=q)
                | Q(lead__lead_number__icontains=q)
                | Q(assigned_to__username__icontains=q)
                | Q(assigned_by__username__icontains=q)
            )
        assignment_type = self.request.GET.get("type", "").strip()
        if assignment_type:
            qs = qs.filter(assignment_type=assignment_type)
        status = self.request.GET.get("status", "").strip()
        if status:
            qs = qs.filter(assignment_status=status)
        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["assignment_type_choices"] = LeadAssignment.ASSIGNMENT_TYPE_CHOICES
        ctx["assignment_status_choices"] = LeadAssignment.ASSIGNMENT_STATUS_CHOICES
        ctx["active_type"] = self.request.GET.get("type", "")
        ctx["active_status"] = self.request.GET.get("status", "")
        ctx["search_query"] = self.request.GET.get("q", "")
        ctx["stats"] = get_assignment_stats()
        return ctx


class AssignmentRuleListView(AdminOrTeamLeadRequiredMixin, ListView):
    model = AssignmentRule
    template_name = "leads/assignment_rules.html"
    context_object_name = "rules"
    paginate_by = 20
    ordering = ["-created_at"]

    def get_queryset(self):
        return AssignmentRule.objects.filter(
            team_lead=self.request.user
        ).select_related("campaign", "team_lead").annotate(
            caller_count=Count("round_robin_counters")
        ).all()


class AssignmentRuleCreateView(AdminOrTeamLeadRequiredMixin, CreateView):
    model = AssignmentRule
    form_class = AssignmentRuleForm
    template_name = "leads/assignment_rule_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse("leads:assignment_rules")

    def form_valid(self, form):
        messages.success(self.request, f"Rule '{form.instance.name}' created successfully.")
        return super().form_valid(form)


class AssignmentRuleUpdateView(AdminOrTeamLeadRequiredMixin, UpdateView):
    model = AssignmentRule
    form_class = AssignmentRuleForm
    template_name = "leads/assignment_rule_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse("leads:assignment_rules")

    def form_valid(self, form):
        messages.success(self.request, f"Rule '{form.instance.name}' updated successfully.")
        return super().form_valid(form)


class AssignmentRuleDeleteView(AdminOrTeamLeadRequiredMixin, View):
    def post(self, request, pk):
        rule = get_object_or_404(AssignmentRule, pk=pk, team_lead=request.user)
        rule.delete()
        messages.success(request, "Assignment rule deleted.")
        return redirect("leads:assignment_rules")
