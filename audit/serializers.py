from rest_framework import serializers
from .models import AuditLog, UserActionLog


class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id", "user", "user_name", "model_name", "record_id",
            "action", "old_values", "new_values",
            "ip_address", "user_agent", "description", "timestamp",
        ]
        read_only_fields = fields

    def get_user_name(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.username
        return None


class UserActionLogSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = UserActionLog
        fields = [
            "id", "user", "user_name", "action_type",
            "resource_type", "resource_id", "duration_seconds",
            "ip_address", "status", "details", "timestamp",
        ]
        read_only_fields = fields

    def get_user_name(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.username
        return None
