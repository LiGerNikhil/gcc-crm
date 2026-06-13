import uuid
from datetime import date
from django.db import models
from django.utils.translation import gettext_lazy as _


def WORK_ITEM_FILE_PATH(instance, filename):
    """Upload path for revert attachments."""
    wi = instance.work_item
    batch_id = wi.batch_id if wi else "unknown"
    return f"documents/revert_attachments/{batch_id}/{wi.id}/{filename}"


class UploadBatch(models.Model):
    """A batch of uploaded documents from any source (Excel, PDF, Image).

    Batch naming convention: {SOURCE_CODE}-{MONTH}-{SEQ}
    Example: HDFC-JUNE-001
    """

    UPLOAD_TYPES = [
        ("EXCEL", _("Excel")),
        ("PDF", _("PDF")),
        ("IMAGE", _("Image")),
    ]

    BATCH_STATUS = [
        ("DRAFT", _("Draft")),
        ("PENDING", _("Pending")),
        ("PROCESSING", _("Processing")),
        ("COMPLETED", _("Completed")),
        ("PARTIAL", _("Partially Completed")),
        ("FAILED", _("Failed")),
        ("CANCELLED", _("Cancelled")),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # ── Batch Identity ──────────────────────────────────────────
    batch_code = models.CharField(
        max_length=50, unique=True, db_index=True,
        verbose_name=_("Batch Code"),
        help_text=_("Auto-generated batch code (e.g. HDFC-JUNE-001)"),
    )
    bank_source = models.ForeignKey(
        "leads.BankSource", on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="upload_batches",
        verbose_name=_("Source Name"),
        help_text=_("Bank or financial institution this data belongs to"),
    )
    upload_type = models.CharField(
        max_length=10, choices=UPLOAD_TYPES, db_index=True,
        verbose_name=_("Upload Type"),
        help_text=_("Format of the uploaded file"),
    )
    status = models.CharField(
        max_length=20, choices=BATCH_STATUS, default="DRAFT", db_index=True,
        verbose_name=_("Batch Status"),
    )

    # ── File Info ────────────────────────────────────────────────
    original_filename = models.CharField(
        max_length=500, blank=True,
        verbose_name=_("Original Filename"),
    )
    file_path = models.CharField(
        max_length=1000, blank=True,
        verbose_name=_("File Path"),
    )
    file_size = models.BigIntegerField(
        null=True, blank=True,
        verbose_name=_("File Size"),
        help_text=_("File size in bytes"),
    )

    # ── Record Counts ────────────────────────────────────────────
    total_records = models.IntegerField(
        default=0, verbose_name=_("Total Records"),
        help_text=_("Number of records in the uploaded file"),
    )
    processed_records = models.IntegerField(
        default=0, verbose_name=_("Processed Records"),
        help_text=_("Number of records that have been processed"),
    )
    failed_records = models.IntegerField(
        default=0, verbose_name=_("Failed Records"),
        help_text=_("Number of records that failed processing"),
    )

    # ── Ownership & Dates ────────────────────────────────────────
    uploaded_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT,
        related_name="upload_batches",
        verbose_name=_("Uploaded By"),
    )
    upload_date = models.DateTimeField(
        auto_now_add=True, verbose_name=_("Upload Date"),
    )
    processed_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Processed At"),
    )

    # ── Notes & Errors ───────────────────────────────────────────
    notes = models.TextField(
        blank=True, verbose_name=_("Notes"),
        help_text=_("Internal notes about this upload"),
    )
    error_log = models.TextField(
        blank=True, verbose_name=_("Error Log"),
    )
    metadata = models.TextField(
        blank=True, verbose_name=_("Metadata"),
        help_text=_("Additional metadata as JSON"),
    )

    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Upload Batch")
        verbose_name_plural = _("Upload Batches")
        db_table = "documents_upload_batch"
        ordering = ["-upload_date"]
        indexes = [
            models.Index(fields=["batch_code"], name="doc_batch_code_idx"),
            models.Index(fields=["bank_source"], name="doc_batch_source_idx"),
            models.Index(fields=["upload_type"], name="doc_batch_type_idx"),
            models.Index(fields=["status"], name="doc_batch_status_idx"),
            models.Index(fields=["uploaded_by"], name="doc_batch_uploader_idx"),
            models.Index(fields=["upload_date"], name="doc_batch_date_idx"),
        ]

    def __str__(self):
        return f"{self.batch_code} [{self.get_upload_type_display()}] - {self.get_status_display()}"

    @classmethod
    def generate_batch_code(cls, bank_source_code):
        """Generate a batch code like HDFC-JUNE-001.

        Pattern: {SOURCE_CODE}-{MONTH}-{3-digit sequence}
        Sequence resets per source per month.
        """
        month = date.today().strftime("%b").upper()
        prefix = f"{bank_source_code}-{month}-"
        last = cls.objects.filter(batch_code__startswith=prefix).order_by("batch_code").last()
        if last:
            seq = int(last.batch_code.split("-")[-1]) + 1
        else:
            seq = 1
        return f"{prefix}{seq:03d}"

    def save(self, *args, **kwargs):
        if not self.batch_code:
            if self.bank_source:
                source_code = self.bank_source.source_code
            else:
                source_code = self.upload_type or "GEN"
            self.batch_code = self.generate_batch_code(source_code)
        super().save(*args, **kwargs)


class WorkItem(models.Model):
    """Individual unit of work extracted from an upload batch."""

    PRIORITY_CHOICES = [
        ("HIGH", _("High")),
        ("MEDIUM", _("Medium")),
        ("LOW", _("Low")),
    ]

    ITEM_STATUS = [
        ("NEW", _("New")),
        ("ASSIGNED", _("Assigned")),
        ("IN_PROGRESS", _("In Progress")),
        ("PENDING", _("Pending")),
        ("NEED_CLARIFICATION", _("Need Clarification")),
        ("COMPLETED", _("Completed")),
        ("REJECTED", _("Rejected")),
        ("CLOSED", _("Closed")),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(
        UploadBatch, on_delete=models.CASCADE,
        related_name="work_items", verbose_name=_("Upload Batch"),
    )

    # Identity within the batch
    item_identifier = models.CharField(
        max_length=100, blank=True,
        verbose_name=_("Item Identifier"),
        help_text=_("Row number, page number, or image index within the batch"),
    )
    sequence = models.IntegerField(
        default=0, verbose_name=_("Sequence"),
        help_text=_("Display order within the batch"),
    )

    # Status tracking
    status = models.CharField(
        max_length=20, choices=ITEM_STATUS, default="NEW", db_index=True,
        verbose_name=_("Work Item Status"),
    )
    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, default="MEDIUM",
        verbose_name=_("Priority"),
    )

    # Current assignment (denormalized for fast queries; full history in WorkAssignment)
    assigned_to = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="assigned_work_items",
        verbose_name=_("Assigned To"),
    )
    assigned_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Assigned At"),
    )

    # Link to the resulting Lead
    lead = models.ForeignKey(
        "leads.Lead", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="source_work_items",
        verbose_name=_("Linked Lead"),
        help_text=_("The lead record created from this work item"),
    )

    # PDF-specific fields (for PDF upload source)
    page_number = models.IntegerField(
        null=True, blank=True, verbose_name=_("Page Number"),
        help_text=_("Page number in the source PDF (1-indexed)"),
    )
    page_preview = models.CharField(
        max_length=1000, blank=True,
        verbose_name=_("Page Preview"),
        help_text=_("Path to the rendered page preview image"),
    )
    page_thumbnail = models.CharField(
        max_length=1000, blank=True,
        verbose_name=_("Page Thumbnail"),
        help_text=_("Path to the page thumbnail image"),
    )

    # Image-specific fields (for image upload source)
    image_original = models.CharField(
        max_length=1000, blank=True,
        verbose_name=_("Original Image"),
        help_text=_("Path to the original uploaded image"),
    )
    image_preview = models.CharField(
        max_length=1000, blank=True,
        verbose_name=_("Image Preview"),
        help_text=_("Path to the resized preview image"),
    )
    image_thumbnail = models.CharField(
        max_length=1000, blank=True,
        verbose_name=_("Image Thumbnail"),
        help_text=_("Path to the image thumbnail"),
    )

    # Extracted and result data as JSON (stored in TextField for SQLite compatibility)
    extracted_data = models.TextField(
        blank=True, verbose_name=_("Extracted Data"),
        help_text=_("Raw extracted data from the source document as JSON"),
    )
    result_data = models.TextField(
        blank=True, verbose_name=_("Result Data"),
        help_text=_("Processed/corrected data after review as JSON"),
    )
    internal_notes = models.TextField(
        blank=True, verbose_name=_("Internal Notes"),
    )
    error_message = models.TextField(
        blank=True, verbose_name=_("Error Message"),
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    completed_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Completed At"),
    )

    class Meta:
        verbose_name = _("Work Item")
        verbose_name_plural = _("Work Items")
        db_table = "documents_work_item"
        ordering = ["batch", "sequence"]
        indexes = [
            models.Index(fields=["batch", "status"], name="doc_wi_batch_status_idx"),
            models.Index(fields=["status"], name="doc_wi_status_idx"),
            models.Index(fields=["assigned_to"], name="doc_wi_assigned_idx"),
            models.Index(fields=["batch", "sequence"], name="doc_wi_batch_seq_idx"),
        ]

    def __str__(self):
        label = self.item_identifier or str(self.id)
        if self.page_number:
            label += f" (p.{self.page_number})"
        return f"WorkItem {label} [{self.get_status_display()}]"


class WorkItemStatus(models.Model):
    """Immutable audit log of every status change on a work item."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    work_item = models.ForeignKey(
        WorkItem, on_delete=models.CASCADE,
        related_name="status_history", verbose_name=_("Work Item"),
    )
    status = models.CharField(
        max_length=20, choices=WorkItem.ITEM_STATUS,
        verbose_name=_("Status"),
    )
    changed_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="work_item_status_changes",
        verbose_name=_("Changed By"),
    )
    changed_at = models.DateTimeField(
        db_index=True, verbose_name=_("Changed At"),
    )
    from_status = models.CharField(
        max_length=20, blank=True,
        verbose_name=_("From Status"),
        help_text=_("Previous status (blank for initial)"),
    )
    notes = models.TextField(
        blank=True, verbose_name=_("Notes"),
        help_text=_("Reason or context for this status change"),
    )
    is_system = models.BooleanField(
        default=False, verbose_name=_("System Change"),
        help_text=_("True if this change was made automatically by the system"),
    )

    class Meta:
        verbose_name = _("Work Item Status Entry")
        verbose_name_plural = _("Work Item Status History")
        db_table = "documents_work_item_status"
        ordering = ["-changed_at"]
        indexes = [
            models.Index(fields=["work_item", "changed_at"], name="doc_wis_wi_ts_idx"),
            models.Index(fields=["status"], name="doc_wis_status_idx"),
            models.Index(fields=["changed_by"], name="doc_wis_user_idx"),
        ]

    def __str__(self):
        return f"[{self.changed_at}] {self.from_status or '—'} → {self.status} on {self.work_item}"


class WorkAssignment(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    work_item = models.ForeignKey(
        WorkItem, on_delete=models.CASCADE,
        related_name="assignments", verbose_name=_("Work Item"),
    )
    assigned_to = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="work_assignments",
        verbose_name=_("Assigned To"),
    )
    assigned_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="work_assignments_made",
        verbose_name=_("Assigned By"),
    )
    assigned_at = models.DateTimeField(
        auto_now_add=True, verbose_name=_("Assigned At"),
    )
    unassigned_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Unassigned At"),
    )
    notes = models.TextField(
        blank=True, verbose_name=_("Assignment Notes"),
        help_text=_("Reason for this assignment"),
    )

    class Meta:
        verbose_name = _("Work Assignment")
        verbose_name_plural = _("Work Assignments")
        db_table = "documents_work_assignment"
        ordering = ["-assigned_at"]
        indexes = [
            models.Index(fields=["work_item"], name="doc_assign_wi_idx"),
            models.Index(fields=["assigned_to"], name="doc_assign_user_idx"),
        ]

    def __str__(self):
        return f"Assignment: {self.assigned_to} -> {self.work_item}"


class WorkNote(models.Model):
    """Notes attached to a work item."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    work_item = models.ForeignKey(
        WorkItem, on_delete=models.CASCADE,
        related_name="notes", verbose_name=_("Work Item"),
    )
    content = models.TextField(verbose_name=_("Note Text"))
    is_feedback = models.BooleanField(
        default=False, verbose_name=_("Feedback"),
        help_text=_("Mark as feedback visible to managers and team leads"),
    )
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="work_notes",
        verbose_name=_("Author"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Date"))

    class Meta:
        verbose_name = _("Work Note")
        verbose_name_plural = _("Work Notes")
        db_table = "documents_work_note"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["work_item"], name="doc_note_wi_idx"),
            models.Index(fields=["created_by"], name="doc_note_user_idx"),
        ]

    def __str__(self):
        return f"Note on {self.work_item} by {self.created_by}"


class WorkRevert(models.Model):
    """Records a revert/undo operation on a work item's status or data."""

    REVERT_REASONS = [
        ("DUPLICATE", _("Duplicate Entry")),
        ("INCORRECT_DATA", _("Incorrect Data")),
        ("USER_ERROR", _("User Error")),
        ("SYSTEM_ERROR", _("System Error")),
        ("CLIENT_REQUEST", _("Client Request")),
        ("QUALITY_REJECT", _("Quality Reject")),
        ("DOCUMENT_INCOMPLETE", _("Document Incomplete")),
        ("NEED_BETTER_IMAGE", _("Need Better Image")),
        ("VERIFIED", _("Verified")),
        ("OTHER", _("Other")),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    work_item = models.ForeignKey(
        WorkItem, on_delete=models.CASCADE,
        related_name="reverts", verbose_name=_("Work Item"),
    )
    reason = models.CharField(
        max_length=30, choices=REVERT_REASONS, default="OTHER",
        verbose_name=_("Revert Reason"),
    )
    reason_details = models.TextField(
        blank=True, verbose_name=_("Reason Details"),
    )
    remarks = models.TextField(
        blank=True, verbose_name=_("Remarks"),
        help_text=_("Additional remarks about this revert"),
    )
    attachment = models.FileField(
        upload_to=WORK_ITEM_FILE_PATH,
        blank=True, null=True,
        verbose_name=_("Attachment"),
        help_text=_("Optional supporting file (image, PDF, document)"),
    )

    # Snapshot of before/after state
    previous_status = models.CharField(
        max_length=20, blank=True,
        verbose_name=_("Previous Status"),
        help_text=_("Status before the revert"),
    )
    restored_status = models.CharField(
        max_length=20, blank=True,
        verbose_name=_("Restored Status"),
        help_text=_("Status restored to after the revert"),
    )
    changed_fields = models.TextField(
        blank=True, verbose_name=_("Changed Fields"),
        help_text=_("JSON object describing which fields were reverted and their old/new values"),
    )

    reverted_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="work_reverts",
        verbose_name=_("Reverted By"),
    )
    reverted_at = models.DateTimeField(
        auto_now_add=True, verbose_name=_("Reverted At"),
    )

    class Meta:
        verbose_name = _("Work Revert")
        verbose_name_plural = _("Work Reverts")
        db_table = "documents_work_revert"
        ordering = ["-reverted_at"]
        indexes = [
            models.Index(fields=["work_item"], name="doc_revert_wi_idx"),
            models.Index(fields=["reverted_by"], name="doc_revert_user_idx"),
        ]

    def __str__(self):
        return f"Revert on {self.work_item} - {self.get_reason_display()}"


class WorkTimeline(models.Model):
    """Activity timeline entry for a work item."""

    ACTION_TYPES = [
        ("CREATED", _("Item Created")),
        ("ASSIGNED", _("Assigned")),
        ("UNASSIGNED", _("Unassigned")),
        ("REASSIGNED", _("Reassigned")),
        ("STATUS_CHANGED", _("Status Changed")),
        ("NOTE_ADDED", _("Note Added")),
        ("DATA_UPDATED", _("Data Updated")),
        ("REVERTED", _("Reverted")),
        ("COMPLETED", _("Completed")),
        ("REOPENED", _("Reopened")),
        ("REJECTED", _("Rejected")),
        ("CLOSED", _("Closed")),
        ("NEED_CLARIFICATION", _("Need Clarification")),
        ("PENDING", _("Pending")),
        ("ERROR", _("Error")),
        ("COMMENT", _("Comment")),
        ("FEEDBACK", _("Feedback")),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    work_item = models.ForeignKey(
        WorkItem, on_delete=models.CASCADE,
        related_name="timeline_entries", verbose_name=_("Work Item"),
    )
    action = models.CharField(
        max_length=20, choices=ACTION_TYPES, db_index=True,
        verbose_name=_("Action"),
    )
    description = models.TextField(
        blank=True, verbose_name=_("Description"),
        help_text=_("Human-readable description of what happened"),
    )

    # Before/after state for status changes
    from_status = models.CharField(
        max_length=20, blank=True, verbose_name=_("From Status"),
    )
    to_status = models.CharField(
        max_length=20, blank=True, verbose_name=_("To Status"),
    )

    performed_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="work_timeline_entries",
        verbose_name=_("Performed By"),
    )

    metadata = models.TextField(
        blank=True, verbose_name=_("Metadata"),
        help_text=_("Additional context as JSON"),
    )
    is_system_generated = models.BooleanField(
        default=False, verbose_name=_("System Generated"),
    )

    timestamp = models.DateTimeField(
        db_index=True, verbose_name=_("Timestamp"),
        help_text=_("When this activity occurred"),
    )

    class Meta:
        verbose_name = _("Work Timeline Entry")
        verbose_name_plural = _("Work Timeline Entries")
        db_table = "documents_work_timeline"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["work_item", "timestamp"], name="doc_tl_wi_ts_idx"),
            models.Index(fields=["action"], name="doc_tl_action_idx"),
            models.Index(fields=["performed_by"], name="doc_tl_user_idx"),
        ]

    def __str__(self):
        return f"[{self.timestamp}] {self.get_action_display()} on {self.work_item}"
