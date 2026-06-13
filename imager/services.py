import os
import json
import uuid
from io import BytesIO
from PIL import Image, ImageOps
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils import timezone


THUMB_MAX_SIZE = (300, 300)
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
MAX_FILE_SIZE = 20 * 1024 * 1024


def _get_upload_path(instance_id, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"images/{instance_id}{ext}"


def _get_thumb_path(instance_id, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"images/thumbs/{instance_id}{ext}"


def process_uploaded_image(uploaded_file, uploaded_by):
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file format: {ext}")
    if uploaded_file.size > MAX_FILE_SIZE:
        raise ValueError("File size exceeds 20MB limit")

    instance_id = str(uuid.uuid4())
    file_path = _get_upload_path(instance_id, uploaded_file.name)
    thumb_path = _get_thumb_path(instance_id, uploaded_file.name)

    saved_path = default_storage.save(file_path, uploaded_file)
    abs_path = os.path.join(settings.MEDIA_ROOT, saved_path)

    img = Image.open(abs_path)
    width, height = img.size
    file_size = os.path.getsize(abs_path)
    image_format = img.format.upper() if img.format else ext.lstrip(".").upper()
    if image_format == "JPEG":
        image_format = "JPG"

    img.thumbnail(THUMB_MAX_SIZE, Image.LANCZOS)
    thumb_buf = BytesIO()
    save_format = "JPEG" if image_format == "JPG" else image_format
    if save_format == "GIF":
        img.save(thumb_buf, format=save_format)
    else:
        img.save(thumb_buf, format=save_format, quality=85)
    thumb_buf.seek(0)
    default_storage.save(thumb_path, ContentFile(thumb_buf.read()))
    img.close()

    from .models import ImageUpload

    image = ImageUpload.objects.create(
        id=instance_id,
        file_path=saved_path,
        thumbnail_path=thumb_path,
        file_name=uploaded_file.name,
        image_format=image_format,
        image_type="OTHER",
        file_size=file_size,
        width=width,
        height=height,
        uploaded_by=uploaded_by,
    )
    return image


def rotate_image(image, degrees=90):
    abs_path = os.path.join(settings.MEDIA_ROOT, image.file_path)
    if not os.path.exists(abs_path):
        return None
    img = Image.open(abs_path)
    rotated = img.rotate(degrees, expand=True, resample=Image.BICUBIC)
    buf = BytesIO()
    save_format = "JPEG" if image.image_format == "JPG" else image.image_format
    if save_format in ("PNG", "WEBP", "GIF"):
        rotated.save(buf, format=save_format)
    else:
        rotated.save(buf, format=save_format, quality=95)
    buf.seek(0)
    new_path = image.file_path
    default_storage.delete(new_path)
    default_storage.save(new_path, ContentFile(buf.read()))
    rotated.close()
    img.close()

    img2 = Image.open(abs_path)
    image.width, image.height = img2.size
    img2.close()
    image.save(update_fields=["width", "height"])
    return image


def create_batch_from_images(images, name, created_by, campaign=None, description=""):
    from .models import ImageBatch

    batch = ImageBatch.objects.create(
        name=name,
        description=description,
        campaign=campaign,
        created_by=created_by,
        total_images=images.count(),
    )
    images.update(batch=batch)
    return batch


def assign_images_to_lead(image_ids, lead, user):
    from .models import ImageUpload

    updated = ImageUpload.objects.filter(id__in=image_ids).update(lead=lead)
    return updated


def bulk_assign_images(image_ids, lead_id, user):
    from leads.models import Lead
    from .models import ImageUpload

    lead = Lead.objects.get(id=lead_id)
    updated = ImageUpload.objects.filter(id__in=image_ids).update(lead=lead)
    return updated, lead
