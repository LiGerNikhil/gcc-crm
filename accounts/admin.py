from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, Role, Permission, UserProfile


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "username", "email", "get_role", "is_active", "is_staff",
        "date_joined",
    )
    list_filter = ("is_active", "is_staff", "is_superuser")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("-date_joined",)
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "email", "phone")}),
        (_("Permissions"), {
            "fields": (
                "is_active", "is_staff", "is_superuser",
                "groups", "user_permissions",
            ),
        }),
        (_("Important dates"), {"fields": ("last_login", "date_joined", "last_activity_at")}),
    )

    @admin.display(description=_("Role"))
    def get_role(self, obj):
        try:
            return obj.profile.role.name
        except UserProfile.DoesNotExist:
            return "-"


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "role_code", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "role_code", "description")
    filter_horizontal = ("permissions",)


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "module", "is_active")
    list_filter = ("module", "is_active")
    search_fields = ("code", "name", "description")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "department", "manager", "is_active")
    list_filter = ("role", "department", "is_active")
    search_fields = ("user__username", "user__email", "phone")
    raw_id_fields = ("user", "manager")

