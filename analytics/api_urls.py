from django.urls import path
from . import api_views

app_name = "analytics_api"

urlpatterns = [
    path("analytics/source-wise/", api_views.source_wise_stats, name="source_wise"),
    path("analytics/lead-metrics/", api_views.lead_metrics, name="lead_metrics"),
    path("analytics/employee-metrics/", api_views.employee_metrics, name="employee_metrics"),
    path("analytics/status-distribution/", api_views.status_distribution, name="status_distribution"),
    path("analytics/monthly-trends/", api_views.monthly_trends, name="monthly_trends"),
]
