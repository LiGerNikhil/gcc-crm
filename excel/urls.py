from django.urls import path
from . import views

app_name = "excel"

urlpatterns = [
    path("", views.ExcelImportListView.as_view(), name="import_list"),
    path("upload/", views.ExcelUploadView.as_view(), name="upload"),
    path("<uuid:pk>/preview/", views.ExcelImportPreviewView.as_view(), name="import_preview"),
    path("<uuid:pk>/process/", views.ExcelImportProcessView.as_view(), name="import_process"),
    path("<uuid:pk>/", views.ExcelImportDetailView.as_view(), name="import_detail"),
]
