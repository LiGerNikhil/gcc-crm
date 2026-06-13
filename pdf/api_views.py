from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import PDFImport, PDFPage
from .serializers import (
    PDFImportListSerializer, PDFImportDetailSerializer,
    PDFPageSerializer, PDFUploadSerializer,
)
from .services import upload_and_process
from excel.permissions import CanImportLeads


class PDFImportViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PDFImport.objects.select_related(
        "batch__campaign", "created_by"
    ).all()
    permission_classes = [IsAuthenticated, CanImportLeads]
    search_fields = ["file_name", "status", "created_by__username", "batch__name", "batch__campaign__name"]
    ordering_fields = ["created_at", "updated_at", "status", "total_pages"]
    filterset_fields = ["status"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PDFImportDetailSerializer
        return PDFImportListSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    @action(detail=False, methods=["post"])
    def upload(self, request):
        serializer = PDFUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file = serializer.validated_data["file"]
        if not file.name.lower().endswith(".pdf"):
            return Response(
                {"error": "Only PDF files are supported."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        pdf_import = upload_and_process(
            uploaded_file=file,
            campaign_id=serializer.validated_data["campaign_id"],
            created_by=request.user,
        )
        return Response(
            PDFImportDetailSerializer(pdf_import, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"])
    def pages(self, request, pk=None):
        pdf_import = self.get_object()
        pages = pdf_import.pages.all().order_by("page_number")
        serializer = PDFPageSerializer(
            pages, many=True, context={"request": request}
        )
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def page(self, request, pk=None):
        page_number = request.query_params.get("page", 1)
        try:
            page_number = int(page_number)
        except (ValueError, TypeError):
            return Response({"error": "Invalid page number"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            page = PDFPage.objects.get(pdf_import_id=pk, page_number=page_number)
            serializer = PDFPageSerializer(page, context={"request": request})
            return Response(serializer.data)
        except PDFPage.DoesNotExist:
            return Response(
                {"error": f"Page {page_number} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
