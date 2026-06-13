import os
import json
from django.views.generic import ListView, DetailView, FormView, TemplateView, View
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.conf import settings
from django.http import HttpResponse, FileResponse
from django.db.models import Q, Count

from accounts.mixins import ActiveUserRequiredMixin, AdminOrTeamLeadRequiredMixin
from .models import ImageUpload, ImageBatch
from .forms import ImageUploadForm, ImageBatchAssignForm
from .services import process_uploaded_image, rotate_image, create_batch_from_images, bulk_assign_images


class ImageUploadView(AdminOrTeamLeadRequiredMixin, FormView):
    form_class = ImageUploadForm
    template_name = "uploads/image_upload.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["image_types"] = ImageUpload.IMAGE_TYPE_CHOICES
        return ctx

    def form_valid(self, form):
        files = self.request.FILES.getlist("files")
        campaign = form.cleaned_data.get("campaign")
        batch_name = form.cleaned_data.get("batch_name", "")
        description = form.cleaned_data.get("description", "")

        if not files:
            messages.error(self.request, "No files selected.")
            return self.form_invalid(form)

        success_count = 0
        error_count = 0
        images = []

        for f in files:
            try:
                image = process_uploaded_image(f, self.request.user)
                images.append(image)
                success_count += 1
            except ValueError as e:
                error_count += 1
                messages.warning(self.request, f"{f.name}: {e}")

        if batch_name and images:
            from django.db.models import Case, When

            img_qs = ImageUpload.objects.filter(id__in=[img.id for img in images])
            batch = create_batch_from_images(
                img_qs, batch_name, self.request.user, campaign, description
            )
            messages.success(
                self.request,
                f"Uploaded {success_count} image(s) in batch '{batch.name}'. "
                f"{f'({error_count} failed)' if error_count else ''}"
            )
            return redirect("imager:gallery")
        elif images:
            messages.success(
                self.request,
                f"Uploaded {success_count} image(s). "
                f"{f'({error_count} failed)' if error_count else ''}"
            )
            return redirect("imager:gallery")
        else:
            messages.error(self.request, "No images were uploaded successfully.")
            return self.form_invalid(form)


class ImageGalleryView(ActiveUserRequiredMixin, ListView):
    model = ImageUpload
    template_name = "uploads/image_gallery.html"
    context_object_name = "images"
    paginate_by = 24

    def get_queryset(self):
        qs = ImageUpload.objects.select_related("lead", "batch", "uploaded_by").all()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(file_name__icontains=q)
                | Q(image_type__icontains=q)
                | Q(lead__customer_name__icontains=q)
                | Q(lead__lead_number__icontains=q)
            )
        image_type = self.request.GET.get("image_type", "").strip()
        if image_type:
            qs = qs.filter(image_type=image_type)
        batch_id = self.request.GET.get("batch", "").strip()
        if batch_id:
            qs = qs.filter(batch_id=batch_id)
        lead_id = self.request.GET.get("lead", "").strip()
        if lead_id:
            qs = qs.filter(lead_id=lead_id)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["image_types"] = ImageUpload.IMAGE_TYPE_CHOICES
        ctx["batches"] = ImageBatch.objects.annotate(
            img_count=Count("images")
        ).filter(img_count__gt=0)[:50]
        ctx["active_type"] = self.request.GET.get("image_type", "")
        ctx["active_batch"] = self.request.GET.get("batch", "")
        ctx["search_query"] = self.request.GET.get("q", "")
        return ctx


class ImageViewerView(ActiveUserRequiredMixin, DetailView):
    model = ImageUpload
    template_name = "uploads/image_viewer.html"
    context_object_name = "image"

    def get_queryset(self):
        return ImageUpload.objects.select_related("lead", "batch", "uploaded_by")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        image = self.object
        ctx["prev_image"] = (
            ImageUpload.objects.filter(created_at__gt=image.created_at)
            .exclude(id=image.id)
            .order_by("created_at")
            .first()
        )
        ctx["next_image"] = (
            ImageUpload.objects.filter(created_at__lt=image.created_at)
            .exclude(id=image.id)
            .order_by("-created_at")
            .first()
        )
        ctx["MEDIA_URL"] = settings.MEDIA_URL
        return ctx


class ImageRotateView(ActiveUserRequiredMixin, View):
    def post(self, request, pk):
        image = get_object_or_404(ImageUpload, id=pk)
        degrees = int(request.POST.get("degrees", 90))
        rotate_image(image, degrees)
        messages.success(request, f"Image rotated {degrees} degrees.")
        return redirect("imager:viewer", pk=pk)


class ImageDownloadView(ActiveUserRequiredMixin, View):
    def get(self, request, pk):
        image = get_object_or_404(ImageUpload, id=pk)
        abs_path = os.path.join(settings.MEDIA_ROOT, image.file_path)
        if not os.path.exists(abs_path):
            messages.error(request, "File not found on disk.")
            return redirect("imager:gallery")
        response = FileResponse(open(abs_path, "rb"), as_attachment=True, filename=image.file_name)
        return response


class ImageBatchListView(ActiveUserRequiredMixin, ListView):
    model = ImageBatch
    template_name = "uploads/image_batch_list.html"
    context_object_name = "batches"
    paginate_by = 20
    ordering = ["-created_at"]

    def get_queryset(self):
        return ImageBatch.objects.select_related("campaign", "created_by").annotate(
            img_count=Count("images"),
            linked_leads_count=Count("images__lead", distinct=True),
        ).all()


class ImageBatchAssignView(AdminOrTeamLeadRequiredMixin, View):
    def post(self, request, pk):
        image_ids = request.POST.getlist("image_ids")
        lead_id = request.POST.get("lead_id")

        if not image_ids or not lead_id:
            messages.error(request, "Please select images and specify a lead.")
            return redirect("imager:gallery")

        try:
            updated, lead = bulk_assign_images(image_ids, lead_id, request.user)
            messages.success(
                request,
                f"Assigned {updated} image(s) to lead '{lead.customer_name}' ({lead.lead_number}).",
            )
        except Exception as e:
            messages.error(request, f"Assignment failed: {e}")

        return redirect("imager:gallery")
