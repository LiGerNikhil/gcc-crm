from django.urls import path
from . import views

app_name = "leads"

urlpatterns = [
    path("", views.LeadListView.as_view(), name="list"),
    path("create/", views.LeadCreateView.as_view(), name="create"),
    path("<uuid:pk>/", views.LeadDetailView.as_view(), name="detail"),
    path("<uuid:pk>/edit/", views.LeadUpdateView.as_view(), name="edit"),
    path("<uuid:pk>/delete/", views.LeadDeleteView.as_view(), name="delete"),
    path("<uuid:pk>/status/", views.LeadUpdateStatusView.as_view(), name="update_status"),
    path("<uuid:pk>/notes/", views.LeadNoteCreateView.as_view(), name="add_note"),
    path("<uuid:pk>/followups/", views.FollowUpCreateView.as_view(), name="add_followup"),
    path("<uuid:pk>/followups/<uuid:fupk>/complete/", views.FollowUpCompleteView.as_view(), name="complete_followup"),
    path("<uuid:pk>/reassign/", views.LeadReassignView.as_view(), name="reassign"),
    path("<uuid:pk>/timeline/", views.LeadTimelineView.as_view(), name="timeline"),
    path("<uuid:pk>/calls/", views.LeadCallCreateView.as_view(), name="add_call"),
    # Assignment
    path("assign/", views.LeadAssignView.as_view(), name="assign"),
    path("assign/round-robin/", views.LeadAssignRoundRobinView.as_view(), name="assign_round_robin"),
    path("assignments/history/", views.AssignmentHistoryView.as_view(), name="assignment_history"),
    # Assignment Rules
    path("assignment-rules/", views.AssignmentRuleListView.as_view(), name="assignment_rules"),
    path("assignment-rules/create/", views.AssignmentRuleCreateView.as_view(), name="assignment_rule_create"),
    path("assignment-rules/<uuid:pk>/edit/", views.AssignmentRuleUpdateView.as_view(), name="assignment_rule_edit"),
    path("assignment-rules/<uuid:pk>/delete/", views.AssignmentRuleDeleteView.as_view(), name="assignment_rule_delete"),
]
