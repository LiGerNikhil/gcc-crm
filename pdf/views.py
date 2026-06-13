import os
from django.views.generic import ListView, DetailView, FormView, TemplateView, View
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.http import FileResponse, Http404
from django.conf import settings

from accounts.mixins import AdminOrTeamLeadRequiredMixin
from .models import PDFImport, PDFPage
from .forms import PDFUploadForm
from .services import upload_and_process


class PDFImportListView(AdminOrTeamLeadRequiredMixin, ListView):
    model = PDFImport
    template_name = "uploads/pdf_list.html"
    context_object_name = "imports"
    paginate_by = 20
    ordering = ["-imported_at"]

    def get_queryset(self):
        return PDFImport.objects.select_related(
            "batch__campaign", "created_by"
        ).all()


class PDFUploadView(AdminOrTeamLeadRequiredMixin, FormView):
    form_class = PDFUploadForm
    template_name = "uploads/pdf_upload.html"

    def form_valid(self, form):
        uploaded_file = form.cleaned_data["file"]
        campaign = form.cleaned_data["campaign"]

        if not uploaded_file.name.lower().endswith(".pdf"):
            messages.error(self.request, "Only PDF files are supported.")
            return self.form_invalid(form)

        pdf_import = upload_and_process(
            uploaded_file=uploaded_file,
            campaign_id=campaign.id,
            created_by=self.request.user,
        )
        if pdf_import.extraction_status == "FAILED":
            messages.error(self.request, f"PDF processing failed: {pdf_import.error_message}")
            return redirect("pdf:detail", pk=pdf_import.id)

        messages.success(self.request, f"PDF processed successfully. {pdf_import.pages_count} pages extracted.")
        return redirect("pdf:viewer", pk=pdf_import.id)


class PDFViewerView(AdminOrTeamLeadRequiredMixin, DetailView):
    model = PDFImport
    template_name = "uploads/pdf_viewer.html"
    context_object_name = "pdf_import"

    def get_queryset(self):
        return PDFImport.objects.filter().select_related(
            "batch__campaign__bank_source", "created_by"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        pages = self.object.pages.all().order_by("page_number")
        ctx["pages"] = pages
        ctx["total_pages"] = pages.count()
        page_num = int(self.request.GET.get("page", 1))
        if page_num < 1:
            page_num = 1
        elif page_num > pages.count():
            page_num = pages.count()
        ctx["current_page_number"] = page_num
        ctx["current_page"] = pages.filter(page_number=page_num).first()
        return ctx


class PDFPageImageView(View):
    def get(self, request, pk, page_number):
        pdf_import = get_object_or_404(PDFImport, pk=pk)
        page = get_object_or_404(
            PDFPage, pdf_import=pdf_import, page_number=page_number
        )
        img_path = page.image_path
        if not os.path.exists(img_path):
            raise Http404("Page image not found")
        return FileResponse(open(img_path, "rb"), content_type="image/png")


class PDFThumbnailView(View):
    def get(self, request, pk, page_number):
        pdf_import = get_object_or_404(PDFImport, pk=pk)
        page = get_object_or_404(
            PDFPage, pdf_import=pdf_import, page_number=page_number
        )
        thumb_path = page.thumbnail_path or page.image_path
        if not os.path.exists(thumb_path):
            raise Http404("Thumbnail not found")
        return FileResponse(open(thumb_path, "rb"), content_type="image/png")


class PDFDownloadView(View):
    def get(self, request, pk):
        pdf_import = get_object_or_404(PDFImport, pk=pk)
        file_path = pdf_import.file_path
        if not os.path.exists(file_path):
            raise Http404("File not found")
        response = FileResponse(
            open(file_path, "rb"),
            content_type="application/pdf",
        )
        response["Content-Disposition"] = f'attachment; filename="{pdf_import.file_name}"'
        return response


class PDFDetailView(AdminOrTeamLeadRequiredMixin, DetailView):
    model = PDFImport
    template_name = "uploads/pdf_detail.html"
    context_object_name = "pdf_import"

    def get_queryset(self):
        return PDFImport.objects.select_related(
            "batch__campaign__bank_source", "created_by"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["pages"] = self.object.pages.all().order_by("page_number")
        return ctx
