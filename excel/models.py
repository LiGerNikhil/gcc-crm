import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _


class ExcelImport(models.Model):
    """Excel file import session tracking."""
    
    STATUS_CHOICES = [
        ("PENDING", _("Pending")),
        ("PROCESSING", _("Processing")),
        ("COMPLETED", _("Completed")),
        ("FAILED", _("Failed")),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.OneToOneField(
        "leads.Batch",
        on_delete=models.CASCADE,
        related_name="excel_import",
        verbose_name=_("Batch"),
        help_text=_("Associated batch")
    )
    file_path = models.CharField(
        max_length=500,
        verbose_name=_("File Path"),
        help_text=_("Path to the uploaded Excel file")
    )
    file_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("File Name"),
        help_text=_("Original file name")
    )
    file_size = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_("File Size"),
        help_text=_("File size in bytes")
    )
    imported_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Imported At"),
        help_text=_("When file was uploaded")
    )
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Processed At"),
        help_text=_("When file was processed")
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
        db_index=True,
        verbose_name=_("Status"),
        help_text=_("Current import status")
    )
    total_rows = models.IntegerField(
        default=0,
        verbose_name=_("Total Rows"),
        help_text=_("Total rows in the Excel file")
    )
    successful_rows = models.IntegerField(
        default=0,
        verbose_name=_("Successful Rows"),
        help_text=_("Number of successfully imported rows")
    )
    failed_rows = models.IntegerField(
        default=0,
        verbose_name=_("Failed Rows"),
        help_text=_("Number of rows that failed")
    )
    error_log = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Error Log'),
        help_text=_('Detailed error messages in JSON format. Use JSONField with PostgreSQL.')
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="excel_imports",
        verbose_name=_("Created By"),
        help_text=_("User who initiated the import")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    
    class Meta:
        verbose_name = _("Excel Import")
        verbose_name_plural = _("Excel Imports")
        db_table = "excel_import"
        ordering = ["-imported_at"]
        indexes = [
            models.Index(fields=["status"], name="excel_status_idx"),
            models.Index(fields=["created_by"], name="excel_created_by_idx"),
        ]
    
    def __str__(self):
        return f"Excel Import - {self.batch.batch_number}"


class ExcelImportLog(models.Model):
    """Line-by-line import log for debugging."""
    
    STATUS_CHOICES = [
        ("SUCCESS", _("Success")),
        ("FAILED", _("Failed")),
        ("SKIPPED", _("Skipped")),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    excel_import = models.ForeignKey(
        ExcelImport,
        on_delete=models.CASCADE,
        related_name="logs",
        verbose_name=_("Excel Import"),
        help_text=_("Associated Excel import session")
    )
    row_number = models.IntegerField(
        verbose_name=_("Row Number"),
        help_text=_("Row number in the Excel file")
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        db_index=True,
        verbose_name=_("Status"),
        help_text=_("Import status for this row")
    )
    error_message = models.TextField(
        blank=True,
        verbose_name=_("Error Message"),
        help_text=_("Error details if import failed")
    )
    raw_data = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Raw Data'),
        help_text=_('Raw data from the Excel row (JSON format). Use JSONField with PostgreSQL.')
    )
    created_lead_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Created Lead ID"),
        help_text=_("ID of created lead (if successful)")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    
    class Meta:
        verbose_name = _("Excel Import Log")
        verbose_name_plural = _("Excel Import Logs")
        db_table = "excel_import_log"
        ordering = ["row_number"]
        indexes = [
            models.Index(fields=["excel_import", "status"], name="excel_log_import_status_idx"),
            models.Index(fields=["row_number"], name="excel_log_row_idx"),
        ]
    
    def __str__(self):
        return f"Row {self.row_number} - {self.get_status_display()}"
