from rest_framework import serializers
from .models import Lead, LeadNote, FollowUp, LeadStatusLog, LeadAssignment, AssignmentRule, RoundRobinCounter, LeadCall


class LeadListSerializer(serializers.ModelSerializer):
    campaign_name = serializers.CharField(source="batch.campaign.name", read_only=True)
    bank_source_name = serializers.CharField(source="batch.campaign.bank_source.name", read_only=True)
    assigned_to_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_lead_status_display", read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)

    class Meta:
        model = Lead
        fields = [
            "id", "lead_number", "customer_name", "phone", "email",
            "loan_type", "loan_amount", "lead_status", "status_display",
            "priority", "priority_display", "city", "assigned_to",
            "assigned_to_name", "campaign_name", "bank_source_name",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "lead_number", "created_at", "updated_at"]

    def get_assigned_to_name(self, obj):
        if obj.assigned_to:
            return obj.assigned_to.get_full_name() or obj.assigned_to.username
        return None


class LeadDetailSerializer(serializers.ModelSerializer):
    campaign = serializers.SerializerMethodField()
    bank_source = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_lead_status_display", read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)
    loan_type_display = serializers.CharField(source="get_loan_type_display", read_only=True)
    employment_type_display = serializers.CharField(source="get_employment_type_display", read_only=True)

    class Meta:
        model = Lead
        fields = "__all__"

    def get_campaign(self, obj):
        return {"id": str(obj.batch.campaign.id), "name": obj.batch.campaign.name}

    def get_bank_source(self, obj):
        return {"id": str(obj.batch.campaign.bank_source.id), "name": obj.batch.campaign.bank_source.name}

    def get_assigned_to_name(self, obj):
        if obj.assigned_to:
            return obj.assigned_to.get_full_name() or obj.assigned_to.username
        return None


class LeadNoteSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = LeadNote
        fields = "__all__"
        read_only_fields = ["id", "lead", "created_by", "created_at", "updated_at"]

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None


class FollowUpSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = FollowUp
        fields = "__all__"
        read_only_fields = ["id", "lead", "created_by", "created_at", "updated_at"]

    def get_assigned_to_name(self, obj):
        if obj.assigned_to:
            return obj.assigned_to.get_full_name() or obj.assigned_to.username
        return None

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None


class LeadStatusLogSerializer(serializers.ModelSerializer):
    changed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = LeadStatusLog
        fields = "__all__"
        read_only_fields = ["id", "lead", "changed_by", "created_at"]

    def get_changed_by_name(self, obj):
        if obj.changed_by:
            return obj.changed_by.get_full_name() or obj.changed_by.username
        return None


class LeadAssignmentSerializer(serializers.ModelSerializer):
    lead_name = serializers.SerializerMethodField()
    lead_number = serializers.CharField(source="lead.lead_number", read_only=True)
    assigned_to_name = serializers.SerializerMethodField()
    assigned_by_name = serializers.SerializerMethodField()
    assignment_type_display = serializers.CharField(source="get_assignment_type_display", read_only=True)
    assignment_status_display = serializers.CharField(source="get_assignment_status_display", read_only=True)

    class Meta:
        model = LeadAssignment
        fields = "__all__"
        read_only_fields = [f.name for f in LeadAssignment._meta.fields]

    def get_lead_name(self, obj):
        return obj.lead.customer_name if obj.lead else None

    def get_assigned_to_name(self, obj):
        if obj.assigned_to:
            return obj.assigned_to.get_full_name() or obj.assigned_to.username
        return None

    def get_assigned_by_name(self, obj):
        if obj.assigned_by:
            return obj.assigned_by.get_full_name() or obj.assigned_by.username
        return None


class AssignmentRuleSerializer(serializers.ModelSerializer):
    campaign_name = serializers.SerializerMethodField()
    team_lead_name = serializers.SerializerMethodField()
    caller_count = serializers.SerializerMethodField()

    class Meta:
        model = AssignmentRule
        fields = [
            "id", "name", "team_lead", "team_lead_name", "campaign",
            "campaign_name", "max_active_leads", "is_active",
            "caller_count", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "team_lead", "created_at", "updated_at"]

    def get_campaign_name(self, obj):
        return obj.campaign.name if obj.campaign else None

    def get_team_lead_name(self, obj):
        return obj.team_lead.get_full_name() or obj.team_lead.username

    def get_caller_count(self, obj):
        return obj.round_robin_counters.count()


class RoundRobinCounterSerializer(serializers.ModelSerializer):
    caller_name = serializers.SerializerMethodField()

    class Meta:
        model = RoundRobinCounter
        fields = "__all__"
        read_only_fields = ["id", "rule", "created_at", "updated_at"]

    def get_caller_name(self, obj):
        return obj.caller.get_full_name() or obj.caller.username


class RoundRobinAssignRequestSerializer(serializers.Serializer):
    lead_ids = serializers.ListField(child=serializers.UUIDField())
    rule_id = serializers.UUIDField()


class BulkAssignRequestSerializer(serializers.Serializer):
    lead_ids = serializers.ListField(child=serializers.UUIDField())
    assigned_to = serializers.UUIDField()


class ReassignRequestSerializer(serializers.Serializer):
    assigned_to = serializers.UUIDField()
    reason = serializers.CharField(required=False, allow_blank=True)


class LeadBulkAssignSerializer(serializers.Serializer):
    lead_ids = serializers.ListField(child=serializers.UUIDField())
    assigned_to = serializers.UUIDField()


class LeadStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Lead.LEAD_STATUS_CHOICES)
    notes = serializers.CharField(required=False, allow_blank=True)


class LeadStatsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    NEW = serializers.IntegerField(required=False, default=0)
    ASSIGNED = serializers.IntegerField(required=False, default=0)
    IN_PROGRESS = serializers.IntegerField(required=False, default=0)
    CALLBACK = serializers.IntegerField(required=False, default=0)
    INTERESTED = serializers.IntegerField(required=False, default=0)
    DOCUMENTS_REQUESTED = serializers.IntegerField(required=False, default=0)
    DOCUMENTS_RECEIVED = serializers.IntegerField(required=False, default=0)
    BANK_LOGIN = serializers.IntegerField(required=False, default=0)
    APPROVED = serializers.IntegerField(required=False, default=0)
    REJECTED = serializers.IntegerField(required=False, default=0)
    DISBURSED = serializers.IntegerField(required=False, default=0)


class TimelineEventSerializer(serializers.Serializer):
    timestamp = serializers.DateTimeField()
    event_type = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    user_name = serializers.CharField(allow_null=True, source="user_name")
    icon = serializers.CharField()
    color = serializers.CharField()
    url = serializers.URLField(allow_null=True)


class LeadCallSerializer(serializers.ModelSerializer):
    caller_name = serializers.SerializerMethodField()
    call_type_display = serializers.CharField(source="get_call_type_display", read_only=True)
    call_status_display = serializers.CharField(source="get_call_status_display", read_only=True)

    class Meta:
        model = LeadCall
        fields = [
            "id", "lead", "call_type", "call_type_display", "call_status",
            "call_status_display", "caller", "caller_name", "duration_seconds",
            "notes", "recording_url", "call_time", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_caller_name(self, obj):
        if obj.caller:
            return obj.caller.get_full_name() or obj.caller.username
        return None
