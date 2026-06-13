import json
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import ExcelImport
from .serializers import (
    ExcelImportListSerializer, ExcelImportDetailSerializer,
    ExcelUploadSerializer, PreviewSerializer,
)
from .permissions import CanImportLeads
from .services import preview_import, import_from_upload, process_import


class ExcelImportViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ExcelImport.objects.select_related(
        "batch__campaign", "created_by"
    ).all()
    permission_classes = [IsAuthenticated, CanImportLeads]
    search_fields = ["file_name", "status", "created_by__username", "batch__name", "batch__campaign__name"]
    ordering_fields = ["created_at", "updated_at", "status", "total_rows", "success_count", "error_count"]
    filterset_fields = ["status"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ExcelImportDetailSerializer
        return ExcelImportListSerializer

    @action(detail=False, methods=["post"])
    def upload(self, request):
        serializer = ExcelUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file = serializer.validated_data["file"]
        ext = file.name.split(".")[-1].lower()
        if ext not in ("xlsx", "xls", "csv"):
            return Response(
                {"error": "Unsupported file format. Use .xlsx, .xls, or .csv."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        excel_import = import_from_upload(
            uploaded_file=file,
            campaign_id=serializer.validated_data["campaign_id"],
            batch_name=serializer.validated_data.get("batch_name", ""),
            created_by=request.user,
            sheet_name=serializer.validated_data.get("sheet_name", "Sheet1"),
            header_row=serializer.validated_data.get("header_row", 1) - 1,
        )
        return Response(
            ExcelImportDetailSerializer(excel_import).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"])
    def preview(self, request, pk=None):
        excel_import = self.get_object()
        try:
            preview = preview_import(excel_import.file_path, max_rows=50)
            serializer = PreviewSerializer(data=preview)
            serializer.is_valid(raise_exception=True)
            return Response(serializer.validated_data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def process(self, request, pk=None):
        excel_import = self.get_object()
        if excel_import.status != "PENDING":
            return Response(
                {"error": f"Import already {excel_import.status.lower()}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        process_import(excel_import.id)
        excel_import.refresh_from_db()
        return Response(ExcelImportDetailSerializer(excel_import).data)

    @action(detail=True, methods=["get"])
    def logs(self, request, pk=None):
        excel_import = self.get_object()
        logs = excel_import.logs.all().order_by("row_number")
        from .serializers import ExcelImportLogSerializer
        serializer = ExcelImportLogSerializer(logs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def success_logs(self, request, pk=None):
        excel_import = self.get_object()
        logs = excel_import.logs.filter(status="SUCCESS").order_by("row_number")
        from .serializers import ExcelImportLogSerializer
        serializer = ExcelImportLogSerializer(logs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def error_logs(self, request, pk=None):
        excel_import = self.get_object()
        logs = excel_import.logs.exclude(status="SUCCESS").order_by("row_number")
        from .serializers import ExcelImportLogSerializer
        serializer = ExcelImportLogSerializer(logs, many=True)
        return Response(serializer.data)
