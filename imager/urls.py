from django.urls import path
from . import views

app_name = "imager"

urlpatterns = [
    path("", views.ImageGalleryView.as_view(), name="gallery"),
    path("upload/", views.ImageUploadView.as_view(), name="upload"),
    path("batches/", views.ImageBatchListView.as_view(), name="batch_list"),
    path("<uuid:pk>/", views.ImageViewerView.as_view(), name="viewer"),
    path("<uuid:pk>/rotate/", views.ImageRotateView.as_view(), name="rotate"),
    path("<uuid:pk>/download/", views.ImageDownloadView.as_view(), name="download"),
    path("batch/<uuid:pk>/assign/", views.ImageBatchAssignView.as_view(), name="batch_assign"),
]
