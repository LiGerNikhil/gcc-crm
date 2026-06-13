import os
import uuid
from datetime import datetime

import fitz
from django.conf import settings
from django.utils import timezone
from django.db import transaction

from .models import PDFImport, PDFPage
from leads.models import Batch, Campaign


def process_pdf(pdf_import_id):
    try:
        pdf_import = PDFImport.objects.select_related("batch", "created_by").get(
            id=pdf_import_id
        )
    except PDFImport.DoesNotExist:
        return

    pdf_import.extraction_status = "PROCESSING"
    pdf_import.save(update_fields=["extraction_status"])
    batch = pdf_import.batch
    batch.import_status = "PROCESSING"
    batch.save(update_fields=["import_status"])

    file_path = pdf_import.file_path
    try:
        doc = fitz.open(file_path)
        total_pages = len(doc)
        pdf_import.pages_count = total_pages
        pdf_import.save(update_fields=["pages_count"])

        pages_dir = settings.MEDIA_ROOT / "pdf_pages" / str(pdf_import.id)
        pages_dir.mkdir(parents=True, exist_ok=True)

        with transaction.atomic():
            for page_num in range(total_pages):
                page = doc[page_num]
                pix = page.get_pixmap(dpi=150)
                img_filename = f"page_{page_num + 1:04d}.png"
                thumb_filename = f"thumb_{page_num + 1:04d}.png"
                img_path = pages_dir / img_filename
                thumb_path = pages_dir / thumb_filename

                pix.save(str(img_path))

                thumb_pix = page.get_pixmap(dpi=60)
                thumb_pix.save(str(thumb_path))

                PDFPage.objects.create(
                    pdf_import=pdf_import,
                    page_number=page_num + 1,
                    image_path=str(img_path),
                    thumbnail_path=str(thumb_path),
                    width=pix.width,
                    height=pix.height,
                    file_size=os.path.getsize(img_path),
                )

        doc.close()

        pdf_import.extraction_status = "COMPLETED"
        pdf_import.processed_at = timezone.now()
        pdf_import.save(update_fields=["extraction_status", "processed_at"])

        batch.import_status = "COMPLETED"
        batch.processed_date = timezone.now()
        batch.processed_by = pdf_import.created_by
        batch.save(update_fields=["import_status", "processed_date", "processed_by"])

    except Exception as e:
        pdf_import.extraction_status = "FAILED"
        pdf_import.error_message = str(e)
        pdf_import.processed_at = timezone.now()
        pdf_import.save(update_fields=["extraction_status", "error_message", "processed_at"])

        batch.import_status = "FAILED"
        batch.error_log = str(e)
        batch.processed_date = timezone.now()
        batch.save(update_fields=["import_status", "error_log", "processed_date"])


def upload_and_process(uploaded_file, campaign_id, created_by):
    upload_dir = settings.MEDIA_ROOT / "uploads" / "pdf"
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.pdf"
    file_path = upload_dir / filename
    with open(file_path, "wb") as f:
        for chunk in uploaded_file.chunks():
            f.write(chunk)

    campaign = Campaign.objects.get(id=campaign_id)
    batch_number = f"B-PDF-{datetime.now():%Y%m%d-%s}"[:50]
    batch = Batch.objects.create(
        campaign=campaign,
        batch_number=batch_number,
        source_file_path=str(file_path),
        file_type="PDF",
        import_status="PENDING",
        uploaded_by=created_by,
    )

    pdf_import = PDFImport.objects.create(
        batch=batch,
        file_path=str(file_path),
        file_name=uploaded_file.name,
        file_size=uploaded_file.size,
        extraction_status="PENDING",
        created_by=created_by,
    )

    process_pdf(pdf_import.id)

    return pdf_import


def get_page_image_url(pdf_import, page_number):
    try:
        page = PDFPage.objects.get(pdf_import=pdf_import, page_number=page_number)
        return page.image_path
    except PDFPage.DoesNotExist:
        return None


def get_page_thumbnail_url(pdf_import, page_number):
    try:
        page = PDFPage.objects.get(pdf_import=pdf_import, page_number=page_number)
        return page.thumbnail_path or page.image_path
    except PDFPage.DoesNotExist:
        return None
