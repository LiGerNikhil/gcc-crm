from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import PDFImportViewSet

router = DefaultRouter()
router.register(r"pdf-imports", PDFImportViewSet, basename="api_pdf_import")

app_name = "pdf_api"

urlpatterns = [
    path("", include(router.urls)),
]
