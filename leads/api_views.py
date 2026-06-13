from django.db.models import Q
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Lead, LeadNote, FollowUp, LeadAssignment, AssignmentRule, LeadCall
from .serializers import (
    LeadListSerializer, LeadDetailSerializer, LeadNoteSerializer,
    FollowUpSerializer, LeadStatusLogSerializer, LeadBulkAssignSerializer,
    LeadStatusUpdateSerializer, LeadStatsSerializer,
    LeadAssignmentSerializer, AssignmentRuleSerializer,
    RoundRobinAssignRequestSerializer, ReassignRequestSerializer,
    TimelineEventSerializer, LeadCallSerializer,
)
from .permissions import IsAdminOrTeamLead, IsCaller, IsAssignedOrAdmin
from .services import (
    assign_lead_manual, assign_lead_bulk, assign_round_robin,
    reassign_lead, get_assignment_history, get_available_callers,
    get_caller_load, get_assignment_stats, get_lead_timeline,
)
from .filters import LeadFilter


class LeadViewSet(viewsets.ModelViewSet):
    queryset = Lead.objects.filter(is_deleted=False)
    permission_classes = [IsAuthenticated]
    search_fields = ["customer_name", "lead_number", "phone", "email", "pan_number", "city"]
    ordering_fields = ["created_at", "updated_at", "loan_amount", "customer_name", "lead_status", "priority"]

    def get_serializer_class(self):
        if self.action in ("retrieve",):
            return LeadDetailSerializer
        if self.action == "stats":
            return LeadStatsSerializer
        if self.action in ("assignments",):
            return LeadAssignmentSerializer
        return LeadListSerializer

    def get_permissions(self):
        if self.action in ("create", "bulk_assign", "round_robin_assign"):
            return [IsAuthenticated(), IsAdminOrTeamLead()]
        if self.action in ("destroy",):
            return [IsAuthenticated(), IsAdminOrTeamLead()]
        if self.action in ("update", "partial_update", "update_status"):
            return [IsAuthenticated(), IsCaller()]
        if self.action == "reassign":
            return [IsAuthenticated(), IsAdminOrTeamLead()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset().select_related(
            "assigned_to", "batch__campaign__bank_source"
        )
        user = self.request.user
        role_code = _get_role_code(user)
        if role_code == "CALLER":
            qs = qs.filter(assigned_to=user)
        elif role_code == "TEAM_LEAD":
            from accounts.models import UserProfile
            profile = user.profile
            team = UserProfile.objects.filter(manager=profile).values_list("user_id", flat=True)
            qs = qs.filter(
                Q(assigned_to__in=team) | Q(assigned_to=user)
            )
        return qs

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        f = LeadFilter(request.GET, queryset=qs)
        page = self.paginate_queryset(f.qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(f.qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def bulk_assign(self, request):
        serializer = LeadBulkAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from accounts.models import User
        user = User.objects.get(id=serializer.validated_data["assigned_to"])
        results = assign_lead_bulk(
            serializer.validated_data["lead_ids"],
            user,
            assigned_by=request.user,
        )
        return Response({"results": results}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def round_robin_assign(self, request):
        serializer = RoundRobinAssignRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            results, rule = assign_round_robin(
                serializer.validated_data["lead_ids"],
                serializer.validated_data["rule_id"],
                assigned_by=request.user,
            )
            return Response({"results": results, "rule": rule.name}, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def reassign(self, request, pk=None):
        lead = self.get_object()
        serializer = ReassignRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from accounts.models import User
        try:
            new_user = User.objects.get(id=serializer.validated_data["assigned_to"])
            reassign_lead(
                lead, new_user, assigned_by=request.user,
                reason=serializer.validated_data.get("reason", ""),
            )
            return Response({"status": "reassigned", "to": str(new_user.id)})
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=["get"])
    def assignments(self, request, pk=None):
        lead = self.get_object()
        history = get_assignment_history(lead=lead)
        page = self.paginate_queryset(history)
        if page is not None:
            serializer = LeadAssignmentSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = LeadAssignmentSerializer(history, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def update_status(self, request, pk=None):
        lead = self.get_object()
        serializer = LeadStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from .services import change_lead_status
        changed = change_lead_status(
            lead,
            serializer.validated_data["status"],
            changed_by=request.user,
            notes=serializer.validated_data.get("notes", ""),
        )
        return Response({"changed": changed, "new_status": lead.lead_status})

    @action(detail=False, methods=["get"])
    def stats(self, request):
        data = get_lead_stats()
        serializer = LeadStatsSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)

    @action(detail=True, methods=["get"])
    def notes(self, request, pk=None):
        lead = self.get_object()
        notes = lead.lead_notes.select_related("created_by").all()
        page = self.paginate_queryset(notes)
        if page is not None:
            serializer = LeadNoteSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = LeadNoteSerializer(notes, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def add_note(self, request, pk=None):
        lead = self.get_object()
        serializer = LeadNoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(lead=lead, created_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def followups(self, request, pk=None):
        lead = self.get_object()
        fups = lead.lead_followups.select_related("assigned_to", "created_by").all()
        page = self.paginate_queryset(fups)
        if page is not None:
            serializer = FollowUpSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = FollowUpSerializer(fups, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def add_followup(self, request, pk=None):
        lead = self.get_object()
        serializer = FollowUpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(lead=lead, created_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def complete_followup(self, request, pk=None):
        lead = self.get_object()
        fup_id = request.data.get("followup_id")
        if not fup_id:
            return Response({"error": "followup_id required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            fup = lead.lead_followups.get(id=fup_id)
            fup.status = "COMPLETED"
            fup.save(update_fields=["status"])
            return Response({"status": "completed"})
        except FollowUp.DoesNotExist:
            return Response({"error": "Follow-up not found"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=["get"])
    def status_logs(self, request, pk=None):
        lead = self.get_object()
        logs = lead.status_logs.select_related("changed_by").all()
        serializer = LeadStatusLogSerializer(logs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def timeline(self, request, pk=None):
        lead = self.get_object()
        events = get_lead_timeline(lead, limit=200)
        serializer = TimelineEventSerializer(events, many=True)
        return Response(serializer.data)


class LeadCallViewSet(viewsets.ModelViewSet):
    queryset = LeadCall.objects.select_related("caller").all()
    permission_classes = [IsAuthenticated]
    serializer_class = LeadCallSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        lead_id = self.request.query_params.get("lead")
        if lead_id:
            qs = qs.filter(lead_id=lead_id)
        return qs.order_by("-call_time")

    def perform_create(self, serializer):
        serializer.save(caller=self.request.user)


class AssignmentRuleViewSet(viewsets.ModelViewSet):
    queryset = AssignmentRule.objects.select_related("campaign", "team_lead").all()
    permission_classes = [IsAuthenticated, IsAdminOrTeamLead]
    serializer_class = AssignmentRuleSerializer

    def get_queryset(self):
        return AssignmentRule.objects.filter(
            team_lead=self.request.user
        ).select_related("campaign", "team_lead").all()

    def perform_create(self, serializer):
        serializer.save(team_lead=self.request.user)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        data = get_assignment_stats(team_lead=request.user)
        return Response(data)

    @action(detail=True, methods=["get"])
    def callers(self, request, pk=None):
        rule = self.get_object()
        counters = rule.round_robin_counters.select_related("caller").all()
        from .serializers import RoundRobinCounterSerializer
        serializer = RoundRobinCounterSerializer(counters, many=True)
        return Response(serializer.data)


class AssignmentHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LeadAssignment.objects.select_related(
        "lead", "assigned_to", "assigned_by"
    ).all()
    permission_classes = [IsAuthenticated]
    serializer_class = LeadAssignmentSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        role_code = _get_role_code(user)
        if role_code == "CALLER":
            qs = qs.filter(assigned_to=user)
        elif role_code == "TEAM_LEAD":
            from accounts.models import UserProfile
            profile = user.profile
            team = UserProfile.objects.filter(manager=profile).values_list("user_id", flat=True)
            qs = qs.filter(assigned_to__in=team)
        lead_id = self.request.query_params.get("lead")
        if lead_id:
            qs = qs.filter(lead_id=lead_id)
        user_id = self.request.query_params.get("user")
        if user_id:
            qs = qs.filter(assigned_to_id=user_id)
        atype = self.request.query_params.get("type")
        if atype:
            qs = qs.filter(assignment_type=atype)
        return qs.order_by("-created_at")


def _get_role_code(user):
    try:
        return user.profile.role.role_code
    except Exception:
        return None
