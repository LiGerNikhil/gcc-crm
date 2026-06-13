from rest_framework import serializers
from .models import ImageUpload, ImageBatch


class ImageUploadListSerializer(serializers.ModelSerializer):
    image_type_display = serializers.CharField(source="get_image_type_display", read_only=True)
    image_format_display = serializers.CharField(source="get_image_format_display", read_only=True)
    uploaded_by_name = serializers.SerializerMethodField()
    lead_info = serializers.SerializerMethodField()
    batch_name = serializers.SerializerMethodField()

    class Meta:
        model = ImageUpload
        fields = [
            "id", "file_name", "file_path", "thumbnail_path",
            "image_type", "image_type_display", "image_format",
            "image_format_display", "file_size", "width", "height",
            "uploaded_by_name", "lead_info", "batch_name", "created_at",
        ]
        read_only_fields = fields

    def get_uploaded_by_name(self, obj):
        if obj.uploaded_by:
            return obj.uploaded_by.get_full_name() or obj.uploaded_by.username
        return None

    def get_lead_info(self, obj):
        if obj.lead:
            return {"id": str(obj.lead.id), "name": obj.lead.customer_name, "lead_number": obj.lead.lead_number}
        return None

    def get_batch_name(self, obj):
        if obj.batch:
            return obj.batch.name
        return None


class ImageUploadDetailSerializer(serializers.ModelSerializer):
    image_type_display = serializers.CharField(source="get_image_type_display", read_only=True)
    image_format_display = serializers.CharField(source="get_image_format_display", read_only=True)
    uploaded_by_name = serializers.SerializerMethodField()
    lead_info = serializers.SerializerMethodField()
    batch_info = serializers.SerializerMethodField()

    class Meta:
        model = ImageUpload
        fields = "__all__"
        read_only_fields = [f.name for f in ImageUpload._meta.fields]

    def get_uploaded_by_name(self, obj):
        if obj.uploaded_by:
            return obj.uploaded_by.get_full_name() or obj.uploaded_by.username
        return None

    def get_lead_info(self, obj):
        if obj.lead:
            return {"id": str(obj.lead.id), "name": obj.lead.customer_name, "lead_number": obj.lead.lead_number}
        return None

    def get_batch_info(self, obj):
        if obj.batch:
            return {"id": str(obj.batch.id), "name": obj.batch.name, "status": obj.batch.status}
        return None


class ImageBatchListSerializer(serializers.ModelSerializer):
    campaign_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = ImageBatch
        fields = [
            "id", "name", "description", "campaign_name", "status",
            "status_display", "total_images", "linked_leads",
            "created_by_name", "created_at",
        ]
        read_only_fields = fields

    def get_campaign_name(self, obj):
        return obj.campaign.name if obj.campaign else None

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None


class ImageBatchDetailSerializer(serializers.ModelSerializer):
    campaign_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    images = ImageUploadListSerializer(many=True, read_only=True)

    class Meta:
        model = ImageBatch
        fields = "__all__"
        read_only_fields = [f.name for f in ImageBatch._meta.fields]

    def get_campaign_name(self, obj):
        return obj.campaign.name if obj.campaign else None

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None


class ImageUploadSerializer(serializers.Serializer):
    files = serializers.ListField(child=serializers.FileField())
    campaign_id = serializers.UUIDField(required=False)
    batch_name = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)


class ImageBulkAssignSerializer(serializers.Serializer):
    image_ids = serializers.ListField(child=serializers.UUIDField())
    lead_id = serializers.UUIDField()
