from rest_framework import serializers
from .models import PDFImport, PDFPage


class PDFPageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = PDFPage
        fields = "__all__"
        read_only_fields = [f.name for f in PDFPage._meta.fields]

    def get_image_url(self, obj):
        request = self.context.get("request")
        if request and obj.image_path:
            from django.urls import reverse
            return request.build_absolute_uri(
                reverse("pdf:page_image", kwargs={
                    "pk": str(obj.pdf_import_id),
                    "page_number": obj.page_number,
                })
            )
        return obj.image_path

    def get_thumbnail_url(self, obj):
        request = self.context.get("request")
        if request and obj.thumbnail_path:
            from django.urls import reverse
            return request.build_absolute_uri(
                reverse("pdf:page_thumb", kwargs={
                    "pk": str(obj.pdf_import_id),
                    "page_number": obj.page_number,
                })
            )
        return obj.thumbnail_path


class PDFImportListSerializer(serializers.ModelSerializer):
    batch_number = serializers.CharField(source="batch.batch_number", read_only=True)
    campaign_name = serializers.CharField(source="batch.campaign.name", read_only=True)
    created_by_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_extraction_status_display", read_only=True)

    class Meta:
        model = PDFImport
        fields = [
            "id", "batch_number", "campaign_name", "file_name", "file_size",
            "pages_count", "extraction_status", "status_display",
            "created_by_name", "imported_at", "processed_at",
        ]
        read_only_fields = fields

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None


class PDFImportDetailSerializer(serializers.ModelSerializer):
    batch = serializers.SerializerMethodField()
    pages = PDFPageSerializer(many=True, read_only=True)
    created_by_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_extraction_status_display", read_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = PDFImport
        fields = "__all__"
        read_only_fields = [f.name for f in PDFImport._meta.fields]

    def get_batch(self, obj):
        return {
            "id": str(obj.batch.id),
            "batch_number": obj.batch.batch_number,
            "campaign": obj.batch.campaign.name,
        }

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None

    def get_download_url(self, obj):
        request = self.context.get("request")
        if request:
            from django.urls import reverse
            return request.build_absolute_uri(
                reverse("pdf:download", kwargs={"pk": str(obj.id)})
            )
        return None


class PDFUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    campaign_id = serializers.UUIDField()
    notes = serializers.CharField(required=False, allow_blank=True)
