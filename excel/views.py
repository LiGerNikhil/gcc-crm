import json
from django.views.generic import ListView, DetailView, FormView, TemplateView, View
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.conf import settings

from accounts.mixins import AdminOrTeamLeadRequiredMixin
from .models import ExcelImport, ExcelImportLog
from .forms import ExcelUploadForm
from .services import preview_import, import_from_upload, process_import


class ExcelImportListView(AdminOrTeamLeadRequiredMixin, ListView):
    model = ExcelImport
    template_name = "uploads/excel_import_list.html"
    context_object_name = "imports"
    paginate_by = 20
    ordering = ["-imported_at"]

    def get_queryset(self):
        return ExcelImport.objects.select_related(
            "batch__campaign", "created_by"
        ).all()


class ExcelUploadView(AdminOrTeamLeadRequiredMixin, FormView):
    form_class = ExcelUploadForm
    template_name = "uploads/excel_upload.html"

    def form_valid(self, form):
        uploaded_file = form.cleaned_data["file"]
        campaign = form.cleaned_data["campaign"]
        batch_name = form.cleaned_data.get("batch_name", "")
        sheet_name = form.cleaned_data.get("sheet_name", "Sheet1")
        header_row = form.cleaned_data.get("header_row", 1) - 1

        ext = uploaded_file.name.split(".")[-1].lower()
        if ext not in ("xlsx", "xls", "csv"):
            messages.error(self.request, "Unsupported file format. Use .xlsx, .xls, or .csv.")
            return self.form_invalid(form)

        excel_import = import_from_upload(
            uploaded_file=uploaded_file,
            campaign_id=campaign.id,
            batch_name=batch_name,
            created_by=self.request.user,
            sheet_name=sheet_name,
            header_row=header_row,
        )
        return redirect("excel:import_preview", pk=excel_import.id)


class ExcelImportPreviewView(AdminOrTeamLeadRequiredMixin, TemplateView):
    template_name = "uploads/excel_preview.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        excel_import = get_object_or_404(ExcelImport, id=self.kwargs["pk"])
        ctx["import_obj"] = excel_import
        try:
            preview = preview_import(
                excel_import.file_path,
                sheet_name=0,
                header_row=0,
                max_rows=50,
            )
            ctx["preview"] = preview
            ctx["has_warnings"] = bool(preview["missing_required"])
        except Exception as e:
            ctx["error"] = str(e)
            ctx["preview"] = None
        return ctx


class ExcelImportProcessView(AdminOrTeamLeadRequiredMixin, View):
    def post(self, request, pk):
        excel_import = get_object_or_404(ExcelImport, id=pk)
        if excel_import.status != "PENDING":
            messages.error(request, "Import already processed.")
            return redirect("excel:import_detail", pk=pk)
        process_import(excel_import.id)
        messages.success(request, "Import completed.")
        return redirect("excel:import_detail", pk=pk)


class ExcelImportDetailView(AdminOrTeamLeadRequiredMixin, DetailView):
    model = ExcelImport
    template_name = "uploads/excel_import_detail.html"
    context_object_name = "import_obj"

    def get_queryset(self):
        return ExcelImport.objects.select_related(
            "batch__campaign__bank_source", "created_by"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["logs"] = self.object.logs.select_related().all()
        ctx["success_logs"] = self.object.logs.filter(status="SUCCESS")
        ctx["failed_logs"] = self.object.logs.filter(status="FAILED")
        ctx["skipped_logs"] = self.object.logs.filter(status="SKIPPED")
        try:
            ctx["error_log_parsed"] = json.loads(self.object.error_log) if self.object.error_log else None
        except (json.JSONDecodeError, TypeError):
            ctx["error_log_parsed"] = self.object.error_log
        return ctx
