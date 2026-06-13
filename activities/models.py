import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _


class Activity(models.Model):
    """Activity/Follow-up tracking for leads."""
    
    ACTIVITY_TYPE_CHOICES = [
        ("CALL", _("Phone Call")),
        ("EMAIL", _("Email")),
        ("SMS", _("SMS")),
        ("SITE_VISIT", _("Site Visit")),
        ("DOCUMENT_SUBMISSION", _("Document Submission")),
        ("FEEDBACK", _("Feedback Collection")),
    ]
    
    STATUS_CHOICES = [
        ("SCHEDULED", _("Scheduled")),
        ("IN_PROGRESS", _("In Progress")),
        ("COMPLETED", _("Completed")),
        ("CANCELLED", _("Cancelled")),
        ("PENDING", _("Pending")),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lead = models.ForeignKey(
        "leads.Lead",
        on_delete=models.CASCADE,
        related_name="activities",
        verbose_name=_("Lead"),
        help_text=_("Associated lead")
    )
    assigned_to = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activities",
        verbose_name=_("Assigned To"),
        help_text=_("User responsible for this activity")
    )
    activity_type = models.CharField(
        max_length=20,
        choices=ACTIVITY_TYPE_CHOICES,
        db_index=True,
        verbose_name=_("Activity Type"),
        help_text=_("Type of activity/follow-up")
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="SCHEDULED",
        db_index=True,
        verbose_name=_("Status"),
        help_text=_("Current status of the activity")
    )
    scheduled_date = models.DateTimeField(
        db_index=True,
        verbose_name=_("Scheduled Date"),
        help_text=_("When the activity is scheduled")
    )
    completed_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Completed Date"),
        help_text=_("When the activity was completed")
    )
    completion_notes = models.TextField(
        blank=True,
        verbose_name=_("Completion Notes"),
        help_text=_("Outcome/details of the completed activity")
    )
    duration_minutes = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_("Duration (Minutes)"),
        help_text=_("Duration of the activity in minutes")
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="activities_created",
        verbose_name=_("Created By"),
        help_text=_("User who created the activity")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    
    class Meta:
        verbose_name = _("Activity")
        verbose_name_plural = _("Activities")
        db_table = "activities_activity"
        ordering = ["-scheduled_date"]
        indexes = [
            models.Index(fields=["lead", "status"], name="activity_lead_status_idx"),
            models.Index(fields=["assigned_to", "status"], name="activity_user_status_idx"),
            models.Index(fields=["assigned_to", "scheduled_date"], name="activity_user_date_idx"),
            models.Index(fields=["status"], name="activity_status_idx"),
            models.Index(fields=["activity_type"], name="activity_type_idx"),
            models.Index(fields=["scheduled_date"], name="activity_scheduled_idx"),
        ]
    
    def __str__(self):
        return f"{self.lead.customer_name} - {self.get_activity_type_display()}"


class Note(models.Model):
    """Internal notes and comments on leads."""
    
    NOTE_TYPE_CHOICES = [
        ("INTERNAL", _("Internal")),
        ("CUSTOMER_FACING", _("Customer Facing")),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lead = models.ForeignKey(
        "leads.Lead",
        on_delete=models.CASCADE,
        related_name="notes",
        verbose_name=_("Lead"),
        help_text=_("Associated lead")
    )
    content = models.TextField(
        verbose_name=_("Content"),
        help_text=_("Note content")
    )
    note_type = models.CharField(
        max_length=20,
        choices=NOTE_TYPE_CHOICES,
        default="INTERNAL",
        db_index=True,
        verbose_name=_("Note Type"),
        help_text=_("Type of note")
    )
    is_internal = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_("Is Internal"),
        help_text=_("Whether this note is for internal use only")
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="notes_created",
        verbose_name=_("Created By"),
        help_text=_("User who created the note")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    
    class Meta:
        verbose_name = _("Note")
        verbose_name_plural = _("Notes")
        db_table = "activities_note"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["lead"], name="note_lead_idx"),
            models.Index(fields=["note_type"], name="note_type_idx"),
            models.Index(fields=["created_at"], name="note_created_idx"),
        ]
    
    def __str__(self):
        return f"Note on {self.lead.customer_name} - {self.note_type}"


class FollowUp(models.Model):
    """Follow-up reminders and scheduling."""
    
    PRIORITY_CHOICES = [
        ("HIGH", _("High")),
        ("MEDIUM", _("Medium")),
        ("LOW", _("Low")),
    ]
    
    STATUS_CHOICES = [
        ("PENDING", _("Pending")),
        ("SCHEDULED", _("Scheduled")),
        ("COMPLETED", _("Completed")),
        ("CANCELLED", _("Cancelled")),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lead = models.ForeignKey(
        "leads.Lead",
        on_delete=models.CASCADE,
        related_name="followups",
        verbose_name=_("Lead"),
        help_text=_("Associated lead")
    )
    assigned_to = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="followups",
        verbose_name=_("Assigned To"),
        help_text=_("User responsible for follow-up")
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default="MEDIUM",
        db_index=True,
        verbose_name=_("Priority"),
        help_text=_("Priority level of the follow-up")
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
        db_index=True,
        verbose_name=_("Status"),
        help_text=_("Current status of the follow-up")
    )
    scheduled_for = models.DateField(
        db_index=True,
        verbose_name=_("Scheduled For"),
        help_text=_("Scheduled date for the follow-up")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Details about what needs to be followed up")
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Completed At"),
        help_text=_("When the follow-up was completed")
    )
    completion_remarks = models.TextField(
        blank=True,
        verbose_name=_("Completion Remarks"),
        help_text=_("Remarks on completion")
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="followups_created",
        verbose_name=_("Created By"),
        help_text=_("User who created the follow-up")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    
    class Meta:
        verbose_name = _("Follow-up")
        verbose_name_plural = _("Follow-ups")
        db_table = "activities_followup"
        ordering = ["scheduled_for"]
        indexes = [
            models.Index(fields=["lead", "status"], name="followup_lead_status_idx"),
            models.Index(fields=["assigned_to", "status"], name="followup_user_status_idx"),
            models.Index(fields=["assigned_to", "scheduled_for"], name="followup_user_date_idx"),
            models.Index(fields=["status"], name="followup_status_idx"),
            models.Index(fields=["priority"], name="followup_priority_idx"),
        ]
    
    def __str__(self):
        return f"Follow-up: {self.lead.customer_name} ({self.status})"
