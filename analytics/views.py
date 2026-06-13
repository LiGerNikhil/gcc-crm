from django.views.generic import TemplateView
from accounts.mixins import AdminOrTeamLeadRequiredMixin
from .services import (
    get_source_wise_stats,
    get_lead_metrics,
    get_employee_metrics,
    get_lead_status_distribution,
    get_monthly_trends,
)


class AnalyticsDashboardView(AdminOrTeamLeadRequiredMixin, TemplateView):
    template_name = "analytics/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["source_stats"] = get_source_wise_stats()
        ctx["lead_metrics"] = get_lead_metrics()
        ctx["employee_metrics"] = get_employee_metrics()
        ctx["status_distribution"] = get_lead_status_distribution()
        ctx["monthly_trends"] = get_monthly_trends()
        return ctx
