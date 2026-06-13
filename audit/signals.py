import json
from django.db.models import Q
from django.db.models.signals import post_save, pre_save
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from .models import AuditLog, UserActionLog
from .services import create_audit_log, create_user_action_log

User = get_user_model()


def _get_changed_fields(instance, created=False):
    """Return dict of changed field names with (old, new) values."""
    if created or not instance.pk:
        return {}
    try:
        old = instance.__class__.objects.get(pk=instance.pk)
    except instance.__class__.DoesNotExist:
        return {}
    changed = {}
    for field in instance._meta.get_fields():
        if not hasattr(field, "attname"):
            continue
        name = field.attname
        try:
            old_val = getattr(old, name)
            new_val = getattr(instance, name)
        except Exception:
            continue
        if old_val != new_val:
            changed[name] = (str(old_val)[:500], str(new_val)[:500])
    return changed


# ------------------------------------------------------------------ #
#  LOGIN / LOGOUT
# ------------------------------------------------------------------ #
@receiver(user_logged_in)
def audit_user_login(sender, request, user, **kwargs):
    create_audit_log(
        user=user,
        model_name="User",
        record_id=user.pk,
        action="LOGIN",
        ip_address=getattr(request, "audit_ip", None),
        user_agent=getattr(request, "audit_user_agent", ""),
        description=f"User {user.get_full_name() or user.username} logged in",
    )
    create_user_action_log(
        user=user,
        action_type="LOGIN",
        ip_address=getattr(request, "audit_ip", None),
    )


@receiver(user_logged_out)
def audit_user_logout(sender, request, user, **kwargs):
    if not user:
        return
    create_audit_log(
        user=user,
        model_name="User",
        record_id=user.pk,
        action="LOGOUT",
        ip_address=getattr(request, "audit_ip", None),
        user_agent=getattr(request, "audit_user_agent", ""),
        description=f"User {user.get_full_name() or user.username} logged out",
    )
    create_user_action_log(
        user=user,
        action_type="LOGOUT",
        ip_address=getattr(request, "audit_ip", None),
    )


# ------------------------------------------------------------------ #
#  LEAD CREATES / UPDATES / SOFT-DELETES
# ------------------------------------------------------------------ #
@receiver(pre_save, sender="leads.Lead")
def audit_lead_pre_save(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return
    changes = {}
    for field in instance._meta.get_fields():
        if not hasattr(field, "attname"):
            continue
        name = field.attname
        if name in ("updated_at",):
            continue
        try:
            old_val = getattr(old, name)
            new_val = getattr(instance, name)
        except Exception:
            continue
        if old_val != new_val:
            changes[name] = {"old": str(old_val)[:500], "new": str(new_val)[:500]}
    instance._audit_changes = changes


@receiver(post_save, sender="leads.Lead")
def audit_lead_post_save(sender, instance, created, **kwargs):
    changes = getattr(instance, "_audit_changes", None)

    if created:
        create_audit_log(
            model_name="Lead",
            record_id=instance.pk,
            action="CREATE",
            new_values={"lead_number": instance.lead_number, "customer_name": instance.customer_name},
            description=f"Lead {instance.lead_number} ({instance.customer_name}) created",
        )
        return

    if changes:
        old_vals = {k: v["old"] for k, v in changes.items()}
        new_vals = {k: v["new"] for k, v in changes.items()}

        # Detect soft-delete
        if "is_deleted" in changes and changes["is_deleted"]["new"] == "True":
            action = "DELETE"
            desc = f"Lead {instance.lead_number} deleted"
        else:
            action = "UPDATE"
            desc = f"Lead {instance.lead_number} updated: {', '.join(changes.keys())}"

        create_audit_log(
            model_name="Lead",
            record_id=instance.pk,
            action=action,
            old_values=old_vals,
            new_values=new_vals,
            description=desc,
        )

        create_user_action_log(
            user=getattr(instance, "_audit_user", None),
            action_type="LEAD_EDIT",
            resource_type="Lead",
            resource_id=instance.pk,
            details={"changed_fields": list(changes.keys())},
        )


# ------------------------------------------------------------------ #
#  LEAD NOTES
# ------------------------------------------------------------------ #
@receiver(post_save, sender="leads.LeadNote")
def audit_lead_note(sender, instance, created, **kwargs):
    if not created:
        return
    create_audit_log(
        user=instance.created_by,
        model_name="LeadNote",
        record_id=instance.pk,
        action="CREATE",
        new_values={"lead": str(instance.lead_id), "note_type": instance.note_type, "content": instance.content[:200]},
        description=f"Note added to lead {instance.lead.lead_number}",
    )


# ------------------------------------------------------------------ #
#  LEAD ASSIGNMENTS
# ------------------------------------------------------------------ #
@receiver(post_save, sender="leads.LeadAssignment")
def audit_lead_assignment(sender, instance, created, **kwargs):
    action = "CREATE" if created else "UPDATE"
    new_vals = {
        "lead": str(instance.lead_id),
        "assigned_to": str(instance.assigned_to_id),
        "assignment_type": instance.assignment_type,
    }
    desc = f"Lead {instance.lead.lead_number} assigned to {instance.assigned_to.get_full_name() or instance.assigned_to.username}"

    create_audit_log(
        user=instance.assigned_by or instance.assigned_to,
        model_name="LeadAssignment",
        record_id=instance.pk,
        action="ASSIGN" if created else action,
        new_values=new_vals,
        description=desc,
    )
    create_user_action_log(
        user=instance.assigned_by or instance.assigned_to,
        action_type="LEAD_EDIT",
        resource_type="Lead",
        resource_id=instance.lead_id,
        details={"assignment_type": instance.assignment_type},
    )


# ------------------------------------------------------------------ #
#  FILE UPLOADS (Excel)
# ------------------------------------------------------------------ #
@receiver(post_save, sender="excel.ExcelImport")
def audit_excel_upload(sender, instance, created, **kwargs):
    if not created:
        return
    create_audit_log(
        user=instance.created_by,
        model_name="ExcelImport",
        record_id=instance.pk,
        action="CREATE",
        new_values={
            "file_name": instance.file_name,
            "file_size": instance.file_size,
            "status": instance.status,
        },
        description=f"Excel file uploaded: {instance.file_name} ({instance.file_size or 0} bytes)",
    )
    create_user_action_log(
        user=instance.created_by,
        action_type="IMPORT_START",
        resource_type="ExcelImport",
        resource_id=instance.pk,
        details={"file_name": instance.file_name},
    )


# ------------------------------------------------------------------ #
#  FILE UPLOADS (Images)
# ------------------------------------------------------------------ #
@receiver(post_save, sender="imager.ImageUpload")
def audit_image_upload(sender, instance, created, **kwargs):
    if not created:
        return
    create_audit_log(
        user=instance.uploaded_by,
        model_name="ImageUpload",
        record_id=instance.pk,
        action="CREATE",
        new_values={
            "file_name": instance.file_name,
            "file_size": instance.file_size,
        },
        description=f"Image uploaded: {instance.file_name} ({instance.file_size or 0} bytes)",
    )
    create_user_action_log(
        user=instance.uploaded_by,
        action_type="IMPORT_START",
        resource_type="ImageUpload",
        resource_id=instance.pk,
        details={"file_name": instance.file_name},
    )


# ------------------------------------------------------------------ #
#  USER CREATES / UPDATES
# ------------------------------------------------------------------ #
@receiver(post_save, sender=User)
def audit_user_save(sender, instance, created, **kwargs):
    if created:
        create_audit_log(
            model_name="User",
            record_id=instance.pk,
            action="CREATE",
            new_values={"username": instance.username, "email": instance.email, "is_active": instance.is_active},
            description=f"User account created: {instance.username}",
        )
        return

    if not kwargs.get("update_fields"):
        return

    create_audit_log(
        model_name="User",
        record_id=instance.pk,
        action="UPDATE",
        new_values={"username": instance.username, "is_active": instance.is_active},
        description=f"User account updated: {instance.username}",
    )


# ------------------------------------------------------------------ #
#  STATUS CHANGE LOG (Lead status -> separate audit trail)
# ------------------------------------------------------------------ #
@receiver(post_save, sender="leads.LeadStatusLog")
def audit_lead_status_change(sender, instance, created, **kwargs):
    if not created:
        return
    create_audit_log(
        user=instance.changed_by,
        model_name="Lead",
        record_id=instance.lead_id,
        action="UPDATE",
        old_values={"lead_status": instance.old_status},
        new_values={"lead_status": instance.new_status},
        description=f"Lead {instance.lead.lead_number} status: {instance.old_status or 'NEW'} -> {instance.new_status}",
    )
