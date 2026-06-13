import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _


class AuditLog(models.Model):
    """Comprehensive audit logging for compliance and tracking."""
    
    ACTION_CHOICES = [
        ("CREATE", _("Create")),
        ("UPDATE", _("Update")),
        ("DELETE", _("Delete")),
        ("VIEW", _("View")),
        ("EXPORT", _("Export")),
        ("LOGIN", _("Login")),
        ("LOGOUT", _("Logout")),
        ("ASSIGN", _("Assign")),
        ("BULK_ACTION", _("Bulk Action")),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="audit_logs",
        verbose_name=_("User"),
        help_text=_("User who performed the action")
    )
    model_name = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name=_("Model Name"),
        help_text=_("Name of the model affected (Lead, Activity, etc.)")
    )
    record_id = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name=_("Record ID"),
        help_text=_("ID of the record affected")
    )
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        db_index=True,
        verbose_name=_("Action"),
        help_text=_("Type of action performed")
    )
    old_values = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Old Values'),
        help_text=_('Previous values before change (JSON format). Use JSONField with PostgreSQL.')
    )
    new_values = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('New Values'),
        help_text=_('New values after change (JSON format). Use JSONField with PostgreSQL.')
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_("IP Address"),
        help_text=_("IP address of the user")
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name=_("User Agent"),
        help_text=_("Browser/client user agent string")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Human-readable description of the action")
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name=_("Timestamp"),
        help_text=_("When the action occurred")
    )
    
    class Meta:
        verbose_name = _("Audit Log")
        verbose_name_plural = _("Audit Logs")
        db_table = "audit_log"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["user", "timestamp"], name="audit_user_time_idx"),
            models.Index(fields=["model_name", "record_id"], name="audit_model_record_idx"),
            models.Index(fields=["action"], name="audit_action_idx"),
            models.Index(fields=["timestamp"], name="audit_timestamp_idx"),
        ]
    
    def __str__(self):
        return f"{self.get_action_display()}: {self.model_name}({self.record_id})"


class UserActionLog(models.Model):
    """User-specific action logging for analytics."""
    
    ACTION_TYPE_CHOICES = [
        ("LOGIN", _("Login")),
        ("LOGOUT", _("Logout")),
        ("LEAD_VIEW", _("Lead View")),
        ("LEAD_EDIT", _("Lead Edit")),
        ("ACTIVITY_CREATE", _("Activity Create")),
        ("ACTIVITY_COMPLETE", _("Activity Complete")),
        ("REPORT_GENERATE", _("Report Generate")),
        ("IMPORT_START", _("Import Start")),
        ("IMPORT_COMPLETE", _("Import Complete")),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="user_actions",
        verbose_name=_("User"),
        help_text=_("User who performed the action")
    )
    action_type = models.CharField(
        max_length=30,
        choices=ACTION_TYPE_CHOICES,
        db_index=True,
        verbose_name=_("Action Type"),
        help_text=_("Type of action performed")
    )
    resource_type = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("Resource Type"),
        help_text=_("Type of resource affected (Lead, Activity, etc.)")
    )
    resource_id = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        verbose_name=_("Resource ID"),
        help_text=_("ID of the resource affected")
    )
    duration_seconds = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_("Duration (Seconds)"),
        help_text=_("Time spent on the action")
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_("IP Address")
    )
    status = models.CharField(
        max_length=20,
        default="SUCCESS",
        verbose_name=_("Status"),
        help_text=_("Success or failure status")
    )
    details = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Details'),
        help_text=_('Additional details about the action (JSON format). Use JSONField with PostgreSQL.')
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name=_("Timestamp")
    )
    
    class Meta:
        verbose_name = _("User Action Log")
        verbose_name_plural = _("User Action Logs")
        db_table = "audit_user_action_log"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["user", "timestamp"], name="action_user_time_idx"),
            models.Index(fields=["action_type"], name="action_type_idx"),
            models.Index(fields=["user", "action_type"], name="action_user_type_idx"),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_action_type_display()}"
