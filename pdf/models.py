import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _


class PDFImport(models.Model):
    """PDF file processing and data extraction."""
    
    EXTRACTION_STATUS_CHOICES = [
        ("PENDING", _("Pending")),
        ("PROCESSING", _("Processing")),
        ("COMPLETED", _("Completed")),
        ("FAILED", _("Failed")),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.OneToOneField(
        "leads.Batch",
        on_delete=models.CASCADE,
        related_name="pdf_import",
        verbose_name=_("Batch"),
        help_text=_("Associated batch")
    )
    file_path = models.CharField(
        max_length=500,
        verbose_name=_("File Path"),
        help_text=_("Path to the uploaded PDF file")
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
    pages_count = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_("Pages Count"),
        help_text=_("Number of pages in PDF")
    )
    imported_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Imported At"),
        help_text=_("When file was uploaded")
    )
    extraction_status = models.CharField(
        max_length=20,
        choices=EXTRACTION_STATUS_CHOICES,
        default="PENDING",
        db_index=True,
        verbose_name=_("Extraction Status"),
        help_text=_("Current extraction status")
    )
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Processed At"),
        help_text=_("When extraction was completed")
    )
    extracted_text = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Extracted Text"),
        help_text=_("Full text extracted from PDF")
    )
    extracted_data = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Extracted Data'),
        help_text=_('Structured data extracted from PDF (JSON format). Use JSONField with PostgreSQL.')
    )
    error_message = models.TextField(
        blank=True,
        verbose_name=_("Error Message"),
        help_text=_("Error details if extraction failed")
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="pdf_imports",
        verbose_name=_("Created By"),
        help_text=_("User who initiated the import")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    
    class Meta:
        verbose_name = _("PDF Import")
        verbose_name_plural = _("PDF Imports")
        db_table = "pdf_import"
        ordering = ["-imported_at"]
        indexes = [
            models.Index(fields=["extraction_status"], name="pdf_status_idx"),
            models.Index(fields=["created_by"], name="pdf_created_by_idx"),
        ]
    
    def __str__(self):
        return f"PDF Import - {self.batch.batch_number}"


class PDFExtractedData(models.Model):
    """Extracted lead data from PDF files."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pdf_import = models.ForeignKey(
        PDFImport,
        on_delete=models.CASCADE,
        related_name="extracted_leads",
        verbose_name=_("PDF Import"),
        help_text=_("Source PDF import")
    )
    page_number = models.IntegerField(
        verbose_name=_("Page Number"),
        help_text=_("Page number in PDF")
    )
    customer_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_("Customer Name"),
        help_text=_("Extracted customer name")
    )
    phone = models.CharField(
        max_length=15,
        blank=True,
        db_index=True,
        verbose_name=_("Phone Number"),
        help_text=_("Extracted phone number")
    )
    email = models.EmailField(
        blank=True,
        verbose_name=_("Email"),
        help_text=_("Extracted email address")
    )
    loan_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Loan Amount"),
        help_text=_("Extracted loan amount")
    )
    confidence_score = models.FloatField(
        default=0.0,
        verbose_name=_("Confidence Score"),
        help_text=_("OCR/extraction confidence (0-1)")
    )
    extracted_fields = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Extracted Fields'),
        help_text=_('All extracted fields in JSON format. Use JSONField with PostgreSQL.')
    )
    is_processed = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=_("Is Processed"),
        help_text=_("Whether this data has been converted to a lead")
    )
    created_lead_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Created Lead ID"),
        help_text=_("ID of created lead (if processed)")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    
    class Meta:
        verbose_name = _("PDF Extracted Data")
        verbose_name_plural = _("PDF Extracted Data")
        db_table = "pdf_extracted_data"
        ordering = ["page_number"]
        indexes = [
            models.Index(fields=["pdf_import", "is_processed"], name="pdf_data_import_processed_idx"),
            models.Index(fields=["phone"], name="pdf_data_phone_idx"),
            models.Index(fields=["is_processed"], name="pdf_data_processed_idx"),
        ]
    
    def __str__(self):
        return f"PDF Page {self.page_number} - {self.customer_name or 'Unknown'}"


class PDFPage(models.Model):
    """Individual PDF page image/preview."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pdf_import = models.ForeignKey(
        PDFImport,
        on_delete=models.CASCADE,
        related_name="pages",
        verbose_name=_("PDF Import"),
    )
    page_number = models.IntegerField(
        verbose_name=_("Page Number"),
    )
    image_path = models.CharField(
        max_length=500,
        verbose_name=_("Image Path"),
        help_text=_("Path to the rendered page image"),
    )
    thumbnail_path = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_("Thumbnail Path"),
        help_text=_("Path to the page thumbnail image"),
    )
    width = models.IntegerField(
        default=0,
        verbose_name=_("Width"),
        help_text=_("Image width in pixels"),
    )
    height = models.IntegerField(
        default=0,
        verbose_name=_("Height"),
        help_text=_("Image height in pixels"),
    )
    file_size = models.IntegerField(
        default=0,
        verbose_name=_("File Size"),
        help_text=_("Image file size in bytes"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    class Meta:
        verbose_name = _("PDF Page")
        verbose_name_plural = _("PDF Pages")
        db_table = "pdf_page"
        ordering = ["page_number"]
        unique_together = [("pdf_import", "page_number")]
        indexes = [
            models.Index(fields=["pdf_import", "page_number"], name="pdf_page_import_num_idx"),
        ]

    def __str__(self):
        return f"Page {self.page_number} of {self.pdf_import.file_name}"
