from rest_framework import serializers
from .models import ExcelImport, ExcelImportLog


class ExcelImportLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExcelImportLog
        fields = "__all__"
        read_only_fields = ["id", "excel_import", "created_at"]


class ExcelImportListSerializer(serializers.ModelSerializer):
    batch_number = serializers.CharField(source="batch.batch_number", read_only=True)
    campaign_name = serializers.CharField(source="batch.campaign.name", read_only=True)
    created_by_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = ExcelImport
        fields = [
            "id", "batch_number", "campaign_name", "file_name", "file_size",
            "status", "status_display", "total_rows", "successful_rows",
            "failed_rows", "created_by_name", "imported_at", "processed_at",
        ]
        read_only_fields = fields

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None


class ExcelImportDetailSerializer(serializers.ModelSerializer):
    batch = serializers.SerializerMethodField()
    logs = ExcelImportLogSerializer(many=True, read_only=True)
    created_by_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = ExcelImport
        fields = "__all__"
        read_only_fields = [f.name for f in ExcelImport._meta.fields]

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


class PreviewSerializer(serializers.Serializer):
    columns = serializers.ListField(child=serializers.CharField())
    total_rows = serializers.IntegerField()
    mapping = serializers.DictField()
    missing_required = serializers.ListField(child=serializers.CharField())
    rows = serializers.ListField()


class ExcelUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    campaign_id = serializers.UUIDField()
    batch_name = serializers.CharField(required=False, allow_blank=True)
    sheet_name = serializers.CharField(required=False, default="Sheet1")
    header_row = serializers.IntegerField(required=False, default=1)
    skip_duplicates = serializers.BooleanField(required=False, default=True)
