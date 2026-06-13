from django.urls import path
from . import org_views

app_name = "org"

urlpatterns = [
    path("", org_views.OrganizationTreeView.as_view(), name="org_tree"),
    path("manager/create/", org_views.ManagerCreateView.as_view(), name="manager_create"),
    path("manager/<uuid:pk>/", org_views.ManagerDetailView.as_view(), name="manager_detail"),
    path("manager/<uuid:pk>/edit/", org_views.ManagerUpdateView.as_view(), name="manager_edit"),
    path("team-lead/create/", org_views.TeamLeadCreateView.as_view(), name="teamlead_create"),
    path("team-lead/<uuid:pk>/", org_views.TeamLeadDetailView.as_view(), name="teamlead_detail"),
    path("team-lead/<uuid:pk>/edit/", org_views.TeamLeadUpdateView.as_view(), name="teamlead_edit"),
    path("aro/create/", org_views.AROCreateView.as_view(), name="aro_create"),
    path("aro/<uuid:pk>/", org_views.ARODetailView.as_view(), name="aro_detail"),
    path("aro/<uuid:pk>/edit/", org_views.AROUpdateView.as_view(), name="aro_edit"),
]
