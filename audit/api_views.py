from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated
from .models import AuditLog, UserActionLog
from .serializers import AuditLogSerializer, UserActionLogSerializer


class AuditLogViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = AuditLog.objects.select_related("user").all().order_by("-timestamp")
    permission_classes = [IsAuthenticated]
    serializer_class = AuditLogSerializer
    filterset_fields = ["action", "model_name", "user"]
    search_fields = ["description", "model_name", "record_id"]


class UserActionLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = UserActionLog.objects.select_related("user").all().order_by("-timestamp")
    permission_classes = [IsAuthenticated]
    serializer_class = UserActionLogSerializer
    filterset_fields = ["action_type", "user"]
