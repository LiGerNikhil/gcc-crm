from django.contrib import admin
from .models import AuditLog, UserActionLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "action", "model_name", "record_id", "user", "description")
    list_filter = ("action", "model_name")
    search_fields = ("description", "model_name", "record_id", "user__username")
    readonly_fields = ("id", "timestamp", "old_values", "new_values")
    date_hierarchy = "timestamp"


@admin.register(UserActionLog)
class UserActionLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "user", "action_type", "resource_type", "status")
    list_filter = ("action_type", "status")
    search_fields = ("user__username", "resource_type")
    readonly_fields = ("id", "timestamp")
    date_hierarchy = "timestamp"
