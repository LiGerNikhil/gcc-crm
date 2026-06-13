from django.urls import path
from . import views

app_name = "pdf"

urlpatterns = [
    path("", views.PDFImportListView.as_view(), name="list"),
    path("upload/", views.PDFUploadView.as_view(), name="upload"),
    path("<uuid:pk>/", views.PDFDetailView.as_view(), name="detail"),
    path("<uuid:pk>/viewer/", views.PDFViewerView.as_view(), name="viewer"),
    path("<uuid:pk>/page/<int:page_number>/", views.PDFPageImageView.as_view(), name="page_image"),
    path("<uuid:pk>/thumb/<int:page_number>/", views.PDFThumbnailView.as_view(), name="page_thumb"),
    path("<uuid:pk>/download/", views.PDFDownloadView.as_view(), name="download"),
]
