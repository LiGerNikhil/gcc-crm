from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import LeadViewSet, AssignmentRuleViewSet, AssignmentHistoryViewSet, LeadCallViewSet

router = DefaultRouter()
router.register(r"leads", LeadViewSet, basename="api_lead")
router.register(r"lead-calls", LeadCallViewSet, basename="api_lead_call")
router.register(r"assignment-rules", AssignmentRuleViewSet, basename="api_assignment_rule")
router.register(r"assignment-history", AssignmentHistoryViewSet, basename="api_assignment_history")

app_name = "leads_api"

urlpatterns = [
    path("", include(router.urls)),
]
