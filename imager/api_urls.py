from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import ImageUploadViewSet, ImageBatchViewSet

router = DefaultRouter()
router.register(r"images", ImageUploadViewSet, basename="api_image")
router.register(r"image-batches", ImageBatchViewSet, basename="api_image_batch")

app_name = "imager_api"

urlpatterns = [
    path("", include(router.urls)),
]
