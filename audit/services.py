import json
import uuid
from django.utils import timezone
from .models import AuditLog, UserActionLog


def create_audit_log(
    user=None,
    model_name="",
    record_id="",
    action="",
    old_values=None,
    new_values=None,
    ip_address=None,
    user_agent="",
    description="",
):
    return AuditLog.objects.create(
        user=user,
        model_name=model_name,
        record_id=str(record_id) if record_id else "",
        action=action,
        old_values=json.dumps(old_values) if old_values else None,
        new_values=json.dumps(new_values) if new_values else None,
        ip_address=ip_address,
        user_agent=user_agent or "",
        description=description,
    )


def create_user_action_log(
    user,
    action_type="",
    resource_type="",
    resource_id="",
    duration_seconds=None,
    ip_address=None,
    status="SUCCESS",
    details=None,
):
    return UserActionLog.objects.create(
        user=user,
        action_type=action_type,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else "",
        duration_seconds=duration_seconds,
        ip_address=ip_address,
        status=status,
        details=json.dumps(details) if details else None,
    )


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def get_user_agent(request):
    return request.META.get("HTTP_USER_AGENT", "")[:255]
