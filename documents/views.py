import json
import os

from django.views.generic import ListView, DetailView, FormView, View
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.http import FileResponse, Http404
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model

from accounts.mixins import (
    AdminOrTeamLeadRequiredMixin,
    ManagerRequiredMixin,
    CallerRequiredMixin,
    ManagerOrTeamLeadRequiredMixin,
)
from .models import UploadBatch, WorkItem, WorkAssignment, WorkNote, WorkRevert, WorkTimeline
from .forms import (
    PDFUploadForm,
    ImageUploadForm,
    ExcelUploadForm,
    WorkItemAssignForm,
    WorkItemStatusForm,
    WorkNoteForm,
    WorkRevertForm,
)
from .services import (
    process_pdf_upload,
    process_image_upload,
    process_excel_upload,
    get_page_preview_url,
    get_page_thumbnail_url,
    get_image_preview_url,
    get_image_thumbnail_url,
)
from .status import change_status, get_allowed_transition_choices

User = get_user_model()


def _parse_extracted_data(raw):
    """Parse JSON extracted_data into a list of {label, value} pairs."""
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    if isinstance(data, dict):
        return [{"label": k, "value": v} for k, v in data.items()]
    return []


# ── Batch Views ────────────────────────────────────────────────

class BatchListView(AdminOrTeamLeadRequiredMixin, ListView):
    model = UploadBatch
    template_name = "documents/batch_list.html"
    context_object_name = "batches"
    paginate_by = 20

    def get_queryset(self):
        qs = UploadBatch.objects.select_related(
            "bank_source", "uploaded_by"
        ).all()
        if self.request.GET.get("type"):
            qs = qs.filter(upload_type=self.request.GET["type"])
        if self.request.GET.get("status"):
            qs = qs.filter(status=self.request.GET["status"])
        return qs.order_by("-upload_date")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["upload_types"] = UploadBatch.UPLOAD_TYPES
        ctx["batch_statuses"] = UploadBatch.BATCH_STATUS
        ctx["current_type"] = self.request.GET.get("type", "")
        ctx["current_status"] = self.request.GET.get("status", "")
        return ctx


class BatchDetailView(AdminOrTeamLeadRequiredMixin, DetailView):
    model = UploadBatch
    template_name = "documents/batch_detail.html"
    context_object_name = "batch"

    def get_queryset(self):
        return UploadBatch.objects.select_related(
            "bank_source", "uploaded_by"
        ).prefetch_related("work_items")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        work_items = self.object.work_items.select_related("assigned_to").order_by("sequence")
        ctx["work_items"] = work_items
        ctx["total_pending"] = work_items.filter(status="PENDING").count()
        ctx["total_completed"] = work_items.filter(status="COMPLETED").count()
        ctx["total_in_progress"] = work_items.filter(status="IN_PROGRESS").count()
        ctx["total_failed"] = work_items.filter(status__in=["FAILED", "SKIPPED"]).count()

        # Users that the current user can assign work to
        role = self.request.user.profile.role.role_code if hasattr(self.request.user, "profile") and self.request.user.profile.role else ""
        if role == "SUPER_ADMIN":
            qs = User.objects.filter(is_active=True)
        elif role == "MANAGER":
            qs = User.objects.filter(profile__role__role_code__in=["TEAM_LEAD", "ARO", "CALLER"], is_active=True)
        elif role == "TEAM_LEAD":
            qs = User.objects.filter(profile__role__role_code__in=["ARO", "CALLER"], is_active=True)
        else:
            qs = User.objects.none()
        ctx["assignable_users"] = qs.select_related("profile__role").order_by("username")
        return ctx


# ── PDF Upload ─────────────────────────────────────────────────

class PDFUploadView(ManagerRequiredMixin, FormView):
    form_class = PDFUploadForm
    template_name = "documents/pdf_upload.html"

    def form_valid(self, form):
        batch = process_pdf_upload(
            uploaded_file=form.cleaned_data["file"],
            bank_source=None,
            uploaded_by=self.request.user,
            notes=form.cleaned_data.get("notes", ""),
        )
        if batch.status == "FAILED":
            messages.error(self.request, f"PDF processing failed: {batch.error_log}")
            return redirect("documents:batch_detail", pk=batch.id)

        messages.success(
            self.request,
            f"PDF processed. {batch.total_records} pages extracted as work items.",
        )
        return redirect("documents:batch_detail", pk=batch.id)


# ── Image Upload ───────────────────────────────────────────────

class ImageUploadView(ManagerRequiredMixin, FormView):
    form_class = ImageUploadForm
    template_name = "documents/image_upload.html"

    def form_valid(self, form):
        files = form.cleaned_data["files"]
        batch = process_image_upload(
            uploaded_files=files,
            bank_source=None,
            uploaded_by=self.request.user,
            notes=form.cleaned_data.get("notes", ""),
        )
        if batch.status == "FAILED":
            messages.error(self.request, f"Image processing failed: {batch.error_log}")
        elif batch.status == "PARTIAL":
            messages.warning(
                self.request,
                f"{batch.total_records} of {len(files)} images uploaded. Some had errors.",
            )
        else:
            messages.success(
                self.request,
                f"{batch.total_records} images uploaded and processed.",
            )
        return redirect("documents:batch_detail", pk=batch.id)


# ── Excel Upload ──────────────────────────────────────────────

class ExcelUploadView(ManagerRequiredMixin, FormView):
    form_class = ExcelUploadForm
    template_name = "documents/excel_upload.html"

    def form_valid(self, form):
        batch = process_excel_upload(
            uploaded_file=form.cleaned_data["file"],
            bank_source=None,
            uploaded_by=self.request.user,
            notes=form.cleaned_data.get("notes", ""),
        )
        if batch.status == "FAILED":
            messages.error(self.request, f"Excel processing failed: {batch.error_log}")
        else:
            messages.success(
                self.request,
                f"Excel processed. {batch.total_records} rows imported as work items.",
            )
        return redirect("documents:batch_detail", pk=batch.id)


# ── Work Item Views ────────────────────────────────────────────

class WorkItemDetailView(CallerRequiredMixin, DetailView):
    model = WorkItem
    template_name = "documents/workitem_detail.html"
    context_object_name = "work_item"

    def get_queryset(self):
        return WorkItem.objects.select_related(
            "batch__bank_source", "assigned_to", "lead"
        ).prefetch_related(
            "assignments__assigned_to",
            "assignments__assigned_by",
            "notes__created_by",
            "reverts__reverted_by",
            "status_history__changed_by",
            "timeline_entries__performed_by",
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        wi = self.object
        ctx["page_preview_url"] = get_page_preview_url(wi)
        ctx["page_thumbnail_url"] = get_page_thumbnail_url(wi)
        ctx["image_preview_url"] = get_image_preview_url(wi)
        ctx["image_thumbnail_url"] = get_image_thumbnail_url(wi)
        ctx["is_image"] = wi.batch.upload_type == "IMAGE"
        ctx["is_pdf"] = wi.batch.upload_type == "PDF"
        ctx["is_excel"] = wi.batch.upload_type == "EXCEL"
        ctx["extracted_fields"] = _parse_extracted_data(wi.extracted_data)
        ctx["assign_form"] = WorkItemAssignForm()
        ctx["note_form"] = WorkNoteForm()
        ctx["revert_form"] = WorkRevertForm()
        ctx["status_form"] = WorkItemStatusForm(current_status=wi.status)
        ctx["allowed_transitions"] = get_allowed_transition_choices(wi.status)
        ctx["status_history"] = wi.status_history.select_related("changed_by").order_by("-changed_at")
        ctx["timeline"] = wi.timeline_entries.select_related("performed_by").order_by("-timestamp")
        ctx["assignment_history"] = wi.assignments.select_related(
            "assigned_to", "assigned_by"
        ).order_by("-assigned_at")
        return ctx


class WorkItemAssignView(ManagerOrTeamLeadRequiredMixin, View):

    def post(self, request, pk):
        work_item = get_object_or_404(WorkItem, pk=pk)
        user = request.user
        role = user.profile.role.role_code if hasattr(user, "profile") and user.profile.role else ""

        # Build assignable user queryset based on assigning role
        if role == "SUPER_ADMIN":
            qs = User.objects.filter(is_active=True)
        elif role == "MANAGER":
            qs = User.objects.filter(profile__role__role_code__in=["TEAM_LEAD", "ARO", "CALLER"], is_active=True)
        elif role == "TEAM_LEAD":
            qs = User.objects.filter(profile__role__role_code__in=["ARO", "CALLER"], is_active=True)
        else:
            qs = User.objects.none()
        qs = qs.select_related("profile__role").order_by("username")

        form = WorkItemAssignForm(data=request.POST, user_queryset=qs)
        if not form.is_valid():
            for err in form.errors.values():
                messages.error(request, err)
            return redirect("documents:workitem_detail", pk=work_item.id)

        assigned_to = form.cleaned_data["assigned_to"]
        notes = form.cleaned_data.get("notes", "")

        with transaction.atomic():
            # Close any active assignment
            WorkAssignment.objects.filter(work_item=work_item, unassigned_at__isnull=True).update(
                unassigned_at=timezone.now()
            )
            # Create new assignment record
            WorkAssignment.objects.create(
                work_item=work_item, assigned_to=assigned_to,
                assigned_by=request.user, notes=notes,
            )
            # Update denormalized fields on the work item
            old_status = work_item.status
            work_item.assigned_to = assigned_to
            work_item.assigned_at = timezone.now()

            if work_item.status == "NEW":
                # First assignment transitions NEW → ASSIGNED
                work_item = change_status(work_item, "ASSIGNED",
                                          changed_by=request.user, notes=notes, is_system=False)
                # change_status only saves status fields; persist assignment too
                WorkItem.objects.filter(pk=work_item.pk).update(
                    assigned_to=assigned_to, assigned_at=work_item.assigned_at,
                )
            else:
                work_item.save(update_fields=["assigned_to", "assigned_at"])
                WorkTimeline.objects.create(
                    work_item=work_item, action="ASSIGNED",
                    description=f"Assigned to {assigned_to.get_full_name() or assigned_to.username}",
                    from_status=old_status, to_status=old_status,
                    performed_by=request.user, timestamp=timezone.now(),
                )

        messages.success(request, f"Work item assigned to {assigned_to.get_full_name() or assigned_to.username}.")
        return redirect("documents:workitem_detail", pk=work_item.id)


class WorkItemStatusUpdateView(CallerRequiredMixin, View):

    def post(self, request, pk):
        work_item = get_object_or_404(WorkItem, pk=pk)
        form = WorkItemStatusForm(data=request.POST, current_status=work_item.status)

        if not form.is_valid():
            for err in form.errors.values():
                messages.error(request, err)
            return redirect("documents:workitem_detail", pk=work_item.id)

        new_status = form.cleaned_data["new_status"]
        try:
            work_item = change_status(
                work_item=work_item,
                new_status=new_status,
                changed_by=request.user,
                notes=form.cleaned_data.get("notes", ""),
            )
            messages.success(request, f"Status updated to {work_item.get_status_display()}.")
        except ValueError as e:
            messages.error(request, str(e))

        return redirect("documents:workitem_detail", pk=work_item.id)


class WorkItemNoteCreateView(CallerRequiredMixin, View):

    def post(self, request, pk):
        work_item = get_object_or_404(WorkItem, pk=pk)
        form = WorkNoteForm(data=request.POST)
        if not form.is_valid():
            for err in form.errors.values():
                messages.error(request, err)
            return redirect("documents:workitem_detail", pk=work_item.id)

        with transaction.atomic():
            note = form.save(commit=False)
            note.work_item = work_item
            note.created_by = request.user
            note.save()
            action = "FEEDBACK" if note.is_feedback else "NOTE_ADDED"
            desc = "Feedback submitted" if note.is_feedback else "Note added"
            WorkTimeline.objects.create(
                work_item=work_item, action=action,
                description=desc,
                performed_by=request.user, timestamp=timezone.now(),
            )
        msg = "Feedback submitted." if note.is_feedback else "Note added."
        messages.success(request, msg)
        return redirect("documents:workitem_detail", pk=work_item.id)


class WorkItemRevertView(ManagerOrTeamLeadRequiredMixin, View):

    def post(self, request, pk):
        work_item = get_object_or_404(WorkItem, pk=pk)
        form = WorkRevertForm(data=request.POST, files=request.FILES)
        if not form.is_valid():
            for err in form.errors.values():
                messages.error(request, err)
            return redirect("documents:workitem_detail", pk=work_item.id)

        previous_status = work_item.status
        with transaction.atomic():
            revert = form.save(commit=False)
            revert.work_item = work_item
            revert.previous_status = previous_status
            revert.restored_status = "REJECTED"
            revert.reverted_by = request.user
            revert.save()

            notes = f"Reverted: {revert.get_reason_display()}"
            if revert.remarks:
                notes += f" — {revert.remarks}"
            change_status(work_item, "REJECTED", changed_by=request.user,
                          notes=notes, is_system=False)

        messages.success(request, "Work item rejected.")
        return redirect("documents:workitem_detail", pk=work_item.id)


class BulkAssignView(ManagerOrTeamLeadRequiredMixin, View):
    """Assign multiple work items in one operation."""

    def post(self, request):
        raw_ids = request.POST.get("work_items", "")
        work_item_ids = [id.strip() for id in raw_ids.split(",") if id.strip()]
        assign_to_id = request.POST.get("assign_to")
        notes = request.POST.get("notes", "")

        if not work_item_ids or not assign_to_id:
            messages.error(request, "Select work items and an assignee.")
            return redirect(request.META.get("HTTP_REFERER", "documents:batch_list"))

        assign_to = get_object_or_404(User, pk=assign_to_id)
        work_items = WorkItem.objects.filter(pk__in=work_item_ids).select_related("batch")

        if not work_items:
            messages.error(request, "No valid work items selected.")
            return redirect(request.META.get("HTTP_REFERER", "documents:batch_list"))

        success = 0
        with transaction.atomic():
            for work_item in work_items:
                # Close active assignment
                WorkAssignment.objects.filter(
                    work_item=work_item, unassigned_at__isnull=True
                ).update(unassigned_at=timezone.now())

                WorkAssignment.objects.create(
                    work_item=work_item, assigned_to=assign_to,
                    assigned_by=request.user, notes=notes,
                )

                old_status = work_item.status
                work_item.assigned_to = assign_to
                work_item.assigned_at = timezone.now()

                if work_item.status == "NEW":
                    work_item = change_status(
                        work_item, "ASSIGNED", changed_by=request.user,
                        notes=notes, is_system=False,
                    )
                    # change_status only saves status; persist assignment too
                    WorkItem.objects.filter(pk=work_item.pk).update(
                        assigned_to=assign_to, assigned_at=work_item.assigned_at,
                    )
                else:
                    work_item.save(update_fields=["assigned_to", "assigned_at"])
                    WorkTimeline.objects.create(
                        work_item=work_item, action="ASSIGNED",
                        description=f"Bulk assigned to {assign_to.get_full_name() or assign_to.username}",
                        from_status=old_status, to_status=old_status,
                        performed_by=request.user, timestamp=timezone.now(),
                    )
                success += 1

        messages.success(
            request,
            f"{success} work item(s) assigned to {assign_to.get_full_name() or assign_to.username}.",
        )
        return redirect(request.META.get("HTTP_REFERER", "documents:batch_list"))


# ── File Serving Views ─────────────────────────────────────────

class PagePreviewView(View):
    """Serve page preview image for a work item."""

    def get(self, request, pk):
        work_item = get_object_or_404(WorkItem, pk=pk)
        path = request.GET.get("thumb") and (work_item.page_thumbnail or work_item.page_preview)
        path = path or work_item.page_preview
        if not path or not os.path.exists(path):
            raise Http404("Preview not found")
        return FileResponse(open(path, "rb"), content_type="image/png")


class OriginalPDFDownloadView(View):
    """Download the original PDF file for a batch."""

    def get(self, request, pk):
        batch = get_object_or_404(UploadBatch, pk=pk)
        if not batch.file_path or not os.path.exists(batch.file_path):
            raise Http404("Original PDF file not found")
        response = FileResponse(
            open(batch.file_path, "rb"),
            content_type="application/pdf",
        )
        response["Content-Disposition"] = f'attachment; filename="{batch.original_filename or "document.pdf"}"'
        return response


class ImagePreviewView(View):
    """Serve image preview or original for a work item."""

    def get(self, request, pk):
        work_item = get_object_or_404(WorkItem, pk=pk)
        variant = request.GET.get("variant", "preview")
        if variant == "original":
            path = work_item.image_original
        elif variant == "thumb":
            path = work_item.image_thumbnail or work_item.image_preview
        else:
            path = work_item.image_preview or work_item.image_original
        if not path or not os.path.exists(path):
            raise Http404("Image not found")
        content_type = "image/png" if path.lower().endswith(".png") else "image/jpeg"
        return FileResponse(open(path, "rb"), content_type=content_type)


class OriginalImageDownloadView(View):
    """Download the original image file for a work item."""

    def get(self, request, pk):
        work_item = get_object_or_404(WorkItem, pk=pk)
        if not work_item.image_original or not os.path.exists(work_item.image_original):
            raise Http404("Original image not found")
        filename = work_item.item_identifier or f"image_{work_item.id}.jpg"
        response = FileResponse(
            open(work_item.image_original, "rb"),
            content_type="application/octet-stream",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


# ── Work Queue Views ────────────────────────────────────────────

class WorkQueueView(CallerRequiredMixin, ListView):
    """Role-aware work queue showing assigned work items.

    - SUPER_ADMIN / MANAGER: all items under their org tree
    - TEAM_LEAD: items assigned to TL or their AROs
    - ARO / CALLER: items assigned to them
    """
    template_name = "documents/work_queue.html"
    context_object_name = "work_items"
    paginate_by = 25

    def get_queryset(self):
        user = self.request.user
        role = user.profile.role.role_code if hasattr(user, "profile") and user.profile.role else ""
        qs = WorkItem.objects.select_related(
            "batch__bank_source", "assigned_to"
        ).prefetch_related(
            "notes",
            "assignments__assigned_to",
            "assignments__assigned_by",
        )

        now = timezone.now()

        if role == "SUPER_ADMIN":
            # All items that are assigned (not NEW)
            return qs.exclude(status="NEW").exclude(assigned_to__isnull=True)
        elif role == "MANAGER":
            # Items assigned to any team lead or ARO under this manager
            my_tls = User.objects.filter(profile__manager=user.profile, profile__role__role_code="TEAM_LEAD", is_active=True)
            my_aros = User.objects.filter(
                profile__manager__in=my_tls,
                profile__role__role_code__in=["ARO", "CALLER"],
                is_active=True,
            )
            user_ids = [u.id for u in my_tls] + [u.id for u in my_aros] + [user.id]
            return qs.filter(assigned_to_id__in=user_ids).exclude(status="NEW")
        elif role == "TEAM_LEAD":
            # Items assigned to TL or their AROs
            my_aros = User.objects.filter(
                profile__manager=user.profile,
                profile__role__role_code__in=["ARO", "CALLER"],
                is_active=True,
            )
            user_ids = [u.id for u in my_aros] + [user.id]
            return qs.filter(assigned_to_id__in=user_ids).exclude(status__in=["CLOSED", "REJECTED"])
        else:
            # ARO / CALLER: only their own items
            return qs.filter(assigned_to=user).exclude(status__in=["CLOSED", "REJECTED"])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        role = user.profile.role.role_code if hasattr(user, "profile") and user.profile.role else ""

        ctx["role_code"] = role
        ctx["status_choices"] = WorkItem.ITEM_STATUS
        ctx["current_status"] = self.request.GET.get("status", "")
        ctx["total_assigned"] = self.get_queryset().count()

        # Assignable users for TL distribution
        ctx["assignable_users"] = User.objects.none()
        if role == "TEAM_LEAD":
            ctx["assignable_users"] = User.objects.filter(
                profile__manager=user.profile,
                profile__role__role_code__in=["ARO", "CALLER"],
                is_active=True,
            ).select_related("profile__role").order_by("username")
        elif role == "MANAGER":
            ctx["assignable_users"] = User.objects.filter(
                profile__role__role_code__in=["TEAM_LEAD", "ARO", "CALLER"],
                is_active=True,
            ).select_related("profile__role").order_by("username")

        return ctx


class RevertAttachmentDownloadView(View):
    """Download a revert attachment file."""

    def get(self, request, pk):
        revert = get_object_or_404(WorkRevert, pk=pk)
        if not revert.attachment or not os.path.exists(revert.attachment.path):
            raise Http404("Attachment not found")
        response = FileResponse(
            open(revert.attachment.path, "rb"),
            content_type="application/octet-stream",
        )
        filename = os.path.basename(revert.attachment.name)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
