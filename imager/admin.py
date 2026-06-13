from django.contrib import admin
from .models import ImageUpload, DocumentImage, ImageBatch


@admin.register(ImageUpload)
class ImageUploadAdmin(admin.ModelAdmin):
    list_display = ["file_name", "image_type", "image_format", "file_size", "lead", "uploaded_by", "created_at"]
    list_filter = ["image_type", "image_format", "created_at"]
    search_fields = ["file_name", "lead__customer_name", "lead__lead_number"]
    raw_id_fields = ["lead", "uploaded_by", "batch"]


@admin.register(DocumentImage)
class DocumentImageAdmin(admin.ModelAdmin):
    list_display = ["lead", "document_type", "document_number", "verification_status", "verified_by", "created_at"]
    list_filter = ["document_type", "verification_status"]
    search_fields = ["lead__customer_name", "document_number"]
    raw_id_fields = ["lead", "image", "verified_by"]


@admin.register(ImageBatch)
class ImageBatchAdmin(admin.ModelAdmin):
    list_display = ["name", "status", "total_images", "linked_leads", "campaign", "created_by", "created_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["name", "campaign__name"]
    raw_id_fields = ["campaign", "created_by"]
