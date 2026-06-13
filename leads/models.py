import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from decimal import Decimal


class BankSource(models.Model):
    """Master data for bank/lead sources (HDFC, ICICI, Axis, Tata Capital, etc.)"""
    
    SOURCE_CODE_CHOICES = [
        ("HDFC", _("HDFC Bank")),
        ("ICICI", _("ICICI Bank")),
        ("AXIS", _("Axis Bank")),
        ("TATA_CAPITAL", _("Tata Capital")),
        ("OTHER", _("Other Banks")),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=150,
        unique=True,
        db_index=True,
        verbose_name=_("Bank Name"),
        help_text=_("Official name of the bank/financial institution")
    )
    source_code = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        choices=SOURCE_CODE_CHOICES,
        verbose_name=_("Source Code"),
        help_text=_("Unique identifier for the source (HDFC, ICICI, etc.)")
    )
    contact_person = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_("Contact Person"),
        help_text=_("Primary contact person at the bank")
    )
    email = models.EmailField(
        blank=True,
        verbose_name=_("Email"),
        help_text=_("Bank's official email address")
    )
    phone = models.CharField(
        max_length=15,
        blank=True,
        verbose_name=_("Phone Number"),
        help_text=_("Bank's contact phone number")
    )
    address = models.TextField(
        blank=True,
        verbose_name=_("Address"),
        help_text=_("Office address of the bank")
    )
    city = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("City")
    )
    state = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("State")
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_("Is Active"),
        help_text=_("Inactive sources will not be available for lead assignment")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    
    class Meta:
        verbose_name = _("Bank Source")
        verbose_name_plural = _("Bank Sources")
        db_table = "leads_bank_source"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["source_code"], name="bank_source_code_idx"),
            models.Index(fields=["is_active"], name="bank_is_active_idx"),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.source_code})"


class Campaign(models.Model):
    """Marketing campaign associated with a bank source."""
    
    STATUS_CHOICES = [
        ("ACTIVE", _("Active")),
        ("INACTIVE", _("Inactive")),
        ("PAUSED", _("Paused")),
        ("COMPLETED", _("Completed")),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bank_source = models.ForeignKey(
        BankSource,
        on_delete=models.PROTECT,
        related_name="campaigns",
        verbose_name=_("Bank Source"),
        help_text=_("Bank/source associated with this campaign")
    )
    name = models.CharField(
        max_length=200,
        verbose_name=_("Campaign Name"),
        help_text=_("Name of the marketing campaign")
    )
    campaign_code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name=_("Campaign Code"),
        help_text=_("Unique identifier for the campaign")
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="ACTIVE",
        db_index=True,
        verbose_name=_("Status"),
        help_text=_("Current status of the campaign")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Campaign details and objectives")
    )
    start_date = models.DateField(
        db_index=True,
        verbose_name=_("Start Date"),
        help_text=_("Campaign start date")
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("End Date"),
        help_text=_("Campaign end date (if applicable)")
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="campaigns_created",
        verbose_name=_("Created By"),
        help_text=_("User who created the campaign")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    
    class Meta:
        verbose_name = _("Campaign")
        verbose_name_plural = _("Campaigns")
        db_table = "leads_campaign"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["bank_source", "status"], name="campaign_bank_status_idx"),
            models.Index(fields=["campaign_code"], name="campaign_code_idx"),
            models.Index(fields=["status"], name="campaign_status_idx"),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.campaign_code})"


class Batch(models.Model):
    """Batch of leads imported in a single operation."""
    
    IMPORT_STATUS_CHOICES = [
        ("PENDING", _("Pending")),
        ("PROCESSING", _("Processing")),
        ("COMPLETED", _("Completed")),
        ("FAILED", _("Failed")),
        ("PARTIAL", _("Partial")),
    ]
    
    FILE_TYPE_CHOICES = [
        ("EXCEL", _("Excel")),
        ("PDF", _("PDF")),
        ("CSV", _("CSV")),
        ("IMAGE", _("Image")),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.PROTECT,
        related_name="batches",
        verbose_name=_("Campaign"),
        help_text=_("Campaign associated with this batch")
    )
    batch_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name=_("Batch Number"),
        help_text=_("Unique identifier for the batch")
    )
    source_file_path = models.CharField(
        max_length=500,
        verbose_name=_("Source File Path"),
        help_text=_("Path to the uploaded file")
    )
    import_status = models.CharField(
        max_length=20,
        choices=IMPORT_STATUS_CHOICES,
        default="PENDING",
        db_index=True,
        verbose_name=_("Import Status"),
        help_text=_("Current status of the import")
    )
    file_type = models.CharField(
        max_length=20,
        choices=FILE_TYPE_CHOICES,
        verbose_name=_("File Type"),
        help_text=_("Type of file imported")
    )
    total_records = models.IntegerField(
        default=0,
        verbose_name=_("Total Records"),
        help_text=_("Total number of records in the batch")
    )
    processed_records = models.IntegerField(
        default=0,
        verbose_name=_("Processed Records"),
        help_text=_("Number of successfully processed records")
    )
    failed_records = models.IntegerField(
        default=0,
        verbose_name=_("Failed Records"),
        help_text=_("Number of records that failed to import")
    )
    import_date = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name=_("Import Date"),
        help_text=_("Date and time of import")
    )
    processed_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Processed Date"),
        help_text=_("Date and time when import completed")
    )
    uploaded_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="batches_uploaded",
        verbose_name=_("Uploaded By"),
        help_text=_("User who uploaded the batch")
    )
    processed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="batches_processed",
        verbose_name=_("Processed By"),
        help_text=_("User who processed the batch")
    )
    error_log = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Error Log'),
        help_text=_('Details of import errors in JSON format. Use JSONField with PostgreSQL.')
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    
    class Meta:
        verbose_name = _("Batch")
        verbose_name_plural = _("Batches")
        db_table = "leads_batch"
        ordering = ["-import_date"]
        indexes = [
            models.Index(fields=["campaign", "import_status"], name="batch_campaign_status_idx"),
            models.Index(fields=["batch_number"], name="batch_number_idx"),
            models.Index(fields=["import_status"], name="batch_status_idx"),
        ]
    
    def __str__(self):
        return f"Batch {self.batch_number} - {self.import_status}"


class Lead(models.Model):
    """Core lead entity - individual loan lead records."""
    
    LEAD_STATUS_CHOICES = [
        ("NEW", _("New")),
        ("ASSIGNED", _("Assigned")),
        ("IN_PROGRESS", _("In Progress")),
        ("CALLBACK", _("Callback")),
        ("INTERESTED", _("Interested")),
        ("DOCUMENTS_REQUESTED", _("Documents Requested")),
        ("DOCUMENTS_RECEIVED", _("Documents Received")),
        ("BANK_LOGIN", _("Bank Login")),
        ("APPROVED", _("Approved")),
        ("REJECTED", _("Rejected")),
        ("DISBURSED", _("Disbursed")),
    ]
    
    PRIORITY_CHOICES = [
        ("HIGH", _("High")),
        ("MEDIUM", _("Medium")),
        ("LOW", _("Low")),
    ]
    
    LOAN_TYPE_CHOICES = [
        ("HOME", _("Home Loan")),
        ("PERSONAL", _("Personal Loan")),
        ("BUSINESS", _("Business Loan")),
        ("AUTO", _("Auto Loan")),
        ("EDUCATION", _("Education Loan")),
        ("GOLD", _("Gold Loan")),
        ("OTHER", _("Other")),
    ]
    
    EMPLOYMENT_CHOICES = [
        ("SALARIED", _("Salaried")),
        ("SELF_EMPLOYED", _("Self Employed")),
        ("BUSINESS", _("Business")),
        ("AGRICULTURE", _("Agriculture")),
        ("UNEMPLOYED", _("Unemployed")),
        ("RETIRED", _("Retired")),
        ("OTHER", _("Other")),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(
        Batch,
        on_delete=models.PROTECT,
        related_name="leads",
        verbose_name=_("Batch"),
        help_text=_("Batch from which this lead was imported")
    )
    lead_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name=_("Lead Number"),
        help_text=_("Unique identifier for the lead")
    )
    lead_source_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Lead Source ID"),
        help_text=_("External ID from the source system (e.g., HDFC_001_12345)")
    )
    customer_name = models.CharField(
        max_length=200,
        db_index=True,
        verbose_name=_("Customer Name"),
        help_text=_("Full name of the customer")
    )
    phone = models.CharField(
        max_length=15,
        db_index=True,
        verbose_name=_("Phone Number"),
        help_text=_("Primary contact phone number")
    )
    email = models.EmailField(
        blank=True,
        null=True,
        db_index=True,
        verbose_name=_("Email Address"),
        help_text=_("Email address of the customer")
    )
    pan_number = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        db_index=True,
        verbose_name=_("PAN Number"),
        help_text=_("Permanent Account Number (10 digits)")
    )
    loan_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Loan Amount"),
        help_text=_("Requested loan amount in INR")
    )
    loan_type = models.CharField(
        max_length=20,
        choices=LOAN_TYPE_CHOICES,
        blank=True,
        verbose_name=_("Loan Type"),
        help_text=_("Type of loan requested")
    )
    property_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Property Value"),
        help_text=_("Property value (for home loans)")
    )
    employment_type = models.CharField(
        max_length=20,
        choices=EMPLOYMENT_CHOICES,
        blank=True,
        verbose_name=_("Employment Type"),
        help_text=_("Type of employment")
    )
    address = models.TextField(
        verbose_name=_("Address"),
        help_text=_("Full postal address of the customer")
    )
    city = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name=_("City"),
        help_text=_("City of residence")
    )
    state = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name=_("State"),
        help_text=_("State of residence")
    )
    pincode = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_("Pincode"),
        help_text=_("Postal code")
    )
    lead_status = models.CharField(
        max_length=20,
        choices=LEAD_STATUS_CHOICES,
        default="NEW",
        db_index=True,
        verbose_name=_("Lead Status"),
        help_text=_("Current status of the lead in the pipeline")
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default="MEDIUM",
        db_index=True,
        verbose_name=_("Priority"),
        help_text=_("Lead priority level")
    )
    assigned_to = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_leads",
        verbose_name=_("Assigned To"),
        help_text=_("User responsible for this lead")
    )
    assigned_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Assigned At"),
        help_text=_("When the lead was assigned")
    )
    is_duplicate = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=_("Is Duplicate"),
        help_text=_("Whether this lead is marked as duplicate")
    )
    duplicate_of = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="duplicates",
        verbose_name=_("Duplicate Of"),
        help_text=_("Link to the original lead if duplicate")
    )
    notes_summary = models.TextField(
        blank=True,
        verbose_name=_("Notes Summary"),
        help_text=_("Quick summary of notes (auto-updated)")
    )
    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=_("Is Deleted"),
        help_text=_("Soft delete flag")
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Deleted At"),
        help_text=_("When the lead was deleted")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    
    class Meta:
        verbose_name = _("Lead")
        verbose_name_plural = _("Leads")
        db_table = "leads_lead"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["customer_name", "phone"], name="lead_customer_phone_idx"),
            models.Index(fields=["phone"], name="lead_phone_idx"),
            models.Index(fields=["email"], name="lead_email_idx"),
            models.Index(fields=["pan_number"], name="lead_pan_idx"),
            models.Index(fields=["batch", "lead_status"], name="lead_batch_status_idx"),
            models.Index(fields=["assigned_to"], name="lead_assigned_to_idx"),
            models.Index(fields=["is_deleted"], name="lead_is_deleted_idx"),
            models.Index(fields=["lead_status"], name="lead_status_idx"),
            models.Index(fields=["priority"], name="lead_priority_idx"),
        ]
    
    def __str__(self):
        return f"{self.customer_name} ({self.lead_number})"


class AssignmentRule(models.Model):
    """Configuration for auto and round-robin lead distribution."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team_lead = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="assignment_rules",
        verbose_name=_("Team Lead"),
        help_text=_("Team lead who manages this rule"),
    )
    campaign = models.ForeignKey(
        "Campaign",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assignment_rules",
        verbose_name=_("Campaign"),
        help_text=_("Optional: scope rule to a specific campaign"),
    )
    name = models.CharField(
        max_length=200,
        verbose_name=_("Rule Name"),
        help_text=_("Human-readable name for this rule"),
    )
    max_active_leads = models.IntegerField(
        default=50,
        verbose_name=_("Max Active Leads"),
        help_text=_("Maximum active leads per assigned caller"),
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_("Is Active"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Assignment Rule")
        verbose_name_plural = _("Assignment Rules")
        db_table = "leads_assignment_rule"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["team_lead", "is_active"], name="assign_rule_lead_active_idx"),
            models.Index(fields=["campaign"], name="assign_rule_campaign_idx"),
        ]

    def __str__(self):
        return f"{self.name} ({self.team_lead.get_full_name() or self.team_lead.username})"


class RoundRobinCounter(models.Model):
    """Track the current position in round-robin rotation for a rule."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rule = models.ForeignKey(
        AssignmentRule,
        on_delete=models.CASCADE,
        related_name="round_robin_counters",
        verbose_name=_("Rule"),
    )
    caller = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="round_robin_entries",
        verbose_name=_("Caller"),
    )
    current_index = models.IntegerField(
        default=0,
        verbose_name=_("Current Index"),
        help_text=_("Current position in the rotation"),
    )
    assigned_count = models.IntegerField(
        default=0,
        verbose_name=_("Assigned Count"),
        help_text=_("Number of leads assigned in this cycle"),
    )
    last_assigned_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Last Assigned At"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Round Robin Counter")
        verbose_name_plural = _("Round Robin Counters")
        db_table = "leads_round_robin_counter"
        ordering = ["current_index"]
        unique_together = [("rule", "caller")]
        indexes = [
            models.Index(fields=["rule", "current_index"], name="rr_rule_idx_idx"),
        ]

    def __str__(self):
        return f"{self.rule.name} → {self.caller.username} (idx: {self.current_index})"


class LeadAssignment(models.Model):
    """Track lead assignments to users."""
    
    ASSIGNMENT_STATUS_CHOICES = [
        ("ACTIVE", _("Active")),
        ("COMPLETED", _("Completed")),
        ("TRANSFERRED", _("Transferred")),
        ("REJECTED", _("Rejected")),
    ]
    
    ASSIGNMENT_TYPE_CHOICES = [
        ("MANUAL", _("Manual")),
        ("BULK", _("Bulk")),
        ("AUTO_ROUND_ROBIN", _("Auto Round Robin")),
        ("REASSIGNMENT", _("Reassignment")),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name="assignments",
        verbose_name=_("Lead"),
        help_text=_("Lead being assigned")
    )
    assigned_to = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="lead_assignments",
        verbose_name=_("Assigned To"),
        help_text=_("User this lead is assigned to (Caller/Operator)")
    )
    assigned_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="assignments_made",
        verbose_name=_("Assigned By"),
        help_text=_("User who made the assignment (usually Team Lead)")
    )
    assignment_type = models.CharField(
        max_length=20,
        choices=ASSIGNMENT_TYPE_CHOICES,
        default="MANUAL",
        db_index=True,
        verbose_name=_("Assignment Type"),
        help_text=_("How this assignment was made"),
    )
    assignment_status = models.CharField(
        max_length=20,
        choices=ASSIGNMENT_STATUS_CHOICES,
        default="ACTIVE",
        db_index=True,
        verbose_name=_("Assignment Status"),
        help_text=_("Current status of the assignment")
    )
    start_date = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name=_("Start Date"),
        help_text=_("When the assignment started")
    )
    end_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("End Date"),
        help_text=_("When the assignment ended")
    )
    reason_for_transfer = models.TextField(
        blank=True,
        verbose_name=_("Reason for Transfer"),
        help_text=_("Reason if lead was transferred")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    
    class Meta:
        verbose_name = _("Lead Assignment")
        verbose_name_plural = _("Lead Assignments")
        db_table = "leads_assignment"
        ordering = ["-start_date"]
        indexes = [
            models.Index(fields=["lead", "assigned_to"], name="assign_lead_user_idx"),
            models.Index(fields=["assigned_to", "assignment_status"], name="assign_user_status_idx"),
            models.Index(fields=["assignment_status"], name="assign_status_idx"),
            models.Index(fields=["assignment_type"], name="assign_type_idx"),
        ]
    
    def __str__(self):
        return f"{self.lead.customer_name} → {self.assigned_to.username}"


class Outcome(models.Model):
    """Lead outcome/result tracking."""
    
    OUTCOME_TYPE_CHOICES = [
        ("CONVERTED", _("Converted")),
        ("REJECTED", _("Rejected")),
        ("LOST", _("Lost")),
        ("PENDING", _("Pending")),
        ("FOLLOW_UP_REQUIRED", _("Follow-up Required")),
    ]
    
    REJECTION_REASON_CHOICES = [
        ("HIGH_INTEREST", _("High Interest Rates")),
        ("POOR_CIBIL", _("Poor CIBIL Score")),
        ("INSUFFICIENT_INCOME", _("Insufficient Income")),
        ("EXISTING_LOANS", _("Existing Loans")),
        ("DOCUMENTATION", _("Documentation Issues")),
        ("OTHER", _("Other")),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name="outcomes",
        verbose_name=_("Lead"),
        help_text=_("Associated lead")
    )
    outcome_type = models.CharField(
        max_length=20,
        choices=OUTCOME_TYPE_CHOICES,
        db_index=True,
        verbose_name=_("Outcome Type"),
        help_text=_("Type of outcome")
    )
    reason = models.CharField(
        max_length=50,
        choices=REJECTION_REASON_CHOICES,
        blank=True,
        verbose_name=_("Reason"),
        help_text=_("Reason for rejection/loss")
    )
    converted_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Converted Amount"),
        help_text=_("Amount sanctioned (for conversions)")
    )
    conversion_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Conversion Date"),
        help_text=_("Date of conversion")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    
    class Meta:
        verbose_name = _("Outcome")
        verbose_name_plural = _("Outcomes")
        db_table = "leads_outcome"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["lead"], name="outcome_lead_idx"),
            models.Index(fields=["outcome_type"], name="outcome_type_idx"),
        ]
    
    def __str__(self):
        return f"{self.lead.lead_number} - {self.outcome_type}"


class LeadNote(models.Model):
    """Notes associated with a lead."""

    NOTE_TYPE_CHOICES = [
        ("GENERAL", _("General")),
        ("CALL", _("Call Notes")),
        ("MEETING", _("Meeting Notes")),
        ("DOCUMENT", _("Document Note")),
        ("FOLLOW_UP", _("Follow-up Note")),
        ("SYSTEM", _("System Generated")),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name="lead_notes",
        verbose_name=_("Lead"),
    )
    note_type = models.CharField(
        max_length=20,
        choices=NOTE_TYPE_CHOICES,
        default="GENERAL",
        verbose_name=_("Note Type"),
    )
    content = models.TextField(
        verbose_name=_("Content"),
        help_text=_("Note content/description"),
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="lead_notes",
        verbose_name=_("Created By"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Lead Note")
        verbose_name_plural = _("Lead Notes")
        db_table = "leads_lead_note"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["lead", "created_at"], name="lnote_lead_date_idx"),
            models.Index(fields=["note_type"], name="lnote_type_idx"),
        ]

    def __str__(self):
        return f"Note on {self.lead.lead_number} by {self.created_by}"


class FollowUp(models.Model):
    """Scheduled follow-ups/reminders for a lead."""

    FOLLOWUP_STATUS_CHOICES = [
        ("PENDING", _("Pending")),
        ("COMPLETED", _("Completed")),
        ("CANCELLED", _("Cancelled")),
        ("RESCHEDULED", _("Rescheduled")),
    ]

    FOLLOWUP_TYPE_CHOICES = [
        ("CALL", _("Call")),
        ("EMAIL", _("Email")),
        ("MEETING", _("Meeting")),
        ("SITE_VISIT", _("Site Visit")),
        ("DOCUMENT_FOLLOWUP", _("Document Follow-up")),
        ("OTHER", _("Other")),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name="lead_followups",
        verbose_name=_("Lead"),
    )
    followup_type = models.CharField(
        max_length=20,
        choices=FOLLOWUP_TYPE_CHOICES,
        default="CALL",
        verbose_name=_("Follow-up Type"),
    )
    status = models.CharField(
        max_length=20,
        choices=FOLLOWUP_STATUS_CHOICES,
        default="PENDING",
        db_index=True,
        verbose_name=_("Status"),
    )
    scheduled_at = models.DateTimeField(
        verbose_name=_("Scheduled At"),
        help_text=_("When the follow-up is scheduled"),
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Completed At"),
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_("Notes"),
        help_text=_("Notes about the follow-up"),
    )
    assigned_to = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lead_followups_assigned",
        verbose_name=_("Assigned To"),
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="lead_followups_created",
        verbose_name=_("Created By"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Follow-up")
        verbose_name_plural = _("Follow-ups")
        db_table = "leads_follow_up"
        ordering = ["-scheduled_at"]
        indexes = [
            models.Index(fields=["lead", "status"], name="lfup_lead_status_idx"),
            models.Index(fields=["assigned_to", "status"], name="lfup_user_status_idx"),
            models.Index(fields=["scheduled_at"], name="lfup_scheduled_idx"),
        ]

    def __str__(self):
        return f"{self.get_followup_type_display()} for {self.lead.lead_number} on {self.scheduled_at:%Y-%m-%d}"


class LeadCall(models.Model):
    """Phone call record associated with a lead."""

    CALL_TYPE_CHOICES = [
        ("INBOUND", _("Inbound")),
        ("OUTBOUND", _("Outbound")),
        ("MISSED", _("Missed")),
        ("TRANSFERRED", _("Transferred")),
    ]

    CALL_STATUS_CHOICES = [
        ("COMPLETED", _("Completed")),
        ("NO_ANSWER", _("No Answer")),
        ("BUSY", _("Busy")),
        ("FAILED", _("Failed")),
        ("CALLBACK", _("Callback Requested")),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name="calls",
        verbose_name=_("Lead"),
        help_text=_("Associated lead"),
    )
    call_type = models.CharField(
        max_length=20,
        choices=CALL_TYPE_CHOICES,
        db_index=True,
        default="OUTBOUND",
        verbose_name=_("Call Type"),
    )
    call_status = models.CharField(
        max_length=20,
        choices=CALL_STATUS_CHOICES,
        default="COMPLETED",
        verbose_name=_("Call Status"),
    )
    caller = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="lead_calls_made",
        verbose_name=_("Caller"),
        help_text=_("User who made/received the call"),
    )
    duration_seconds = models.IntegerField(
        default=0,
        verbose_name=_("Duration (seconds)"),
        help_text=_("Call duration in seconds"),
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_("Call Notes"),
        help_text=_("Notes about the call conversation"),
    )
    recording_url = models.URLField(
        blank=True,
        verbose_name=_("Recording URL"),
        help_text=_("URL to call recording if available"),
    )
    call_time = models.DateTimeField(
        db_index=True,
        verbose_name=_("Call Time"),
        help_text=_("When the call took place"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Lead Call")
        verbose_name_plural = _("Lead Calls")
        db_table = "leads_lead_call"
        ordering = ["-call_time"]
        indexes = [
            models.Index(fields=["lead", "call_time"], name="lcall_lead_time_idx"),
            models.Index(fields=["caller"], name="lcall_caller_idx"),
            models.Index(fields=["call_type"], name="lcall_type_idx"),
        ]

    def __str__(self):
        return f"{self.get_call_type_display()} call for {self.lead.lead_number} at {self.call_time:%Y-%m-%d %H:%M}"


class LeadStatusLog(models.Model):
    """Audit log for lead status changes."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name="status_logs",
        verbose_name=_("Lead"),
    )
    old_status = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_("Old Status"),
    )
    new_status = models.CharField(
        max_length=20,
        verbose_name=_("New Status"),
    )
    changed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="lead_status_changes",
        verbose_name=_("Changed By"),
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_("Notes"),
        help_text=_("Reason or context for the status change"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    class Meta:
        verbose_name = _("Lead Status Log")
        verbose_name_plural = _("Lead Status Logs")
        db_table = "leads_status_log"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["lead", "created_at"], name="lslog_lead_date_idx"),
            models.Index(fields=["new_status"], name="lslog_new_status_idx"),
        ]

    def __str__(self):
        return f"{self.lead.lead_number}: {self.old_status or 'NEW'} -> {self.new_status}"
