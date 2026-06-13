from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import AuditLogViewSet, UserActionLogViewSet

router = DefaultRouter()
router.register(r"audit-logs", AuditLogViewSet, basename="api_audit_log")
router.register(r"user-action-logs", UserActionLogViewSet, basename="api_user_action_log")

app_name = "audit_api"

urlpatterns = [
    path("", include(router.urls)),
]
