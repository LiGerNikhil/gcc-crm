# Enterprise Security & Architecture Audit

Generated: 2026-06-11
Scope: Full CRM codebase (accounts, leads, excel, pdf, imager, analytics, audit, activities)

---

## 1. SECURITY IMPROVEMENTS

### CRITICAL — `crm/settings.py:25`
**`SECRET_KEY` hardcoded in version control.**
```python
SECRET_KEY = 'django-insecure-_9#ff(3gao%7s7zb*0wu=in_-hs#qi=58e-f*few!c*_%v&i)='
```
**Fix:** Load from environment variable.
```python
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']
```

### CRITICAL — `crm/settings.py:27`
**`DEBUG = True` in what appears to be a shared/production-adjacent settings file.**
```python
DEBUG = True
```
**Fix:** 
```python
DEBUG = os.environ.get('DJANGO_DEBUG', 'False') == 'True'
```

### CRITICAL — `crm/settings.py:29`
**`ALLOWED_HOSTS = []` — no hosts configured.**
```python
ALLOWED_HOSTS = []
```
**Fix:**
```python
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',')
```

### HIGH — Missing HTTPS security settings
Add to `crm/settings.py`:
```python
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
```

### HIGH — No CORS configuration
`django-cors-headers` is in `requirements.txt` but not configured in settings.
Add to `crm/settings.py`:
```python
CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',')
CORS_ALLOW_CREDENTIALS = True
CORS_EXPOSE_HEADERS = ['Content-Type', 'X-Total-Count']
```

### HIGH — `audit/middleware.py` — No user-agent length validation
`get_user_agent()` in `audit/services.py:60` truncates to 255 chars but this happens after the string is already in memory. DOS vector via massive User-Agent headers.
```python
def get_user_agent(request):
    raw = request.META.get('HTTP_USER_AGENT', '')
    return raw[:255]
```
**Fix:** No change needed for truncation logic; ensure web server (nginx) limits header size upstream.

### HIGH — `leads/views.py:97` — `LeadDetailView` has no queryset restriction per role
```python
def get_queryset(self):
    return Lead.objects.filter(is_deleted=False).select_related(
        "assigned_to", "batch__campaign__bank_source"
    )
```
A CALLER can view ANY lead's detail page by guessing the UUID. **Fix:**
```python
def get_queryset(self):
    qs = Lead.objects.filter(is_deleted=False).select_related(...)
    role = _get_role(self.request.user)
    if role == "CALLER":
        qs = qs.filter(assigned_to=self.request.user)
    return qs
```

### HIGH — `leads/views.py:106-123` — `LeadDetailView.get_context_data` passes ALL related objects
Every related object set is loaded without pagination or limits for CALLER users:
```python
ctx["notes"] = lead.lead_notes.select_related("created_by").all()
ctx["followups"] = lead.lead_followups.select_related("assigned_to", "created_by").all()
```
No check that the current user is the assigned caller.

### MEDIUM — File upload validation
- `excel/api_views.py:33-37` checks extension client-side only (`file.name.split`). Malicious files can bypass.
- `imager/services.py` — no virus scanning or MIME type validation beyond Pillow's load.
**Fix:** Use `python-magic` to validate MIME type server-side. Integrate ClamAV for production.

### MEDIUM — No rate limiting
Login endpoint has no throttling. Add to `REST_FRAMEWORK`:
```python
'DEFAULT_THROTTLE_CLASSES': [
    'rest_framework.throttling.AnonRateThrottle',
    'rest_framework.throttling.UserRateThrottle',
],
'DEFAULT_THROTTLE_RATES': {
    'anon': '10/minute',
    'user': '1000/day',
    'login': '5/minute',
}
```
Apply `AnonRateThrottle` to `TokenObtainPairView`.

### MEDIUM — Session settings
```python
SESSION_EXPIRE_AT_BROWSER_CLOSE = False     # Should be True
SESSION_COOKIE_AGE = 86400                  # 24h — reasonable
SESSION_COOKIE_SAMESITE = 'Lax'  # Missing
CSRF_COOKIE_SAMESITE = 'Lax'  # Missing
```

### LOW — `accounts/views.py:46` — Logged-in username interpolated into message
```python
messages.success(request, _(f"Welcome back, {user.get_full_name() or user.username}!"))
```
Translating interpolated strings breaks i18n. Use `str.format()` with named placeholder or separate string.

### LOW — JWT `BLACKLIST_AFTER_ROTATION = True` but no `'rest_framework_simplejwt.token_blacklist'` in INSTALLED_APPS
Add to `INSTALLED_APPS`:
```python
'rest_framework_simplejwt.token_blacklist',
```
Then run `python manage.py migrate`.

---

## 2. PERMISSION VULNERABILITIES

### `accounts/permissions.py` vs `leads/permissions.py` — Duplicate code
`leads/permissions.py:1-40` is a line-for-line duplicate of `accounts/permissions.py`. The `leads/api_views.py` imports from `leads.permissions`. The `accounts.permissions` module should be the single source of truth.

**Fix:** Remove `leads/permissions.py`, update all imports in `leads/api_views.py`:
```python
from accounts.permissions import IsAdminOrTeamLead, IsCaller, IsAssignedOrAdmin
```

### `leads/views.py` — Template views lack granular object-level permissions
| View | Mixin | Vulnerability |
|---|---|---|
| `LeadDetailView` | `ActiveUserRequiredMixin` | Any active user sees any lead |
| `LeadUpdateView` | `ActiveUserRequiredMixin` | Any active user edits any lead |
| `LeadNoteCreateView` | `ActiveUserRequiredMixin` | Any user adds notes to any lead |
| `FollowUpCreateView` | `ActiveUserRequiredMixin` | Any user schedules follow-ups |

These should use the mixin chain correctly: CALLER sees only their leads, TEAM_LEAD sees team's leads.

### `leads/api_views.py:66` — `LeadViewSet.update_status` allows any CALLER to update ANY lead
```python
if self.action in ("update", "partial_update", "update_status"):
    return [IsAuthenticated(), IsCaller()]
```
No object-level check. A CALLER can POST to `/api/leads/{uuid}/update_status/` for any lead. **Fix:** Add `IsAssignedOrAdmin` or override `get_object()` to check assignment.

### `accounts/api_views.py:56` — `UserViewSet.toggle_active` — no secondary confirmation
```python
@action(detail=True, methods=["post"])
def toggle_active(self, request, pk=None):
    user = self.get_object()
    user.is_active = not user.is_active
    ...
```
A TEAM_LEAD can toggle any non-SUPER_ADMIN user (including themselves or other TEAM_LEADs). `get_permissions()` returns `[IsAdminOrTeamLead()]` but the queryset filtering in `get_queryset()` is not applied to `get_object()`. **Fix:** Override `get_object()` in `toggle_active` to prevent self-deactivation and cross-TEAM_LEAD deactivation.

### `accounts/api_views.py:130-140` — `UserProfileViewSet.get_queryset` exception silently passes
```python
except Exception:
    pass
```
If `role_code` lookup fails, the queryset is not filtered, exposing ALL profiles. **Fix:** Catch specific exceptions, or set `qs = qs.none()` in the except block.

### `accounts/permissions.py:46` — `IsSelfOrAdmin.has_object_permission` uses broad exception
```python
def _has_role(user, roles):
    try:
        role = user.profile.role.role_code
        ...
    except Exception:
        return False
```
Broad `except Exception` masks AttributeError, UserProfile.DoesNotExist, and Role.DoesNotExist. **Fix:** Catch `AttributeError` and `ObjectDoesNotExist` specifically.

---

## 3. QUERY OPTIMIZATION

### `analytics/services.py:142-162` — `get_dashboard_kpi()` runs 7 separate COUNT queries
Current: 7 queries (total_leads, leads_today, active_campaigns, pending_followups, interested_leads, approved_leads, disbursed_leads).

**Optimization:**
```python
def get_dashboard_kpi():
    today = timezone.now().date()
    from django.db.models import Count, Q
    base = Lead.objects.filter(is_deleted=False)
    agg = base.aggregate(
        total_leads=Count("id"),
        leads_today=Count("id", filter=Q(created_at__date=today)),
        interested_leads=Count("id", filter=Q(lead_status="INTERESTED")),
        approved_leads=Count("id", filter=Q(lead_status="APPROVED")),
        disbursed_leads=Count("id", filter=Q(lead_status="DISBURSED")),
    )
    agg["active_campaigns"] = Campaign.objects.filter(status="ACTIVE").count()
    agg["pending_followups"] = FollowUp.objects.filter(status="PENDING").count()
    return agg
```
Reduces leads DB queries from 5 → 1.

### `analytics/services.py:91-102` — `get_lead_status_distribution()` materializes all statuses in Python
Current: Fetches all leads with `.values("lead_status").annotate(count=Count("id"))`, then iterates to match status choices.

**Optimization:**
```python
def get_lead_status_distribution():
    from django.db.models import Case, When, Value, IntegerField
    qs = Lead.objects.filter(is_deleted=False)
    status_counts = dict(
        qs.values("lead_status")
        .annotate(count=Count("id"))
        .values_list("lead_status", "count")
    )
    labels, values = zip(*[(s, status_counts.get(s, 0)) for s, _ in Lead.LEAD_STATUS_CHOICES])
    return {"labels": labels, "values": values, "raw": status_counts}
```

### `leads/views.py:25-33` — `LeadListView` does 2 queries for the same filtered dataset
`get_queryset()` applies `LeadFilter`, then `get_context_data()` runs a SEPARATE unfiltered status_counts query. The filtered queryset should be used.

**Fix:**
```python
def get_context_data(self, **kwargs):
    ctx = super().get_context_data(**kwargs)
    filtered_qs = self.object_list  # Already filtered by get_queryset
    ctx["status_counts"] = (
        filtered_qs.values("lead_status")
        .annotate(count=Count("id"))
        .order_by("lead_status")
    )
    return ctx
```

### `leads/services.py:323-380` — `get_lead_timeline()` runs N+1 queries
Each section loads its own queryset: `status_logs.select_related("changed_by").all()` (1), `lead_notes.select_related("created_by").all()` (1), `lead_followups.select_related("assigned_to", "created_by").all()` (1), `get_assignment_history(lead=lead)` (1), `lead.calls.select_related("caller").all()` (1), and potentially `DocumentImage.objects.filter(lead=lead)` (1).

This is unavoidable with the ORM's multi-model aggregation, but each can be wrapped in a single query per model.

### `leads/views.py:88-89` — `LeadListView` status_counts query lacks `is_deleted=False`
```python
ctx["status_counts"] = (
    Lead.objects.filter(is_deleted=False)
    .values("lead_status")
    .annotate(count=Count("id"))
    .order_by("lead_status")
)
```
This is correct here but the filtered `get_queryset()` version is preferred to keep filters in sync.

### `accounts/views.py:182` — `UserListView.get_queryset()` loads profile eagerly but not role
```python
qs = User.objects.select_related("profile__role").all()
```
This IS correct (deep string syntax). Good.

### `analytics/services.py:6-24` — `get_source_wise_stats()` lacks null-source exclusion
```python
data = {r["batch__campaign__bank_source__source_code"]: r["count"]
        for r in rows if r["batch__campaign__bank_source__source_code"]}
```
Leads with null source_code are silently excluded post-query. Better to filter in SQL:
```python
rows = (
    Lead.objects.filter(
        is_deleted=False,
        batch__campaign__bank_source__source_code__isnull=False,
    )
    .values("batch__campaign__bank_source__source_code")
    .annotate(count=Count("id"))
    .order_by("-count")
)
```

### `leads/views.py:242-261` — `AssignmentHistoryView.get_queryset()` missing select_related
```python
qs = LeadAssignment.objects.select_related(
    "lead", "assigned_to", "assigned_by"
).all()
```
This IS correct. No issue.

### DRF Serializer N+1 — `LeadListSerializer` reads `assigned_to.get_full_name()` via SerializerMethodField
Every serialized lead calls `get_assigned_to_name()` which accesses `obj.assigned_to`. Since `get_queryset()` uses `.select_related("assigned_to")`, this is fine.

### `accounts/api_views.py:110-122` — `UserProfileViewSet` uses `select_related("user", "role", "manager")`
Already optimized. Good.

---

## 4. POSTGRESQL INDEXES

### Missing composite indexes for dashboard/analytics queries

| Query Pattern | Suggested Index |
|---|---|
| `WHERE is_deleted=False AND lead_status=X` | `(is_deleted, lead_status)` on `leads_lead` |
| `WHERE is_deleted=False AND created_at__date>=X` | `(is_deleted, created_at)` on `leads_lead` |
| `WHERE assigned_to=X AND is_deleted=False` | `(assigned_to, is_deleted)` on `leads_lead` |
| `WHERE assigned_to=X AND lead_status IN (...)` | `(assigned_to, lead_status)` on `leads_lead` |
| `WHERE FollowUp.status='PENDING'` | `(status, scheduled_at)` on `leads_follow_up` (use for pending follow-up queries) |
| `WHERE lead=X AND call_time DESC` | Existing `lcall_lead_time_idx` covers this |
| `WHERE status='ACTIVE'` on Campaign | Existing `campaign_status_idx` covers this |
| `WHERE AuditLog.model_name=X AND record_id=X` | Existing `audit_model_record_idx` covers this |

### Generate migration for new indexes:
```python
# leads/migrations/0005_add_composite_indexes.py
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("leads", "0004_add_lead_call_model")]

    operations = [
        migrations.AddIndex(
            model_name="lead",
            index=models.Index(
                fields=["is_deleted", "lead_status"],
                name="lead_del_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="lead",
            index=models.Index(
                fields=["is_deleted", "created_at"],
                name="lead_del_created_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="lead",
            index=models.Index(
                fields=["assigned_to", "is_deleted"],
                name="lead_assign_del_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="followup",
            index=models.Index(
                fields=["status", "scheduled_at"],
                name="lfup_status_sched_idx",
            ),
        ),
    ]
```

### Partial indexes (PostgreSQL-only):
```sql
CREATE INDEX lead_active_non_deleted_idx ON leads_lead (assigned_to, lead_status)
WHERE is_deleted = false;

CREATE INDEX lead_recent_30d_idx ON leads_lead (created_at)
WHERE is_deleted = false
  AND created_at >= NOW() - INTERVAL '30 days';
```

### Full-text search index for text columns:
```sql
CREATE INDEX lead_search_idx ON leads_lead
USING gin(to_tsvector('english', coalesce(customer_name,'') || ' ' || coalesce(lead_number,'') || ' ' || coalesce(phone,'')));
```

### Missing indexes on commonly filtered FK fields:
- `leads_lead.duplicate_of` — used in duplicate lookup queries
- `leads_lead.is_duplicate` — indexed but composite with `is_deleted` would be faster

---

## 5. CACHING STRATEGY

### Redis Configuration
```python
# crm/settings.py
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "PARSER_CLASS": "redis.connection.HiredisParser",
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
            "SERIALIZER": "django_redis.serializers.json.JSONSerializer",
        },
        "KEY_PREFIX": "crm",
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
```

### Cache Strategy by Endpoint

| Endpoint | TTL | Key Pattern | Strategy |
|---|---|---|---|
| Dashboard KPI | 5 min | `dash:kpi` | Invalidate on Lead create/update |
| Daily Leads | 1 hour | `dash:daily_leads:{days}` | Cron refresh |
| Source Stats | 1 hour | `dash:source_stats` | Cron refresh |
| Employee Metrics | 5 min | `dash:employee_metrics` | Invalidate on LeadAssignment |
| Lead Detail | 2 min | `lead:{id}:detail` | Invalidate on Lead save |
| Lead List (page 1) | 2 min | `lead:list:{query_params_hash}` | Invalidate on any Lead change |
| API Token blacklist | JWt expiry | JWT jti | Built into simplejwt |
| Analytics API responses | 1 hour | `analytics:{endpoint}:{params}` | Stale-while-revalidate |

### Implementation pattern for dashboard views:
```python
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie

class CachedDashboardView(DashboardView):
    @cache_page(300)  # 5 min
    @vary_on_cookie
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
```

For template fragment caching in `dashboard.html`:
```django
{% load cache %}
{% cache 300 dashboard_kpi user.id %}
    <!-- KPI Cards -->
{% endcache %}
```

### Cache invalidation signals:
```python
# leads/signals.py
from django.core.cache import cache

@receiver(post_save, sender=Lead)
def invalidate_dashboard_cache(sender, **kwargs):
    cache.delete_pattern("dash:*")
    cache.delete_pattern("lead:list:*")
    cache.delete_pattern("analytics:*")
```

---

## 6. CELERY STRATEGY

### Architecture

```
[Web Request] ──► [Celery Producer] ──► [Redis Broker]
                                             │
                                    [Celery Worker]
                                          │
                              ┌───────────┴───────────┐
                              │                       │
                         [PostgreSQL]           [File Storage]
```

### Worker Configuration
```python
# celery.py
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm.settings")
app = Celery("crm")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# crm/settings.py
CELERY_BROKER_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 min
CELERY_WORKER_MAX_TASKS_PER_CHILD = 200
CELERY_WORKER_SEND_TASKS_EVENTS = True
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60
```

### Task Inventory

| Task | Priority | Queue | Description |
|---|---|---|---|
| `process_excel_import` | HIGH | `imports` | Parse XLSX/CSV, create Leads |
| `process_pdf_import` | HIGH | `imports` | Extract PDF pages, create Leads |
| `process_image` | MEDIUM | `images` | Generate thumbnails, OCR if needed |
| `generate_analytics_cache` | LOW | `analytics` | Pre-compute dashboard/analytics data |
| `send_email_notification` | LOW | `emails` | Send email alerts |
| `cleanup_temp_files` | LOW | `maintenance` | Delete expired temp files |
| `backup_database` | LOW | `maintenance` | Trigger pg_dump |
| `audit_log_archival` | LOW | `maintenance` | Archive logs older than 90 days |

### Sample Task — Excel Import (refactored from synchronous):
```python
# excel/tasks.py
from celery import shared_task
from django.db import transaction

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_excel_import_task(self, import_id):
    from .models import ExcelImport
    from .services import process_import
    try:
        process_import(import_id)
    except Exception as exc:
        self.retry(exc=exc)
```

### Flower monitoring:
```bash
celery -A crm flower --port=5555 --basic_auth=admin:${FLOWER_PASSWORD}
```

### Periodic tasks with Celery Beat:
```python
# crm/beat.py
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "refresh-analytics-cache": {
        "task": "analytics.tasks.refresh_analytics_cache",
        "schedule": crontab(minute="*/15"),  # Every 15 min
    },
    "cleanup-expired-sessions": {
        "task": "accounts.tasks.cleanup_expired_sessions",
        "schedule": crontab(hour="3", minute="0"),  # Daily 3 AM
    },
    "send-daily-summary-emails": {
        "task": "accounts.tasks.send_daily_summary",
        "schedule": crontab(hour="8", minute="0"),  # Daily 8 AM
    },
    "archive-old-audit-logs": {
        "task": "audit.tasks.archive_audit_logs",
        "schedule": crontab(day_of_month="1", hour="2", minute="0"),  # Monthly
    },
}
```

---

## 7. BACKUP STRATEGY

### Database Backup (PostgreSQL)
```bash
#!/bin/bash
# /etc/cron.daily/crm-db-backup
BACKUP_DIR=/var/backups/crm/db
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_NAME="${DB_NAME:-crm_lms}"

mkdir -p "$BACKUP_DIR"

# Full backup
pg_dump \
  --host="${DB_HOST:-localhost}" \
  --port="${DB_PORT:-5432}" \
  --username="${DB_USER:-postgres}" \
  --format=custom \
  --compress=9 \
  --file="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.dump" \
  "$DB_NAME"

# Symlink latest
ln -sf "${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.dump" "${BACKUP_DIR}/latest.dump"

# Encrypt
gpg --encrypt --recipient admin@company.com \
  "${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.dump"

# Upload to S3/Wasabi/Backblaze
aws s3 cp "${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.dump.gpg" \
  "s3://crm-backups/db/${TIMESTAMP}.dump.gpg"

# Retention: keep 7 daily, 4 weekly, 12 monthly
find "$BACKUP_DIR" -name "*.dump" -mtime +7 -delete
```

### File Backup (Media/Uploads)
```bash
#!/bin/bash
# /etc/cron.daily/crm-files-backup
MEDIA_DIR=/var/www/crm/media
BACKUP_DIR=/var/backups/crm/files

tar czf "${BACKUP_DIR}/media_$(date +%Y%m%d).tar.gz" -C "$MEDIA_DIR" .
aws s3 cp "${BACKUP_DIR}/media_$(date +%Y%m%d).tar.gz" \
  "s3://crm-backups/files/media_$(date +%Y%m%d).tar.gz"
```

### Backup Schedule

| Type | Frequency | Retention | Storage |
|---|---|---|---|
| PostgreSQL (full) | Daily | 7 days local, 30 days S3 | S3 + local |
| WAL archives | Continuous (5 min) | 7 days | S3 |
| Media files | Daily | 30 days | S3 |
| Config files | Every deploy | Git history | GitHub |
| Audit logs (archived) | Monthly | 7 years | S3 Glacier |

### Recovery Runbook
```bash
# Restore DB
pg_restore --dbname=crm_lms --format=custom --jobs=4 \
  /var/backups/crm/db/latest.dump

# Point-in-time recovery
# 1. Identify target time
# 2. Restore from base backup
# 3. Apply WAL up to target time
pg_ctl -D /var/lib/postgresql/data promote  # if replica
```

---

## 8. DEPLOYMENT STRATEGY

### Docker Compose (Production)
```yaml
# docker-compose.yml
version: "3.8"

services:
  db:
    image: postgres:16-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: crm_lms
      POSTGRES_USER: crm_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    deploy:
      resources:
        limits: { cpus: "2", memory: "2G" }
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U crm_user -d crm_lms"]
      interval: 10s

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    command: redis-server --requirepass ${REDIS_PASSWORD}
    deploy:
      resources:
        limits: { cpus: "0.5", memory: "256M" }

  web:
    build: .
    command: gunicorn crm.wsgi:application --config gunicorn.conf.py
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    environment:
      DJANGO_SETTINGS_MODULE: crm.settings
      DJANGO_SECRET_KEY: ${DJANGO_SECRET_KEY}
      DJANGO_DEBUG: "False"
      DJANGO_ALLOWED_HOSTS: ${DOMAIN}
      DB_ENGINE: django.db.backends.postgresql
      DB_NAME: crm_lms
      DB_USER: crm_user
      DB_PASSWORD: ${DB_PASSWORD}
      DB_HOST: db
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0
    depends_on:
      db: { condition: service_healthy }
      redis: { condition: service_started }
    deploy:
      replicas: 2
      resources:
        limits: { cpus: "1", memory: "512M" }

  worker:
    build: .
    command: celery -A crm worker -l info -Q imports,images,emails,analytics,maintenance -c 4
    volumes:
      - media_volume:/app/media
    environment:
      <<: *web_environment  # same env as web
    depends_on:
      - db
      - redis
    deploy:
      replicas: 2
      resources:
        limits: { cpus: "2", memory: "1G" }

  beat:
    build: .
    command: celery -A crm beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    environment:
      <<: *web_environment
    depends_on:
      - db
      - redis

  nginx:
    image: nginx:1.27-alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
      - static_volume:/static:ro
      - media_volume:/media:ro
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - web

volumes:
  postgres_data:
  redis_data:
  static_volume:
  media_volume:
```

### CI/CD Pipeline (GitHub Actions)
```yaml
# .github/workflows/deploy.yml
name: Deploy
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r requirements.txt
      - run: python manage.py check --deploy
      - run: python manage.py test --parallel --settings=crm.settings_test

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: |
          docker compose -f docker-compose.yml build
          docker compose -f docker-compose.yml push
          ssh deploy@${{ secrets.HOST }} "
            cd /opt/crm &&
            docker compose pull &&
            docker compose up -d --wait &&
            docker compose exec -T web python manage.py migrate &&
            docker compose exec -T web python manage.py collectstatic --no-input
          "
```

### Environment variable template (`.env.production`):
```ini
DJANGO_SECRET_KEY=<random-64-char-string>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=crm.company.com,api.crm.company.com
DB_ENGINE=django.db.backends.postgresql
DB_NAME=crm_lms
DB_USER=crm_user
DB_PASSWORD=<strong-password>
DB_HOST=db
DB_PORT=5432
REDIS_URL=redis://:<password>@redis:6379/0
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=<sendgrid-api-key>
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=noreply@crm.company.com
STATIC_ROOT=/app/staticfiles
MEDIA_ROOT=/app/media
AWS_ACCESS_KEY_ID=<id>
AWS_SECRET_ACCESS_KEY=<key>
AWS_STORAGE_BUCKET_NAME=crm-uploads
```

---

## 9. NGINX CONFIGURATION

```nginx
# /etc/nginx/nginx.conf
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 4096;
    multi_accept on;
    use epoll;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format json escape=json
        '{'
        '"time":"$time_iso8601",'
        '"remote_addr":"$remote_addr",'
        '"remote_user":"$remote_user",'
        '"request":"$request",'
        '"status":$status,'
        '"body_bytes":$body_bytes_sent,'
        '"request_time":$request_time,'
        '"http_referrer":"$http_referer",'
        '"http_user_agent":"$http_user_agent",'
        '"http_x_forwarded_for":"$http_x_forwarded_for"'
        '}';

    access_log /var/log/nginx/access.log json buffer=32k flush=5s;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    keepalive_requests 1000;
    client_max_body_size 50M;
    client_body_buffer_size 128k;
    client_header_buffer_size 8k;
    types_hash_max_size 2048;
    server_tokens off;

    # Rate limiting zones
    limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;
    limit_req_zone $binary_remote_addr zone=api:10m rate=100r/s;
    limit_req_zone $binary_remote_addr zone=uploads:10m rate=10r/m;
    limit_conn_zone $binary_remote_addr zone=conn_limit:10m;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:50m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;
    ssl_stapling on;
    ssl_stapling_verify on;
    resolver 8.8.8.8 1.1.1.1 valid=300s;

    # Security headers
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy strict-origin-when-cross-origin always;
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

    # Content Security Policy
    add_header Content-Security-Policy "
        default-src 'self';
        script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline' 'unsafe-eval';
        style-src 'self' https://cdn.jsdelivr.net https://fonts.googleapis.com 'unsafe-inline';
        font-src 'self' https://cdn.jsdelivr.net https://fonts.gstatic.com;
        img-src 'self' data: blob:;
        connect-src 'self';
        form-action 'self';
        base-uri 'self';
        frame-ancestors 'none';
    " always;

    upstream django {
        least_time header;
        server web:8000 max_fails=3 fail_timeout=30s;
        keepalive 32;
    }

    server {
        listen 80;
        server_name crm.company.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name crm.company.com;

        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;

        # Gzip
        gzip on;
        gzip_comp_level 5;
        gzip_min_length 256;
        gzip_proxied any;
        gzip_types
            application/json
            application/javascript
            text/css
            text/plain
            text/xml
            image/svg+xml;

        # Static files
        location /static/ {
            alias /static/;
            expires 365d;
            add_header Cache-Control "public, immutable";
            access_log off;
        }

        # Media files
        location /media/ {
            alias /media/;
            expires 30d;
            add_header Cache-Control "public, immutable";
            access_log off;
        }

        # API — rate limited
        location /api/ {
            limit_req zone=api burst=200 nodelay;
            proxy_pass http://django;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 90s;
        }

        # Login — strict rate limit
        location /api/auth/login/ {
            limit_req zone=login burst=3 nodelay;
            proxy_pass http://django;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }

        # File uploads — size + rate limited
        location /api/excel/upload/ {
            client_max_body_size 100M;
            client_body_timeout 300s;
            proxy_read_timeout 300s;
            proxy_pass http://django;
        }

        location /api/images/upload/ {
            client_max_body_size 200M;
            client_body_timeout 300s;
            proxy_read_timeout 300s;
            proxy_pass http://django;
        }

        # Django admin
        location /admin/ {
            limit_req zone=login burst=5;
            proxy_pass http://django;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }

        # Main app
        location / {
            proxy_pass http://django;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_redirect off;
        }

        # Health check
        location /health/ {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }
    }
}
```

---

## 10. GUNICORN RECOMMENDATIONS

### Configuration file `gunicorn.conf.py`:
```python
"""Gunicorn production configuration."""
import multiprocessing
import os

bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1  # e.g., 5 on 2-core
worker_class = "uvicorn.workers.UvicornWorker"  # ASGI for future async
# worker_class = "sync"  # Use sync for WSGI-only

threads = 4  # Only for sync workers
worker_connections = 1000
max_requests = 2000
max_requests_jitter = 200

timeout = 120
graceful_timeout = 30
keepalive = 5

limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

accesslog = "-"  # stdout
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(L)s'
errorlog = "-"
loglevel = "info"

capture_output = True
enable_stdio_inheritance = True

# Preload app for faster worker startup
preload_app = True

# Restart workers that use too much memory
reload = False  # Set to True only in dev
spew = False

# Environment
raw_env = [
    "DJANGO_SETTINGS_MODULE=crm.settings",
]

def on_starting(server):
    """Log startup."""
    server.log.info("Starting CRM Gunicorn server")


def when_ready(server):
    """Log ready."""
    server.log.info("CRM server is ready to accept connections")


def post_fork(server, worker):
    """Log worker startup."""
    server.log.info(f"Worker spawned (pid: {worker.pid})")


def pre_exec(server):
    """Log before reload."""
    server.log.info("Forked child for pre_exec")


def worker_abort(worker):
    """Log worker abort."""
    worker.log.info(f"Worker {worker.pid} aborted")
```

### Systemd Service Unit
```ini
# /etc/systemd/system/crm-gunicorn.service
[Unit]
Description=CRM Gunicorn daemon
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=simple
User=crm
Group=crm
WorkingDirectory=/opt/crm
EnvironmentFile=/opt/crm/.env
ExecStart=/opt/crm/venv/bin/gunicorn crm.wsgi:application --config gunicorn.conf.py
ExecReload=/bin/kill -s HUP $MAINPID
ExecStop=/bin/kill -s TERM $MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security hardening
ProtectSystem=full
ProtectHome=true
PrivateTmp=true
NoNewPrivileges=true
CapabilityBoundingSet=
SystemCallArchitectures=native
MemoryLimit=512M
CPUQuota=200%

[Install]
WantedBy=multi-user.target
```

### Logrotate Configuration
```nginx
# /etc/logrotate.d/crm
/var/log/nginx/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    sharedscripts
    postrotate
        [ -f /var/run/nginx.pid ] && kill -USR1 `cat /var/run/nginx.pid`
    endscript
}

/var/log/crm/*.log {
    daily
    rotate 90
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
```

### Monitoring with Prometheus + Grafana (via `django-prometheus`):
```python
# crm/settings.py
INSTALLED_APPS += ["django_prometheus"]
MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
] + MIDDLEWARE + [
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]
```
Exposes metrics at `/metrics` endpoint for Prometheus scraping.

---

## QUICK-WIN PRIORITY LIST

| Priority | Effort | Category | Action |
|---|---|---|---|
| P0 | 5 min | Security | Move `SECRET_KEY` to env var |
| P0 | 5 min | Security | Set `DEBUG=False` in production |
| P0 | 2 min | Security | Set `ALLOWED_HOSTS` via env |
| P0 | 30 min | Security | Add missing HTTPS settings |
| P1 | 1 hr | Permissions | Restrict `LeadDetailView` per role |
| P1 | 1 hr | Permissions | Add object-level check to API status updates |
| P1 | 2 hr | Performance | Reduce `get_dashboard_kpi()` from 7 queries to 1 |
| P1 | 1 hr | Performance | Add composite indexes migration |
| P1 | 4 hr | Architecture | Set up Celery + Redis for async imports |
| P2 | 2 hr | Performance | Add Redis caching to dashboard views |
| P2 | 1 hr | Performance | Optimize `LeadListView.status_counts` to use filtered qs |
| P2 | 2 hr | Security | Add rate limiting to login and API |
| P2 | 4 hr | Infrastructure | Dockerize application |
| P3 | 2 hr | Security | Remove duplicate `leads/permissions.py` |
| P3 | 4 hr | Infrastructure | Set up CI/CD pipeline |
| P3 | 4 hr | Infrastructure | Configure nginx + gunicorn for production |
| P3 | 2 hr | Backup | Implement automated backup scripts |
| P3 | 4 hr | Monitoring | Add Prometheus metrics |
