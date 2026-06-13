from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from leads.models import Lead, LeadCall, FollowUp, LeadStatusLog, Campaign


def get_source_wise_stats():
    """Leads grouped by bank source (HDFC, ICICI, Axis, Tata, Other)."""
    from django.db.models import Case, When, Value, CharField

    rows = (
        Lead.objects.filter(is_deleted=False)
        .values("batch__campaign__bank_source__source_code")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    total = sum(r["count"] for r in rows)
    data = {r["batch__campaign__bank_source__source_code"]: r["count"] for r in rows if r["batch__campaign__bank_source__source_code"]}
    return {
        "labels": [k for k in data],
        "values": [v for v in data.values()],
        "total": total,
        "raw": data,
        "items": [{"label": k, "count": v} for k, v in data.items()],
    }


def get_lead_metrics():
    """Lead funnel counts: total, assigned, interested, approved, disbursed."""
    qs = Lead.objects.filter(is_deleted=False)
    total = qs.count()
    assigned = qs.filter(lead_status="ASSIGNED").count()
    interested = qs.filter(lead_status="INTERESTED").count()
    approved = qs.filter(lead_status="APPROVED").count()
    disbursed = qs.filter(lead_status="DISBURSED").count()
    return {
        "total": total,
        "assigned": assigned,
        "interested": interested,
        "approved": approved,
        "disbursed": disbursed,
        "labels": ["Total Leads", "Assigned", "Interested", "Approved", "Disbursed"],
        "values": [total, assigned, interested, approved, disbursed],
    }


def get_employee_metrics():
    """Per-employee: call count, follow-up count, conversion count (leads that reached APPROVED/DISBURSED)."""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    today = timezone.now().date()
    employees = User.objects.filter(is_active=True, profile__role__role_code="CALLER").annotate(
        call_count=Count(
            "lead_calls_made",
            filter=Q(lead_calls_made__call_time__date=today),
        ),
        followup_count=Count(
            "lead_followups_created",
            filter=Q(lead_followups_created__created_at__date=today),
        ),
        conversion_count=Count(
            "lead_status_changes",
            filter=Q(
                lead_status_changes__new_status__in=["APPROVED", "DISBURSED"],
                lead_status_changes__created_at__date=today,
            ),
        ),
    ).values("id", "username", "first_name", "last_name", "call_count", "followup_count", "conversion_count")

    data = list(employees)
    return {
        "employees": [
            {
                "name": f"{e['first_name'] or ''} {e['last_name'] or ''}".strip() or e["username"],
                "calls": e["call_count"],
                "followups": e["followup_count"],
                "conversions": e["conversion_count"],
            }
            for e in data
        ],
        "labels": [
            f"{e['first_name'] or ''} {e['last_name'] or ''}".strip() or e["username"]
            for e in data
        ],
        "calls": [e["call_count"] for e in data],
        "followups": [e["followup_count"] for e in data],
        "conversions": [e["conversion_count"] for e in data],
    }


def get_lead_status_distribution():
    """All statuses with counts for pie/doughnut chart."""
    qs = Lead.objects.filter(is_deleted=False)
    statuses = [s[0] for s in Lead.LEAD_STATUS_CHOICES]
    counts = {s: 0 for s in statuses}
    for row in qs.values("lead_status").annotate(count=Count("id")):
        counts[row["lead_status"]] = row["count"]
    return {
        "labels": [s for s in statuses if counts[s] > 0],
        "values": [counts[s] for s in statuses if counts[s] > 0],
        "raw": counts,
    }


def get_monthly_trends(months=6):
    """Monthly lead creation count for the last N months."""
    from django.db.models.functions import TruncMonth
    from datetime import date
    from dateutil.relativedelta import relativedelta

    cutoff = date.today() - relativedelta(months=months - 1)
    cutoff = timezone.make_aware(timezone.datetime(cutoff.year, cutoff.month, 1))

    rows = (
        Lead.objects.filter(is_deleted=False, created_at__gte=cutoff)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )
    return {
        "labels": [r["month"].strftime("%b %Y") if r["month"] else "N/A" for r in rows],
        "values": [r["count"] for r in rows],
    }


def get_dashboard_kpi():
    today = timezone.now().date()
    qs = Lead.objects.filter(is_deleted=False)
    return {
        "total_leads": qs.count(),
        "leads_today": qs.filter(created_at__date=today).count(),
        "active_campaigns": Campaign.objects.filter(status="ACTIVE").count(),
        "pending_followups": FollowUp.objects.filter(status="PENDING").count(),
        "interested_leads": qs.filter(lead_status="INTERESTED").count(),
        "approved_leads": qs.filter(lead_status="APPROVED").count(),
        "disbursed_leads": qs.filter(lead_status="DISBURSED").count(),
    }


def get_daily_leads(days=30):
    from datetime import date, timedelta
    today = date.today()
    start = today - timedelta(days=days - 1)
    rows = (
        Lead.objects.filter(is_deleted=False, created_at__date__gte=start)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    raw = {r["day"]: r["count"] for r in rows}
    labels, values = [], []
    for i in range(days):
        d = start + timedelta(days=i)
        labels.append(d.strftime("%d %b"))
        values.append(raw.get(d, 0))
    return {"labels": labels, "values": values}
