from django.views.generic import ListView, DetailView
from django.db.models import Q
from accounts.mixins import AdminOrTeamLeadRequiredMixin
from .models import AuditLog


class AuditLogListView(AdminOrTeamLeadRequiredMixin, ListView):
    model = AuditLog
    template_name = "audit/auditlog_list.html"
    context_object_name = "logs"
    paginate_by = 50

    def get_queryset(self):
        qs = AuditLog.objects.select_related("user").all()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(model_name__icontains=q)
                | Q(action__icontains=q)
                | Q(description__icontains=q)
                | Q(user__username__icontains=q)
                | Q(record_id__icontains=q)
            )
        action = self.request.GET.get("action", "").strip()
        if action:
            qs = qs.filter(action=action)
        model = self.request.GET.get("model", "").strip()
        if model:
            qs = qs.filter(model_name__icontains=model)
        user_id = self.request.GET.get("user", "").strip()
        if user_id:
            qs = qs.filter(user_id=user_id)
        return qs.order_by("-timestamp")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["action_choices"] = AuditLog.ACTION_CHOICES
        ctx["active_action"] = self.request.GET.get("action", "")
        ctx["active_model"] = self.request.GET.get("model", "")
        ctx["search_query"] = self.request.GET.get("q", "")
        ctx["model_names"] = (
            AuditLog.objects.values_list("model_name", flat=True)
            .distinct().order_by("model_name")
        )
        return ctx


class AuditLogDetailView(AdminOrTeamLeadRequiredMixin, DetailView):
    model = AuditLog
    template_name = "audit/auditlog_detail.html"
    context_object_name = "log"

    def get_queryset(self):
        return AuditLog.objects.select_related("user").all()
