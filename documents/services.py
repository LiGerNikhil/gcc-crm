import os
import json
import uuid
from datetime import datetime

import fitz
import pandas as pd
from PIL import Image, ImageOps
from django.conf import settings
from django.utils import timezone
from django.db import transaction

from .models import UploadBatch, WorkItem, WorkItemStatus, WorkTimeline


PDF_STORAGE = settings.MEDIA_ROOT / "documents" / "pdf"
IMAGE_STORAGE = settings.MEDIA_ROOT / "documents" / "images"
EXCEL_STORAGE = settings.MEDIA_ROOT / "documents" / "excel"


def process_pdf_upload(uploaded_file, bank_source, uploaded_by, notes=""):
    """Upload a PDF, split into pages, create WorkItems with previews.

    Returns the UploadBatch instance.
    """
    batch = UploadBatch.objects.create(
        bank_source=bank_source,
        upload_type="PDF",
        status="DRAFT",
        original_filename=uploaded_file.name,
        file_size=uploaded_file.size,
        uploaded_by=uploaded_by,
        notes=notes,
    )

    batch_dir = PDF_STORAGE / str(batch.id)
    pages_dir = batch_dir / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    # Save original PDF
    pdf_path = batch_dir / "original.pdf"
    with open(pdf_path, "wb") as f:
        for chunk in uploaded_file.chunks():
            f.write(chunk)
    batch.file_path = str(pdf_path)

    try:
        doc = fitz.open(str(pdf_path))
        total_pages = len(doc)
        batch.status = "PROCESSING"
        batch.save(update_fields=["file_path", "status"])

        with transaction.atomic():
            for page_num in range(total_pages):
                page = doc[page_num]
                pix = page.get_pixmap(dpi=150)
                thumb_pix = page.get_pixmap(dpi=60)

                img_filename = f"page_{page_num + 1:04d}.png"
                thumb_filename = f"thumb_{page_num + 1:04d}.png"
                img_path = pages_dir / img_filename
                thumb_path = pages_dir / thumb_filename

                pix.save(str(img_path))
                thumb_pix.save(str(thumb_path))

                work_item = WorkItem.objects.create(
                    batch=batch,
                    page_number=page_num + 1,
                    item_identifier=f"Page {page_num + 1}",
                    sequence=page_num + 1,
                    status="NEW",
                    page_preview=str(img_path),
                    page_thumbnail=str(thumb_path),
                    extracted_data=json.dumps({
                        "page_number": page_num + 1,
                        "image_width": pix.width,
                        "image_height": pix.height,
                        "file_size": os.path.getsize(img_path),
                    }),
                )

                WorkTimeline.objects.create(
                    work_item=work_item,
                    action="CREATED",
                    description=f"Page {page_num + 1} extracted from PDF",
                    performed_by=uploaded_by,
                    timestamp=timezone.now(),
                    is_system_generated=True,
                )

                WorkItemStatus.objects.create(
                    work_item=work_item,
                    status="NEW",
                    changed_by=uploaded_by,
                    changed_at=timezone.now(),
                    from_status="",
                    notes="Work item created from PDF page",
                    is_system=True,
                )

        doc.close()

        batch.total_records = total_pages
        batch.status = "COMPLETED"
        batch.processed_at = timezone.now()
        batch.save(update_fields=["total_records", "status", "processed_at"])

    except Exception as e:
        batch.status = "FAILED"
        batch.error_log = str(e)
        batch.processed_at = timezone.now()
        batch.save(update_fields=["status", "error_log", "processed_at"])

    return batch


def get_page_preview_url(work_item):
    """Return the URL path for a work item's page preview."""
    if not work_item.page_preview:
        return None
    rel = os.path.relpath(work_item.page_preview, str(settings.MEDIA_ROOT))
    return f"{settings.MEDIA_URL}{rel.replace(os.sep, '/')}"


def get_page_thumbnail_url(work_item):
    """Return the URL path for a work item's page thumbnail."""
    path = work_item.page_thumbnail or work_item.page_preview
    if not path:
        return None
    rel = os.path.relpath(path, str(settings.MEDIA_ROOT))
    return f"{settings.MEDIA_URL}{rel.replace(os.sep, '/')}"


def process_image_upload(uploaded_files, bank_source, uploaded_by, notes=""):
    """Upload multiple images, create one WorkItem per image with previews.

    Returns the UploadBatch instance.
    """
    batch = UploadBatch.objects.create(
        bank_source=bank_source,
        upload_type="IMAGE",
        status="PROCESSING",
        original_filename=", ".join(f.name for f in uploaded_files[:5]),
        uploaded_by=uploaded_by,
        notes=notes,
    )

    batch_dir = IMAGE_STORAGE / str(batch.id)
    originals_dir = batch_dir / "originals"
    previews_dir = batch_dir / "previews"
    thumbs_dir = batch_dir / "thumbs"
    originals_dir.mkdir(parents=True, exist_ok=True)
    previews_dir.mkdir(parents=True, exist_ok=True)
    thumbs_dir.mkdir(parents=True, exist_ok=True)

    success_count = 0
    errors = []

    with transaction.atomic():
        for idx, f in enumerate(uploaded_files):
            try:
                ext = os.path.splitext(f.name)[1] or ".jpg"
                original_path = originals_dir / f"{idx + 1:04d}{ext}"
                with open(original_path, "wb") as dest:
                    for chunk in f.chunks():
                        dest.write(chunk)

                img = Image.open(original_path)
                img = ImageOps.exif_transpose(img) or img

                orig_w, orig_h = img.size

                # Generate preview (max 1920px on longest side)
                preview = _resize_image(img, 1920)
                preview_path = previews_dir / f"{idx + 1:04d}.jpg"
                preview.save(preview_path, "JPEG", quality=85)

                # Generate thumbnail (max 300px on longest side)
                thumb = _resize_image(img, 300)
                thumb_path = thumbs_dir / f"{idx + 1:04d}.jpg"
                thumb.save(thumb_path, "JPEG", quality=75)

                img.close()

                work_item = WorkItem.objects.create(
                    batch=batch,
                    item_identifier=f.name,
                    sequence=idx + 1,
                    status="NEW",
                    image_original=str(original_path),
                    image_preview=str(preview_path),
                    image_thumbnail=str(thumb_path),
                    extracted_data=json.dumps({
                        "original_filename": f.name,
                        "original_width": orig_w,
                        "original_height": orig_h,
                        "file_size": os.path.getsize(original_path),
                    }),
                )

                WorkTimeline.objects.create(
                    work_item=work_item,
                    action="CREATED",
                    description=f"Image uploaded: {f.name}",
                    performed_by=uploaded_by,
                    timestamp=timezone.now(),
                    is_system_generated=True,
                )

                WorkItemStatus.objects.create(
                    work_item=work_item,
                    status="NEW",
                    changed_by=uploaded_by,
                    changed_at=timezone.now(),
                    from_status="",
                    notes="Work item created from image upload",
                    is_system=True,
                )

                success_count += 1

            except Exception as e:
                errors.append(f"{f.name}: {e}")

    batch.total_records = success_count
    batch.status = "COMPLETED" if not errors else "PARTIAL"
    batch.processed_at = timezone.now()
    if errors:
        batch.error_log = "\n".join(errors)
    batch.save(update_fields=["total_records", "status", "processed_at", "error_log"])

    return batch


def _resize_image(img, max_dim):
    """Resize image maintaining aspect ratio so longest side <= max_dim."""
    img = img.convert("RGB")
    w, h = img.size
    if w <= max_dim and h <= max_dim:
        return img
    if w >= h:
        new_w = max_dim
        new_h = int(h * max_dim / w)
    else:
        new_h = max_dim
        new_w = int(w * max_dim / h)
    return img.resize((new_w, new_h), Image.LANCZOS)


def get_image_preview_url(work_item):
    """Return URL for a work item's image preview."""
    path = work_item.image_preview or work_item.image_original
    if not path:
        return None
    rel = os.path.relpath(path, str(settings.MEDIA_ROOT))
    return f"{settings.MEDIA_URL}{rel.replace(os.sep, '/')}"


def get_image_thumbnail_url(work_item):
    """Return URL for a work item's image thumbnail."""
    path = work_item.image_thumbnail or work_item.image_preview
    if not path:
        return None
    rel = os.path.relpath(path, str(settings.MEDIA_ROOT))
    return f"{settings.MEDIA_URL}{rel.replace(os.sep, '/')}"


def process_excel_upload(uploaded_file, bank_source, uploaded_by, notes=""):
    """Upload an XLSX file, create one WorkItem per row with original data.

    Returns the UploadBatch instance.
    """
    batch = UploadBatch.objects.create(
        bank_source=bank_source,
        upload_type="EXCEL",
        status="PROCESSING",
        original_filename=uploaded_file.name,
        file_size=uploaded_file.size,
        uploaded_by=uploaded_by,
        notes=notes,
    )

    batch_dir = EXCEL_STORAGE / str(batch.id)
    batch_dir.mkdir(parents=True, exist_ok=True)
    file_path = batch_dir / "original.xlsx"
    with open(file_path, "wb") as f:
        for chunk in uploaded_file.chunks():
            f.write(chunk)
    batch.file_path = str(file_path)
    batch.save(update_fields=["file_path"])

    errors = []
    success_count = 0

    try:
        df = pd.read_excel(file_path, dtype=str)
        df = df.dropna(how="all").reset_index(drop=True)
        total_rows = len(df)

        if total_rows == 0:
            batch.status = "COMPLETED"
            batch.total_records = 0
            batch.processed_at = timezone.now()
            batch.save(update_fields=["status", "total_records", "processed_at"])
            return batch

        with transaction.atomic():
            headers = list(df.columns)
            for idx, (_, row) in enumerate(df.iterrows()):
                row_data = {}
                for col in headers:
                    val = row.get(col)
                    if pd.isna(val):
                        val = ""
                    row_data[col] = str(val)

                identifier = row_data.get(headers[0]) if headers else ""
                if not identifier or identifier == "nan":
                    identifier = f"Row {idx + 2}"

                work_item = WorkItem.objects.create(
                    batch=batch,
                    item_identifier=str(identifier),
                    sequence=idx + 1,
                    status="NEW",
                    extracted_data=json.dumps(row_data),
                )

                WorkTimeline.objects.create(
                    work_item=work_item,
                    action="CREATED",
                    description=f"Row {idx + 2} extracted from Excel",
                    performed_by=uploaded_by,
                    timestamp=timezone.now(),
                    is_system_generated=True,
                )

                WorkItemStatus.objects.create(
                    work_item=work_item,
                    status="NEW",
                    changed_by=uploaded_by,
                    changed_at=timezone.now(),
                    from_status="",
                    notes="Work item created from Excel upload",
                    is_system=True,
                )

                success_count += 1

        batch.total_records = success_count
        batch.status = "COMPLETED" if not errors else "PARTIAL"
        batch.processed_at = timezone.now()
        if errors:
            batch.error_log = "\n".join(errors)
        batch.save(update_fields=["total_records", "status", "processed_at", "error_log"])

    except Exception as e:
        batch.status = "FAILED"
        batch.error_log = str(e)
        batch.processed_at = timezone.now()
        batch.save(update_fields=["status", "error_log", "processed_at"])

    return batch
