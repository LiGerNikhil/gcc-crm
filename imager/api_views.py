from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import ImageUpload, ImageBatch
from .serializers import (
    ImageUploadListSerializer, ImageUploadDetailSerializer,
    ImageBatchListSerializer, ImageBatchDetailSerializer,
    ImageUploadSerializer, ImageBulkAssignSerializer,
)
from .services import process_uploaded_image, create_batch_from_images, bulk_assign_images


class ImageUploadViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ImageUpload.objects.select_related("lead", "batch", "uploaded_by").all()
    permission_classes = [IsAuthenticated]
    search_fields = ["file_name", "original_name", "uploaded_by__username", "lead__customer_name"]
    ordering_fields = ["uploaded_at", "file_size", "lead__customer_name"]
    filterset_fields = ["lead", "batch", "uploaded_by"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ImageUploadDetailSerializer
        return ImageUploadListSerializer

    @action(detail=False, methods=["post"])
    def upload(self, request):
        serializer = ImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        files = request.FILES.getlist("files")
        campaign_id = serializer.validated_data.get("campaign_id")
        batch_name = serializer.validated_data.get("batch_name", "")
        description = serializer.validated_data.get("description", "")

        if not files:
            return Response({"error": "No files provided."}, status=status.HTTP_400_BAD_REQUEST)

        images = []
        errors = []
        for f in files:
            try:
                image = process_uploaded_image(f, request.user)
                images.append(image)
            except ValueError as e:
                errors.append({"file": f.name, "error": str(e)})

        if batch_name and images:
            img_qs = ImageUpload.objects.filter(id__in=[img.id for img in images])
            create_batch_from_images(img_qs, batch_name, request.user, description=description)

        return Response({
            "uploaded": ImageUploadListSerializer(images, many=True).data,
            "errors": errors,
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def rotate(self, request, pk=None):
        image = self.get_object()
        degrees = int(request.data.get("degrees", 90))
        from .services import rotate_image
        rotate_image(image, degrees)
        return Response(ImageUploadDetailSerializer(image).data)

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        image = self.get_object()
        lead_id = request.data.get("lead_id")
        if not lead_id:
            return Response({"error": "lead_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        from .services import assign_images_to_lead
        assign_images_to_lead([pk], lead_id, request.user)
        return Response(ImageUploadDetailSerializer(image).data)

    @action(detail=False, methods=["post"])
    def bulk_assign(self, request):
        serializer = ImageBulkAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        image_ids = serializer.validated_data["image_ids"]
        lead_id = serializer.validated_data["lead_id"]
        try:
            updated, lead = bulk_assign_images(image_ids, lead_id, request.user)
            return Response({"assigned": updated, "lead": str(lead.id)})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ImageBatchViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ImageBatch.objects.select_related("campaign", "created_by").all()
    permission_classes = [IsAuthenticated]
    serializer_class = ImageBatchListSerializer
    search_fields = ["name", "description", "created_by__username", "campaign__name"]
    ordering_fields = ["created_at", "name"]
    filterset_fields = ["campaign"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ImageBatchDetailSerializer
        return ImageBatchListSerializer

    @action(detail=True, methods=["post"])
    def assign_all(self, request, pk=None):
        batch = self.get_object()
        lead_id = request.data.get("lead_id")
        if not lead_id:
            return Response({"error": "lead_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        image_ids = list(batch.images.values_list("id", flat=True))
        try:
            updated, lead = bulk_assign_images(image_ids, lead_id, request.user)
            return Response({"assigned": updated, "lead": str(lead.id)})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
