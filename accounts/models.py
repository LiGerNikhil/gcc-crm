import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """Extended Django User model with UUID primary key and additional fields."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(
        _("username"),
        max_length=150,
        unique=True,
        help_text=_("Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."),
        validators=[],  # Use Django's validators
        error_messages={
            "unique": _("A user with that username already exists."),
        },
    )
    email = models.EmailField(
        _("email address"),
        unique=True,
        db_index=True,
        help_text=_("Email must be unique within the system.")
    )
    phone = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        db_index=True,
        verbose_name=_("Phone Number")
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_("Designates whether this user should be treated as active. Unselect this instead of deleting accounts.")
    )
    last_activity_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Last Activity At"),
        help_text=_("Track when user last performed an action.")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    
    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        db_table = "auth_user_extended"
        indexes = [
            models.Index(fields=["email"], name="user_email_idx"),
            models.Index(fields=["username"], name="user_username_idx"),
            models.Index(fields=["is_active"], name="user_is_active_idx"),
            models.Index(fields=["-created_at"], name="user_created_at_idx"),
        ]
    
    def __str__(self):
        return f"{self.get_full_name() or self.username}"


class Role(models.Model):
    """Role system for RBAC."""
    
    ROLE_CHOICES = [
        ("SUPER_ADMIN", _("Super Admin")),
        ("MANAGER", _("Manager")),
        ("TEAM_LEAD", _("Team Lead")),
        ("ARO", _("ARO (Agent)")),
        ("CALLER", _("Caller")),
        ("DATA_ENTRY", _("Data Entry Operator")),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role_code = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        unique=True,
        db_index=True,
        verbose_name=_("Role Code")
    )
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("Role Name"),
        help_text=_("Human-readable role name")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Detailed description of the role and its responsibilities")
    )
    permissions = models.ManyToManyField(
        "Permission",
        blank=True,
        related_name="roles",
        verbose_name=_("Permissions"),
        help_text=_("Select permissions associated with this role")
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_("Is Active")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    
    class Meta:
        verbose_name = _("Role")
        verbose_name_plural = _("Roles")
        db_table = "auth_role"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["role_code"], name="role_code_idx"),
            models.Index(fields=["is_active"], name="role_is_active_idx"),
        ]
    
    def __str__(self):
        return self.name


class Permission(models.Model):
    """Custom permissions for granular access control."""
    
    MODULE_CHOICES = [
        ("LEADS", _("Leads")),
        ("ACTIVITIES", _("Activities")),
        ("REPORTS", _("Reports")),
        ("USERS", _("Users")),
        ("SETTINGS", _("Settings")),
        ("AUDIT", _("Audit")),
        ("IMPORTS", _("Imports")),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name=_("Permission Code"),
        help_text=_("Unique identifier for the permission (e.g., leads.add_lead)")
    )
    name = models.CharField(
        max_length=200,
        verbose_name=_("Permission Name"),
        help_text=_("Human-readable permission name")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description")
    )
    module = models.CharField(
        max_length=20,
        choices=MODULE_CHOICES,
        db_index=True,
        verbose_name=_("Module")
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_("Is Active")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    
    class Meta:
        verbose_name = _("Permission")
        verbose_name_plural = _("Permissions")
        db_table = "auth_permission_custom"
        ordering = ["module", "code"]
        indexes = [
            models.Index(fields=["code"], name="permission_code_idx"),
            models.Index(fields=["module"], name="permission_module_idx"),
        ]
    
    def __str__(self):
        return f"{self.module}: {self.name}"


class UserProfile(models.Model):
    """Extended user profile with CRM-specific information."""
    
    DEPARTMENT_CHOICES = [
        ("SALES", _("Sales")),
        ("OPERATIONS", _("Operations")),
        ("SUPPORT", _("Support")),
        ("MANAGEMENT", _("Management")),
        ("FINANCE", _("Finance")),
        ("ADMIN", _("Administration")),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name=_("User"),
        help_text=_("Associated user account")
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="user_profiles",
        verbose_name=_("Role"),
        help_text=_("User's role in the system")
    )
    department = models.CharField(
        max_length=20,
        choices=DEPARTMENT_CHOICES,
        blank=True,
        verbose_name=_("Department")
    )
    manager = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subordinates",
        verbose_name=_("Manager"),
        help_text=_("Direct manager/supervisor")
    )
    phone = models.CharField(
        max_length=15,
        blank=True,
        db_index=True,
        verbose_name=_("Phone Number")
    )
    profile_image = models.ImageField(
        upload_to="profile_images/",
        blank=True,
        null=True,
        verbose_name=_("Profile Image")
    )
    bio = models.TextField(
        blank=True,
        max_length=500,
        verbose_name=_("Bio")
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_("Is Active"),
        help_text=_("Inactive users cannot log in")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    
    class Meta:
        verbose_name = _("User Profile")
        verbose_name_plural = _("User Profiles")
        db_table = "auth_user_profile"
        indexes = [
            models.Index(fields=["role"], name="userprofile_role_idx"),
            models.Index(fields=["manager"], name="userprofile_manager_idx"),
            models.Index(fields=["is_active"], name="userprofile_is_active_idx"),
        ]
    
    def __str__(self):
        return f"Profile: {self.user.get_full_name() or self.user.username}"
    
    def get_team_members(self):
        """Get all direct subordinates."""
        return UserProfile.objects.filter(manager=self)
    
    def get_manager_chain(self):
        """Get the chain of command up to the top."""
        chain = [self]
        current = self.manager
        while current is not None:
            chain.append(current)
            current = current.manager.manager if hasattr(current, 'manager') else None
        return chain
