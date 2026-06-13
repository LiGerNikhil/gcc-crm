from django.contrib import admin
from .models import UploadBatch, WorkItem, WorkAssignment, WorkNote, WorkRevert, WorkTimeline


@admin.register(UploadBatch)
class UploadBatchAdmin(admin.ModelAdmin):
    list_display = ["batch_code", "bank_source", "upload_type", "status", "total_records", "uploaded_by", "upload_date"]
    list_filter = ["status", "upload_type", "bank_source", "upload_date"]
    search_fields = ["batch_code", "bank_source__name", "original_filename"]
    readonly_fields = ["batch_code", "upload_date", "updated_at", "processed_at"]


class WorkAssignmentInline(admin.TabularInline):
    model = WorkAssignment
    extra = 0
    readonly_fields = ["assigned_at", "unassigned_at"]


class WorkNoteInline(admin.TabularInline):
    model = WorkNote
    extra = 0
    readonly_fields = ["created_at"]


class WorkRevertInline(admin.TabularInline):
    model = WorkRevert
    extra = 0
    readonly_fields = ["reverted_at"]
    fields = ["reason", "remarks", "attachment", "reverted_by", "reverted_at"]


class WorkTimelineInline(admin.TabularInline):
    model = WorkTimeline
    extra = 0
    readonly_fields = ["timestamp"]


@admin.register(WorkItem)
class WorkItemAdmin(admin.ModelAdmin):
    list_display = ["item_identifier", "batch", "status", "priority", "assigned_to", "sequence"]
    list_filter = ["status", "priority", "batch"]
    search_fields = ["item_identifier", "internal_notes"]
    inlines = [WorkAssignmentInline, WorkNoteInline, WorkRevertInline, WorkTimelineInline]


@admin.register(WorkAssignment)
class WorkAssignmentAdmin(admin.ModelAdmin):
    list_display = ["work_item", "assigned_to", "assigned_by", "assigned_at", "unassigned_at"]
    list_filter = ["assigned_at"]


@admin.register(WorkNote)
class WorkNoteAdmin(admin.ModelAdmin):
    list_display = ["work_item", "created_by", "created_at"]
    search_fields = ["content"]


@admin.register(WorkRevert)
class WorkRevertAdmin(admin.ModelAdmin):
    list_display = ["work_item", "reason", "remarks", "attachment", "previous_status", "restored_status", "reverted_by", "reverted_at"]
    list_filter = ["reason"]
    search_fields = ["remarks", "reason_details"]


@admin.register(WorkTimeline)
class WorkTimelineAdmin(admin.ModelAdmin):
    list_display = ["work_item", "action", "description", "performed_by", "timestamp"]
    list_filter = ["action", "timestamp"]
    readonly_fields = ["timestamp"]
