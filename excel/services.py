import os
import json
import uuid
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation

import pandas as pd
from django.utils import timezone
from django.db import transaction
from django.conf import settings

from .models import ExcelImport, ExcelImportLog
from leads.models import Batch, Lead, Campaign

FIELD_MAPPING = {
    "customer_name": [
        "customer name", "name", "full name", "customer", "borrower name",
        "applicant name", "client name",
    ],
    "phone": [
        "phone", "mobile", "phone number", "mobile number", "contact",
        "contact number", "telephone", "phone_no", "telephone number",
    ],
    "email": [
        "email", "email id", "email address", "e-mail", "mail",
    ],
    "pan_number": [
        "pan", "pan number", "pan no", "pan card", "pan_no",
    ],
    "loan_amount": [
        "loan amount", "amount", "sanctioned amount", "loan_amt",
        "requested amount", "finance amount", "loan",
    ],
    "loan_type": [
        "loan type", "type", "loan category", "product", "loan product",
    ],
    "property_value": [
        "property value", "property cost", "property valuation",
        "estimated value",
    ],
    "employment_type": [
        "employment type", "employment", "occupation", "profession",
        "employment_status",
    ],
    "address": [
        "address", "residence address", "current address", "postal address",
    ],
    "city": [
        "city", "town", "location",
    ],
    "state": [
        "state", "province",
    ],
    "pincode": [
        "pincode", "pin code", "pin", "zip", "zip code", "postal code",
    ],
    "lead_source_id": [
        "lead source id", "source id", "external id", "reference id",
        "lead_id", "source_id",
    ],
}

REQUIRED_FIELDS = ["customer_name", "phone"]

LOAN_TYPE_MAP = {
    "home": "HOME", "home loan": "HOME", "housing": "HOME",
    "personal": "PERSONAL", "personal loan": "PERSONAL",
    "business": "BUSINESS", "business loan": "BUSINESS", "biz": "BUSINESS",
    "auto": "AUTO", "car": "AUTO", "vehicle": "AUTO", "auto loan": "AUTO",
    "education": "EDUCATION", "education loan": "EDUCATION", "student": "EDUCATION",
    "gold": "GOLD", "gold loan": "GOLD",
}

EMPLOYMENT_MAP = {
    "salaried": "SALARIED", "employed": "SALARIED",
    "self employed": "SELF_EMPLOYED", "self-employed": "SELF_EMPLOYED", "self_employed": "SELF_EMPLOYED",
    "business": "BUSINESS", "business owner": "BUSINESS",
    "agriculture": "AGRICULTURE", "farmer": "AGRICULTURE",
    "unemployed": "UNEMPLOYED",
    "retired": "RETIRED",
}


def _normalize_column(name):
    return name.strip().lower().replace("_", " ")


def resolve_column_mapping(df_columns):
    normalized_cols = {_normalize_column(c): c for c in df_columns}
    mapping = {}
    for field, aliases in FIELD_MAPPING.items():
        for alias in aliases:
            if alias in normalized_cols:
                mapping[field] = normalized_cols[alias]
                break
    return mapping


def validate_required_columns(mapping):
    missing = []
    for field in REQUIRED_FIELDS:
        if field not in mapping:
            aliases = FIELD_MAPPING[field]
            missing.append(f"{field} (expected columns: {', '.join(aliases[:3])}...)")
    return missing


def parse_uploaded_file(file_path, sheet_name=0, header_row=0):
    ext = os.path.splitext(file_path)[1].lower()
    if ext in (".xlsx", ".xls"):
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row, dtype=str)
    elif ext == ".csv":
        df = pd.read_csv(file_path, header=header_row, dtype=str, encoding="utf-8")
        if df.shape[1] <= 1:
            df = pd.read_csv(file_path, header=header_row, dtype=str, encoding="latin1")
    else:
        raise ValueError(f"Unsupported file type: {ext}")
    df = df.dropna(how="all").reset_index(drop=True)
    return df


def _clean_value(val):
    if pd.isna(val):
        return ""
    val = str(val).strip()
    return val


def _parse_amount(val):
    if not val:
        return None
    cleaned = val.replace(",", "").replace("₹", "").replace("Rs", "").replace(" ", "")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _detect_duplicates(phone, email, pan, exclude_id=None):
    from django.db.models import Q
    queries = Q()
    if phone:
        queries |= Q(phone=phone)
    if email:
        queries |= Q(email=email)
    if pan:
        queries |= Q(pan_number=pan)
    if not queries:
        return []
    qs = Lead.objects.filter(queries, is_deleted=False)
    if exclude_id:
        qs = qs.exclude(id=exclude_id)
    return list(qs.values("id", "customer_name", "phone", "email", "pan_number"))


def process_import(excel_import_id):
    try:
        excel_import = ExcelImport.objects.select_related("batch", "created_by").get(
            id=excel_import_id
        )
    except ExcelImport.DoesNotExist:
        return

    excel_import.status = "PROCESSING"
    excel_import.save(update_fields=["status"])
    batch = excel_import.batch
    batch.import_status = "PROCESSING"
    batch.save(update_fields=["import_status"])

    file_path = excel_import.file_path
    errors = []
    success_count = 0
    failed_count = 0

    try:
        df = parse_uploaded_file(file_path)
        total_rows = len(df)
        excel_import.total_rows = total_rows
        excel_import.save(update_fields=["total_rows"])

        mapping = resolve_column_mapping(df.columns.tolist())
        missing = validate_required_columns(mapping)
        if missing:
            error_msg = f"Missing required columns: {', '.join(missing)}"
            _fail_import(excel_import, batch, error_msg)
            return

        with transaction.atomic():
            for idx, row in df.iterrows():
                row_num = idx + 2
                raw = row.to_dict()
                try:
                    lead_data = _build_lead_data(row, mapping)
                    if not lead_data.get("customer_name") or not lead_data.get("phone"):
                        ExcelImportLog.objects.create(
                            excel_import=excel_import,
                            row_number=row_num,
                            status="FAILED",
                            error_message="Missing customer_name or phone",
                            raw_data=json.dumps(raw, default=str),
                        )
                        failed_count += 1
                        continue

                    duplicates = _detect_duplicates(
                        lead_data.get("phone"),
                        lead_data.get("email"),
                        lead_data.get("pan_number"),
                    )
                    if duplicates:
                        ExcelImportLog.objects.create(
                            excel_import=excel_import,
                            row_number=row_num,
                            status="SKIPPED",
                            error_message=f"Duplicate detected: {', '.join([d['customer_name'] for d in duplicates])}",
                            raw_data=json.dumps(raw, default=str),
                        )
                        failed_count += 1
                        continue

                    lead = Lead.objects.create(
                        batch=batch,
                        lead_number=_generate_lead_number(batch),
                        customer_name=lead_data["customer_name"],
                        phone=lead_data["phone"],
                        email=lead_data.get("email", ""),
                        pan_number=lead_data.get("pan_number", ""),
                        loan_amount=_parse_amount(lead_data.get("loan_amount")),
                        loan_type=_resolve_loan_type(lead_data.get("loan_type", "")),
                        property_value=_parse_amount(lead_data.get("property_value")),
                        employment_type=_resolve_employment_type(lead_data.get("employment_type", "")),
                        address=lead_data.get("address", ""),
                        city=lead_data.get("city", ""),
                        state=lead_data.get("state", ""),
                        pincode=lead_data.get("pincode", ""),
                        lead_source_id=lead_data.get("lead_source_id", ""),
                    )
                    ExcelImportLog.objects.create(
                        excel_import=excel_import,
                        row_number=row_num,
                        status="SUCCESS",
                        raw_data=json.dumps(raw, default=str),
                        created_lead_id=str(lead.id),
                    )
                    success_count += 1

                except Exception as e:
                    ExcelImportLog.objects.create(
                        excel_import=excel_import,
                        row_number=row_num,
                        status="FAILED",
                        error_message=str(e),
                        raw_data=json.dumps(raw, default=str),
                    )
                    failed_count += 1

        excel_import.status = "COMPLETED"
        excel_import.successful_rows = success_count
        excel_import.failed_rows = failed_count
        excel_import.processed_at = timezone.now()
        excel_import.save(update_fields=[
            "status", "successful_rows", "failed_rows", "processed_at"
        ])

        batch.import_status = "COMPLETED"
        batch.total_records = total_rows
        batch.processed_records = success_count
        batch.failed_records = failed_count
        batch.processed_date = timezone.now()
        batch.processed_by = excel_import.created_by
        batch.save(update_fields=[
            "import_status", "total_records", "processed_records",
            "failed_records", "processed_date", "processed_by",
        ])

    except Exception as e:
        _fail_import(excel_import, batch, str(e))


def _fail_import(excel_import, batch, error_msg):
    excel_import.status = "FAILED"
    excel_import.error_log = error_msg
    excel_import.processed_at = timezone.now()
    excel_import.save(update_fields=["status", "error_log", "processed_at"])
    batch.import_status = "FAILED"
    batch.error_log = error_msg
    batch.processed_date = timezone.now()
    batch.save(update_fields=["import_status", "error_log", "processed_date"])


def _build_lead_data(row, mapping):
    data = {}
    for field, col in mapping.items():
        data[field] = _clean_value(row.get(col, ""))
    return data


def _resolve_loan_type(val):
    if not val:
        return ""
    key = val.strip().lower()
    for k, v in LOAN_TYPE_MAP.items():
        if k in key:
            return v
    return "OTHER"


def _resolve_employment_type(val):
    if not val:
        return ""
    key = val.strip().lower()
    for k, v in EMPLOYMENT_MAP.items():
        if k in key:
            return v
    return "OTHER"


def _generate_lead_number(batch):
    count = batch.leads.count() + 1
    short_id = str(batch.id)[:8]
    return f"L-{short_id}-{count:04d}"


def preview_import(file_path, sheet_name=0, header_row=0, max_rows=50):
    df = parse_uploaded_file(file_path, sheet_name, header_row)
    df = df.head(max_rows)
    columns = df.columns.tolist()
    mapping = resolve_column_mapping(columns)
    missing = validate_required_columns(mapping)
    rows = df.fillna("").to_dict(orient="records")
    return {
        "columns": columns,
        "total_rows": len(df),
        "mapping": {k: v for k, v in mapping.items()},
        "missing_required": missing,
        "rows": rows,
    }


def import_from_upload(uploaded_file, campaign_id, batch_name, created_by, sheet_name=0, header_row=0):
    upload_dir = settings.MEDIA_ROOT / "uploads" / "excel"
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = upload_dir / filename
    with open(file_path, "wb") as f:
        for chunk in uploaded_file.chunks():
            f.write(chunk)

    campaign = Campaign.objects.get(id=campaign_id)
    batch_number = f"B-{datetime.now():%Y%m%d-%s}"[:50]
    batch = Batch.objects.create(
        campaign=campaign,
        batch_number=batch_number,
        source_file_path=str(file_path),
        file_type="EXCEL" if ext in (".xlsx", ".xls") else "CSV",
        import_status="PENDING",
        uploaded_by=created_by,
        total_records=0,
        processed_records=0,
        failed_records=0,
    )

    excel_import = ExcelImport.objects.create(
        batch=batch,
        file_path=str(file_path),
        file_name=uploaded_file.name,
        file_size=uploaded_file.size,
        status="PENDING",
        created_by=created_by,
    )
    return excel_import
