import uuid
import os
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class ImageBatch(models.Model):
    """Group of images uploaded together for batch processing."""

    BATCH_STATUS_CHOICES = [
        ("PENDING", _("Pending")),
        ("PROCESSING", _("Processing")),
        ("COMPLETED", _("Completed")),
        ("PARTIAL", _("Partially Completed")),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=255,
        verbose_name=_("Batch Name"),
        help_text=_("Name for this image batch"),
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Optional description of the batch"),
    )
    campaign = models.ForeignKey(
        "leads.Campaign",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="image_batches",
        verbose_name=_("Campaign"),
    )
    status = models.CharField(
        max_length=20,
        choices=BATCH_STATUS_CHOICES,
        default="PENDING",
        db_index=True,
        verbose_name=_("Status"),
    )
    total_images = models.IntegerField(default=0, verbose_name=_("Total Images"))
    linked_leads = models.IntegerField(default=0, verbose_name=_("Linked Leads"))
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="image_batches_created",
        verbose_name=_("Created By"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Image Batch")
        verbose_name_plural = _("Image Batches")
        db_table = "imager_image_batch"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"], name="img_batch_status_idx"),
            models.Index(fields=["campaign"], name="img_batch_campaign_idx"),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"


class ImageUpload(models.Model):
    """Image file uploads and metadata."""
    
    IMAGE_TYPE_CHOICES = [
        ("ID_PROOF", _("ID Proof")),
        ("ADDRESS_PROOF", _("Address Proof")),
        ("SIGNATURE", _("Signature")),
        ("DOCUMENT", _("Document")),
        ("OTHER", _("Other")),
    ]
    
    IMAGE_FORMAT_CHOICES = [
        ("JPG", _("JPG")),
        ("PNG", _("PNG")),
        ("WEBP", _("WebP")),
        ("GIF", _("GIF")),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(
        ImageBatch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="images",
        verbose_name=_("Batch"),
        help_text=_("Batch this image belongs to"),
    )
    lead = models.ForeignKey(
        "leads.Lead",
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name=_("Lead"),
        help_text=_("Associated lead"),
        null=True,
        blank=True
    )
    file_path = models.CharField(
        max_length=500,
        verbose_name=_("File Path"),
        help_text=_("Path to the uploaded image file")
    )
    file_name = models.CharField(
        max_length=255,
        verbose_name=_("File Name"),
        help_text=_("Original file name")
    )
    image_type = models.CharField(
        max_length=20,
        choices=IMAGE_TYPE_CHOICES,
        verbose_name=_("Image Type"),
        help_text=_("Type of image/document")
    )
    image_format = models.CharField(
        max_length=10,
        choices=IMAGE_FORMAT_CHOICES,
        verbose_name=_("Image Format"),
        help_text=_("Image file format")
    )
    file_size = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_("File Size"),
        help_text=_("File size in bytes")
    )
    width = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_("Width"),
        help_text=_("Image width in pixels")
    )
    height = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_("Height"),
        help_text=_("Image height in pixels")
    )
    thumbnail_path = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_("Thumbnail Path"),
        help_text=_("Path to the generated thumbnail")
    )
    is_compressed = models.BooleanField(
        default=False,
        verbose_name=_("Is Compressed"),
        help_text=_("Whether image has been compressed")
    )
    original_size = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_("Original Size"),
        help_text=_("Original file size before compression")
    )
    uploaded_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="images_uploaded",
        verbose_name=_("Uploaded By"),
        help_text=_("User who uploaded the image")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    
    class Meta:
        verbose_name = _("Image Upload")
        verbose_name_plural = _("Image Uploads")
        db_table = "imager_image_upload"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["lead"], name="image_lead_idx"),
            models.Index(fields=["batch"], name="image_batch_idx"),
            models.Index(fields=["image_type"], name="image_type_idx"),
            models.Index(fields=["created_at"], name="image_created_idx"),
        ]
    
    def __str__(self):
        return f"{self.file_name} ({self.get_image_type_display()})"

    @property
    def extension(self):
        return os.path.splitext(self.file_name)[1].lower().lstrip(".")

    @property
    def is_image(self):
        return self.extension in ("jpg", "jpeg", "png", "webp", "gif", "bmp")


class DocumentImage(models.Model):
    """Structured document image storage linked to leads."""
    
    DOCUMENT_TYPE_CHOICES = [
        ("PAN", _("PAN Card")),
        ("AADHAR", _("Aadhar Card")),
        ("PASSPORT", _("Passport")),
        ("DRIVING_LICENSE", _("Driving License")),
        ("UTILITY_BILL", _("Utility Bill")),
        ("RENT_AGREEMENT", _("Rent Agreement")),
        ("PROPERTY_DOCUMENT", _("Property Document")),
        ("SALARY_SLIP", _("Salary Slip")),
        ("ITR", _("Income Tax Return")),
        ("BANK_STATEMENT", _("Bank Statement")),
        ("OTHER", _("Other")),
    ]
    
    DOCUMENT_STATUS_CHOICES = [
        ("PENDING", _("Pending Verification")),
        ("VERIFIED", _("Verified")),
        ("REJECTED", _("Rejected")),
        ("EXPIRED", _("Expired")),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lead = models.ForeignKey(
        "leads.Lead",
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name=_("Lead"),
        help_text=_("Associated lead")
    )
    image = models.ForeignKey(
        ImageUpload,
        on_delete=models.CASCADE,
        related_name="document_records",
        verbose_name=_("Image"),
        help_text=_("Associated image file")
    )
    document_type = models.CharField(
        max_length=30,
        choices=DOCUMENT_TYPE_CHOICES,
        db_index=True,
        verbose_name=_("Document Type"),
        help_text=_("Type of document")
    )
    document_number = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        verbose_name=_("Document Number"),
        help_text=_("Document/ID number (e.g., PAN, Aadhar, etc.)")
    )
    valid_from = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Valid From"),
        help_text=_("Document validity start date")
    )
    valid_till = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Valid Till"),
        help_text=_("Document expiry date")
    )
    verification_status = models.CharField(
        max_length=20,
        choices=DOCUMENT_STATUS_CHOICES,
        default="PENDING",
        db_index=True,
        verbose_name=_("Verification Status"),
        help_text=_("Current verification status")
    )
    verified_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents_verified",
        verbose_name=_("Verified By"),
        help_text=_("User who verified the document")
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Verified At"),
        help_text=_("When document was verified")
    )
    rejection_reason = models.TextField(
        blank=True,
        verbose_name=_("Rejection Reason"),
        help_text=_("Reason for rejection if rejected")
    )
    remarks = models.TextField(
        blank=True,
        verbose_name=_("Remarks"),
        help_text=_("Additional remarks about the document")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    
    class Meta:
        verbose_name = _("Document Image")
        verbose_name_plural = _("Document Images")
        db_table = "imager_document_image"
        ordering = ["-created_at"]
        unique_together = [("lead", "document_type")]  # One document type per lead
        indexes = [
            models.Index(fields=["lead", "document_type"], name="doc_lead_type_idx"),
            models.Index(fields=["document_number"], name="doc_number_idx"),
            models.Index(fields=["verification_status"], name="doc_verify_status_idx"),
        ]
    
    def __str__(self):
        return f"{self.lead.customer_name} - {self.get_document_type_display()}"
    
    def is_expired(self):
        """Check if document has expired."""
        from django.utils import timezone
        if self.valid_till:
            return self.valid_till < timezone.now().date()
        return False
