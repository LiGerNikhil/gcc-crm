from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import ExcelImportViewSet

router = DefaultRouter()
router.register(r"imports", ExcelImportViewSet, basename="api_excel_import")

app_name = "excel_api"

urlpatterns = [
    path("", include(router.urls)),
]
