# Loan Lead Management CRM - Production Grade Architecture

**Project**: Loan Lead Management System
**Status**: Architecture Design
**Version**: 1.0
**Date**: 2026-06-10
**Tech Stack**: Django 4.2+, DRF, PostgreSQL, Celery, Redis

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Database Architecture](#database-architecture)
3. [Entity Relationship Diagram](#entity-relationship-diagram)
4. [App Responsibilities](#app-responsibilities)
5. [Folder Structure](#folder-structure)
6. [Models Planning](#models-planning)
7. [API Planning](#api-planning)
8. [Security Architecture](#security-architecture)
9. [Permissions & RBAC](#permissions--rbac)
10. [Integration Points](#integration-points)
11. [Scalability & Future Growth](#scalability--future-growth)

---

## 1. System Overview

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                   FRONTEND LAYER                             │
│        Django Templates + Bootstrap 5 + Vanilla JS            │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    API LAYER (DRF)                            │
│    RESTful APIs for Web & Future Mobile Clients              │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                 BUSINESS LOGIC LAYER                         │
│  ┌─────────────┬──────────┬────────┬──────────┬────────────┐ │
│  │  Accounts   │  Leads   │ Excel  │   PDF    │  Imager    │ │
│  └─────────────┴──────────┴────────┴──────────┴────────────┘ │
│  ┌─────────────┬──────────┬────────┬──────────┬────────────┐ │
│  │  Analytics  │ Audit    │ Tasks  │ Reports  │ Notification│ │
│  └─────────────┴──────────┴────────┴──────────┴────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                  DATA ACCESS LAYER (ORM)                     │
│              Django Models + PostgreSQL Queries              │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   DATABASE LAYER                             │
│    ┌──────────────────────────────────────────────────────┐  │
│    │         PostgreSQL Primary Database                  │  │
│    │  (Users, Leads, Activities, Audit Logs, etc.)        │  │
│    └──────────────────────────────────────────────────────┘  │
│    ┌──────────────────────────────────────────────────────┐  │
│    │         Redis Cache & Session Store                  │  │
│    └──────────────────────────────────────────────────────┘  │
│    ┌──────────────────────────────────────────────────────┐  │
│    │         File Storage (Excel, PDF, Images)            │  │
│    └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   WORKER LAYER (Celery)                      │
│  ┌─────────────┬──────────┬────────┬──────────┬────────────┐ │
│  │   Imports   │ Reports  │ Emails │ Analytics│  Cleanup   │ │
│  │  (Excel/    │Generation│Notific │ Calculate│  Tasks     │ │
│  │  PDF/Img)   │          │ations  │          │            │ │
│  └─────────────┴──────────┴────────┴──────────┴────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Database Architecture

### Core Entities

The system operates on a hierarchical data structure:

```
Bank (Lead Source Provider)
  ├── Campaign (Marketing Campaign)
  │    ├── Batch (Import Batch)
  │    │    └── Lead (Individual Lead)
  │    │         ├── Activity (Follow-up Action)
  │    │         ├── Note (Internal Notes)
  │    │         ├── Outcome (Result)
  │    │         └── Attachment (File Reference)
  │    └── LeadAssignment (Caller Assignment)
  │
  ├── User (Team Members)
  └── Report (Generated Analytics)
```

### Database Design Principles

1. **Normalization**: 3NF to prevent data anomalies
2. **Audit Trail**: Timestamp tracking on all entities
3. **Soft Deletes**: Logical deletion with is_deleted flag
4. **Indexing Strategy**: Composite indexes on frequently queried fields
5. **Partitioning**: Ready for future time-based partitioning on Activity/Lead tables
6. **Relationships**: Foreign key constraints with CASCADE/PROTECT options

### Key Design Decisions

| Aspect        | Decision                         | Rationale                                           |
| ------------- | -------------------------------- | --------------------------------------------------- |
| Primary Keys  | UUID + Auto ID (Hybrid)          | UUID for distributed future; Auto ID for simplicity |
| Timestamps    | Django auto_now/auto_now_add     | Automatic tracking with timezone support            |
| Soft Deletes  | is_deleted + deleted_at          | Audit compliance + recovery capability              |
| Status Fields | CharField with Choices           | Enum-like behavior + database queryability          |
| Audit Logs    | Separate AuditLog table          | Complete history without bloating main tables       |
| File Storage  | Database path + External storage | Flexibility with cloud migration                    |

---

## 3. Entity Relationship Diagram

### ERD Overview (Detailed View)

```
┌──────────────────┐
│   AUTH_USER      │
├──────────────────┤
│ id (PK)          │ 1
│ username         │ │
│ email            │ │
│ password_hash    │ │
│ is_active        │ │
│ created_at       │ │
│ updated_at       │ │
└──────────────────┘
         │
         │ 1:N
         │
┌──────────────────────────────┐
│   USER_PROFILE               │
├──────────────────────────────┤
│ id (PK)                      │
│ user_id (FK)                 │ 1
│ role (SuperAdmin, TeamLead...) │ │
│ department                   │ │
│ phone                        │ │
│ manager_id (FK Self)         │ │
│ is_active                    │ │
│ created_at                   │ │
│ updated_at                   │ │
└──────────────────────────────┘
         │
         │ 1:N
         │
    ┌────┴────┐
    │          │
    │          │
┌───┴──────────────────┐      ┌──────────────────────┐
│   BANK_SOURCE        │      │   CAMPAIGN           │
├──────────────────────┤      ├──────────────────────┤
│ id (PK)              │ 1    │ id (PK)              │
│ name                 │ ├─── │ bank_source_id (FK)  │ 1
│ source_code          │      │ name                 │ │
│ (HDFC, ICICI, etc)   │      │ campaign_code        │ │
│ contact_person       │      │ status               │ │
│ email                │      │ start_date           │ │
│ phone                │      │ end_date             │ │
│ address              │      │ description          │ │
│ is_active            │      │ created_by_id (FK)   │ │
│ created_at           │      │ created_at           │ │
│ updated_at           │      │ updated_at           │ │
└──────────────────────┘      └──────────────────────┘
                                       │
                                       │ 1:N
                                       │
                                ┌──────┴──────────────────┐
                                │   BATCH                  │
                                ├──────────────────────────┤
                                │ id (PK)                  │
                                │ campaign_id (FK)         │ 1
                                │ batch_number             │ │
                                │ source_file_path         │ │
                                │ import_status            │ │
                                │ (Pending, Processing,    │ │
                                │  Completed, Failed)      │ │
                                │ total_records            │ │
                                │ processed_records        │ │
                                │ failed_records           │ │
                                │ import_date              │ │
                                │ uploaded_by_id (FK)      │ │
                                │ processed_by_id (FK)     │ │
                                │ created_at               │ │
                                │ updated_at               │ │
                                └──────────────────────────┘
                                         │
                                         │ 1:N
                                         │
        ┌────────────────────────────────┴───────────────────┐
        │                                                     │
        │                                                     │
┌───────┴──────────────────────┐        ┌──────────────────────────────┐
│   LEAD                        │        │   ACTIVITY                   │
├───────────────────────────────┤        ├──────────────────────────────┤
│ id (PK)                       │ 1      │ id (PK)                      │
│ batch_id (FK)                 │ ├─┬─── │ lead_id (FK)                 │ 1
│ lead_number                   │   │    │ assigned_to_id (FK)          │ │
│ lead_source_id                │   │    │ activity_type                │ │
│ (Ex: HDFC_001)                │   │    │ (Call, Email, SMS, Visit)    │ │
│ customer_name                 │   │    │ status                       │ │
│ phone                         │   │    │ (Scheduled, Completed,      │ │
│ email                         │   │    │  Pending, Cancelled)         │ │
│ loan_amount                   │   │    │ scheduled_date               │ │
│ pan_number                    │   │    │ completed_date               │ │
│ address                       │   │    │ notes                        │ │
│ city                          │   │    │ outcome_id (FK)              │ │
│ state                         │   │    │ created_at                   │ │
│ lead_status                   │   │    │ updated_at                   │ │
│ (New, Contacted, Qualified,   │   │    └──────────────────────────────┘
│  Converted, Rejected, Lost)   │   │
│ assigned_to_id (FK)           │   │
│ (Current Caller)              │   │
│ is_duplicate                  │   │
│ duplicate_of_id (FK)          │   │
│ created_at                    │   │
│ updated_at                    │   │
│ is_deleted                    │   │
└───────────────────────────────┘   │
        │                            │
        │ 1:N                        │
        │                            │
        └────────────────────────────┘
        │
        │ 1:N
        │
┌───────┴────────────────┐
│   NOTE                 │
├────────────────────────┤
│ id (PK)                │
│ lead_id (FK)           │ 1
│ created_by_id (FK)     │ │
│ content                │ │
│ is_internal            │ │
│ created_at             │ │
│ updated_at             │ │
└────────────────────────┘


┌──────────────────────────────┐
│   OUTCOME                     │
├──────────────────────────────┤
│ id (PK)                      │
│ outcome_type                 │ 1
│ (Converted, Rejected, Lost,  │ │
│  Pending, Follow-up)         │ │
│ reason                       │ │
│ converted_amount (nullable)  │ │
│ conversion_date (nullable)   │ │
│ created_at                   │ │
│ updated_at                   │ │
└──────────────────────────────┘


┌──────────────────────────────┐
│   LEAD_ASSIGNMENT            │
├──────────────────────────────┤
│ id (PK)                      │
│ lead_id (FK)                 │ 1:N
│ assigned_to_id (FK)          │
│ (Caller/Operator)            │
│ assigned_by_id (FK)          │
│ (Team Lead)                  │
│ assignment_status            │
│ (Active, Completed,          │
│  Transferred, Rejected)      │
│ start_date                   │
│ end_date                     │
│ created_at                   │
│ updated_at                   │
└──────────────────────────────┘


┌──────────────────────────────┐
│   ATTACHMENT                 │
├──────────────────────────────┤
│ id (PK)                      │
│ lead_id (FK)                 │ 1:N
│ file_path                    │
│ file_type                    │
│ (Excel, PDF, Image, Document)│
│ file_size                    │
│ uploaded_by_id (FK)          │
│ created_at                   │
│ updated_at                   │
└──────────────────────────────┘


┌──────────────────────────────┐
│   AUDIT_LOG                  │
├──────────────────────────────┤
│ id (PK)                      │ 1:N
│ user_id (FK)                 │
│ model_name                   │
│ record_id                    │
│ action                       │
│ (Create, Update, Delete,     │
│  View)                       │
│ old_values (JSONB)           │
│ new_values (JSONB)           │
│ ip_address                   │
│ user_agent                   │
│ timestamp                    │
└──────────────────────────────┘


┌──────────────────────────────┐
│   REPORT                     │
├──────────────────────────────┤
│ id (PK)                      │ 1:N
│ report_type                  │
│ (Daily, Weekly, Monthly,     │
│  Custom)                     │
│ report_scope                 │
│ (Employee, Source, Dept)     │
│ report_date                  │
│ generated_by_id (FK)         │
│ data (JSONB)                 │
│ created_at                   │
└──────────────────────────────┘
```

---

## 4. App Responsibilities

### 4.1 Accounts App

**Purpose**: User management, authentication, and role-based access control

**Core Responsibilities**:

- User registration and authentication
- Profile management
- Role & permission management
- User activity tracking
- Department hierarchy management
- Manager-employee relationships

**Key Models**:

- `User` (Extended Django User)
- `UserProfile` (Role, department, manager)
- `Permission` (Custom permissions)
- `Role` (Predefined roles)

**Business Logic**:

- Multi-level hierarchy (organization structure)
- Active/inactive user management
- Password policies
- Session management

---

### 4.2 Leads App

**Purpose**: Core lead management and lead lifecycle tracking

**Core Responsibilities**:

- Lead creation and maintenance
- Lead status workflow management
- Lead assignment to team members
- Lead deduplication logic
- Bulk lead import coordination
- Lead activity tracking
- Outcome management

**Key Models**:

- `BankSource` (HDFC, ICICI, Axis, Tata Capital, etc.)
- `Campaign` (Marketing campaigns)
- `Batch` (Import batches)
- `Lead` (Individual lead records)
- `LeadAssignment` (Assignment tracking)
- `Outcome` (Lead outcome/result)

**Business Logic**:

- Lead status transitions (New → Contacted → Qualified → Converted/Lost)
- Duplicate detection and merging
- Assignment routing (round-robin, manual)
- SLA tracking
- Lead reactivation rules

---

### 4.3 Accounts App (Enhanced)

**Purpose**: User authentication and authorization beyond Django auth

**Note**: This overlaps with Accounts app; consolidate as needed

**Responsibilities**:

- Extended user model for CRM-specific fields
- Authentication (Session + Token-based for future API clients)
- API key management for integrations
- Two-factor authentication (future)

---

### 4.4 Excel App

**Purpose**: Excel file import and processing

**Core Responsibilities**:

- Excel file upload handling
- File validation (schema, data types)
- Data parsing and extraction
- Bulk lead creation from Excel
- Error handling and logging
- Duplicate detection
- Data transformation

**Key Models**:

- `ExcelImport` (Import session tracking)
- `ExcelImportLog` (Line-by-line import logs)

**Supported Formats**:

- Lead list imports (Customer Name, Phone, Email, Loan Amount, etc.)
- Batch imports with standardized templates
- Multi-sheet handling

---

### 4.5 PDF App

**Purpose**: PDF file processing and extraction

**Core Responsibilities**:

- PDF file upload handling
- Text/data extraction from PDFs
- OCR support (optional, future)
- Document classification
- Lead data extraction from PDFs
- Metadata extraction

**Key Models**:

- `PDFImport` (Import session tracking)
- `PDFExtractedData` (Extracted information)

**Use Cases**:

- Bank-provided lead lists in PDF format
- Loan application documents
- Verification documents

---

### 4.6 Imager App

**Purpose**: Image processing and document management

**Core Responsibilities**:

- Image file upload handling
- Image validation (format, size, resolution)
- Image storage and retrieval
- Document image storage (ID proof, address proof, etc.)
- Thumbnail generation
- Image compression

**Key Models**:

- `ImageUpload` (Image metadata)
- `DocumentImage` (Lead-associated images)

**Supported Formats**:

- JPG, PNG, WebP
- Document images (ID, Address proof, etc.)

---

### 4.7 Activity App (New - Required)

**Purpose**: Track all lead follow-up activities and interactions

**Core Responsibilities**:

- Activity creation and tracking
- Activity scheduling
- Completion tracking
- Activity history
- Activity outcome management
- SLA monitoring

**Key Models**:

- `Activity` (Call, Email, SMS, Visit, etc.)
- `ActivityType` (Enum)
- `ActivityOutcome` (Result of activity)

**Activity Types**:

- Phone call
- Email
- SMS
- Site visit
- Document submission
- Feedback collection

---

### 4.8 Audit App (New - Required)

**Purpose**: Comprehensive audit logging and compliance tracking

**Core Responsibilities**:

- Log all CRUD operations
- Track user actions
- Maintain audit trail
- Compliance reporting
- Data change history
- Access logging

**Key Models**:

- `AuditLog` (Complete audit trail)
- `UserActionLog` (User-specific actions)

**Logged Events**:

- Record creation/modification/deletion
- Sensitive field changes
- Lead assignment changes
- Outcome changes
- User login/logout
- Report generation

---

### 4.9 Analytics App (New - Required)

**Purpose**: Business intelligence and reporting

**Core Responsibilities**:

- Daily/weekly/monthly report generation
- Employee performance metrics
- Source analytics
- Conversion rate tracking
- Pipeline analytics
- Dashboard data aggregation

**Key Models**:

- `Report` (Generated reports)
- `DailyStats` (Daily aggregated data)
- `EmployeeAnalytics` (Per-employee metrics)

**Report Types**:

- Daily lead summary
- Employee performance
- Source performance
- Conversion analytics
- SLA compliance
- Team-wise reports

---

### 4.10 Notification App (New - Required)

**Purpose**: Real-time notifications and alerts

**Core Responsibilities**:

- Activity reminders
- Assignment notifications
- Status change alerts
- Bulk notification delivery
- Notification preferences

**Key Models**:

- `Notification` (Notification records)
- `NotificationTemplate` (Template management)

**Notification Channels**:

- In-app notifications
- Email
- SMS (future)

---

### 4.11 Tasks App (New - Required)

**Purpose**: Activity/task scheduling and management

**Core Responsibilities**:

- Scheduled activity creation
- Task reminders
- Task completion tracking
- Recurring tasks
- Task escalation

**Key Models**:

- `Task` (Scheduled activities)
- `TaskReminder` (Reminder tracking)

---

### 4.12 API App (Structural)

**Purpose**: API versioning and documentation

**Responsibilities**:

- API endpoint organization
- API documentation
- API versioning
- Rate limiting
- API authentication

---

## 5. Folder Structure

```
crm/
├── manage.py
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
│
├── crm/                          # Project settings
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py               # Shared settings
│   │   ├── development.py        # Development overrides
│   │   ├── production.py         # Production overrides
│   │   └── testing.py            # Testing overrides
│   ├── urls.py
│   ├── wsgi.py
│   ├── asgi.py
│   └── settings.py               # Legacy, redirect to settings/base.py
│
├── apps/                         # All Django apps
│   │
│   ├── accounts/                 # User & Authentication
│   │   ├── migrations/
│   │   ├── management/commands/
│   │   ├── tests/
│   │   │   ├── test_models.py
│   │   │   ├── test_views.py
│   │   │   ├── test_permissions.py
│   │   │   ├── test_api.py
│   │   │   └── __init__.py
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── permissions.py        # Custom permission classes
│   │   ├── serializers.py        # DRF serializers
│   │   ├── services.py           # Business logic
│   │   └── forms.py
│   │
│   ├── leads/                    # Core Lead Management
│   │   ├── migrations/
│   │   ├── management/commands/
│   │   ├── tests/
│   │   │   ├── test_models.py
│   │   │   ├── test_lead_assignment.py
│   │   │   ├── test_deduplication.py
│   │   │   ├── test_bulk_import.py
│   │   │   └── __init__.py
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── serializers.py
│   │   ├── services.py           # Lead assignment, deduplication logic
│   │   ├── utils.py              # Utility functions
│   │   ├── forms.py
│   │   └── signals.py            # Django signals for lead changes
│   │
│   ├── excel/                    # Excel Import
│   │   ├── migrations/
│   │   ├── tests/
│   │   │   ├── test_models.py
│   │   │   ├── test_import.py
│   │   │   ├── fixtures/
│   │   │   │   └── sample_leads.xlsx
│   │   │   └── __init__.py
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── serializers.py
│   │   ├── services.py           # Excel parsing, validation
│   │   ├── utils.py              # Excel utilities
│   │   ├── validators.py         # Custom validators
│   │   └── forms.py
│   │
│   ├── pdf/                      # PDF Processing
│   │   ├── migrations/
│   │   ├── tests/
│   │   │   ├── test_models.py
│   │   │   ├── test_extraction.py
│   │   │   ├── fixtures/
│   │   │   │   └── sample_lead_list.pdf
│   │   │   └── __init__.py
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── serializers.py
│   │   ├── services.py           # PDF parsing, OCR integration
│   │   ├── utils.py              # PDF utilities
│   │   └── forms.py
│   │
│   ├── imager/                   # Image Processing
│   │   ├── migrations/
│   │   ├── tests/
│   │   │   ├── test_models.py
│   │   │   ├── test_upload.py
│   │   │   └── __init__.py
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── serializers.py
│   │   ├── services.py           # Image processing, compression
│   │   ├── utils.py              # Image utilities
│   │   └── forms.py
│   │
│   ├── activities/               # Activity/Follow-up Tracking
│   │   ├── migrations/
│   │   ├── tests/
│   │   │   ├── test_models.py
│   │   │   ├── test_scheduling.py
│   │   │   └── __init__.py
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── serializers.py
│   │   ├── services.py           # Activity scheduling, SLA tracking
│   │   ├── signals.py
│   │   └── forms.py
│   │
│   ├── audit/                    # Audit Logging
│   │   ├── migrations/
│   │   ├── tests/
│   │   │   └── test_audit.py
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── serializers.py
│   │   ├── middleware.py         # Audit middleware
│   │   ├── signals.py            # Auto-logging via signals
│   │   └── utils.py
│   │
│   ├── analytics/                # Reports & Analytics
│   │   ├── migrations/
│   │   ├── tests/
│   │   │   ├── test_models.py
│   │   │   ├── test_reports.py
│   │   │   └── __init__.py
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── serializers.py
│   │   ├── services.py           # Report generation, aggregation
│   │   ├── utils.py              # Analytics utilities
│   │   ├── tasks.py              # Celery tasks for report gen
│   │   └── queries.py            # Complex database queries
│   │
│   ├── notifications/            # Notifications & Alerts
│   │   ├── migrations/
│   │   ├── tests/
│   │   │   ├── test_models.py
│   │   │   ├── test_notifications.py
│   │   │   └── __init__.py
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── serializers.py
│   │   ├── services.py           # Notification dispatch
│   │   ├── tasks.py              # Celery tasks
│   │   └── signals.py
│   │
│   ├── tasks/                    # Task Management
│   │   ├── migrations/
│   │   ├── tests/
│   │   │   └── test_tasks.py
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── serializers.py
│   │   ├── services.py
│   │   └── tasks.py              # Celery tasks (confusing naming - rename to celery_tasks.py)
│   │
│   └── api/                      # API Organization
│       ├── __init__.py
│       ├── v1/
│       │   ├── __init__.py
│       │   ├── urls.py
│       │   ├── views/
│       │   │   ├── __init__.py
│       │   │   ├── accounts.py
│       │   │   ├── leads.py
│       │   │   ├── activities.py
│       │   │   ├── analytics.py
│       │   │   └── ...
│       │   ├── serializers/
│       │   │   ├── __init__.py
│       │   │   ├── accounts.py
│       │   │   ├── leads.py
│       │   │   └── ...
│       │   └── permissions.py
│       │
│       └── v2/                   # Future API version
│           └── (same structure)
│
├── core/                         # Shared utilities & base classes
│   ├── __init__.py
│   ├── models.py                 # AbstractBaseModel, TimeStampedModel
│   ├── views.py                  # BaseViewSet, BaseListView
│   ├── serializers.py            # BaseSerializer
│   ├── permissions.py            # Custom DRF permissions
│   ├── pagination.py             # Custom pagination
│   ├── filters.py                # Custom filters
│   ├── exceptions.py             # Custom exceptions
│   ├── decorators.py             # Utility decorators
│   ├── utils.py                  # Utility functions
│   └── constants.py              # App-wide constants
│
├── celery_tasks/                 # Celery configuration
│   ├── __init__.py
│   ├── config.py                 # Celery app config
│   └── tasks.py                  # Shared celery tasks
│
├── templates/                    # Django templates
│   ├── base.html
│   ├── accounts/
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── dashboard.html
│   │   └── profile.html
│   ├── leads/
│   │   ├── lead_list.html
│   │   ├── lead_detail.html
│   │   ├── lead_form.html
│   │   └── bulk_import.html
│   ├── analytics/
│   │   ├── dashboard.html
│   │   ├── reports.html
│   │   └── employee_analytics.html
│   └── includes/
│       ├── navbar.html
│       ├── sidebar.html
│       ├── pagination.html
│       └── alerts.html
│
├── static/                       # Static files
│   ├── css/
│   │   ├── bootstrap.min.css
│   │   ├── custom.css
│   │   └── responsive.css
│   ├── js/
│   │   ├── utils.js
│   │   ├── api-client.js
│   │   ├── forms.js
│   │   ├── charts.js             # Chart.js for analytics
│   │   ├── excel-upload.js
│   │   └── lead-management.js
│   └── images/
│       └── ...
│
├── media/                        # User uploads
│   ├── uploads/
│   │   ├── excel/
│   │   ├── pdf/
│   │   └── images/
│   └── temp/
│
├── docs/                         # Documentation
│   ├── ARCHITECTURE.md           # This file
│   ├── SETUP.md
│   ├── API.md
│   ├── DATABASE.md
│   └── DEPLOYMENT.md
│
└── tests/                        # Integration/E2E tests
    ├── __init__.py
    ├── conftest.py               # Pytest fixtures
    ├── test_integration.py
    ├── test_workflows.py
    └── fixtures/
        ├── users.json
        ├── leads.json
        └── banks.json
```

---

## 6. Models Planning

### 6.1 Core Models Reference

#### Authentication & User Management

```
User (Extended Django User)
├── username (unique)
├── email (unique)
├── password_hash
├── first_name
├── last_name
├── is_active
├── is_staff
├── is_superuser
├── last_login
├── date_joined
└── created_at, updated_at

UserProfile
├── user (OneToOneField)
├── role (CharField: SuperAdmin, TeamLead, Caller, DataEntryOperator)
├── department (CharField)
├── phone (CharField)
├── manager (ForeignKey to User, nullable, self-referential)
├── profile_image (ImageField, nullable)
├── bio (TextField, nullable)
├── is_active (BooleanField)
├── last_activity_at (DateTimeField)
├── created_at, updated_at
└── Indexes: user, role, manager

Role (Master Data)
├── role_name (CharField, unique)
├── description (TextField)
├── permissions (ManyToManyField)
├── is_active (BooleanField)
└── created_at, updated_at

Permission (Custom)
├── permission_code (CharField, unique)
├── name (CharField)
├── description (TextField)
├── module (CharField: Leads, Activities, Reports, Users, etc.)
└── created_at, updated_at
```

#### Lead Sources

```
BankSource
├── name (CharField, unique)
├── source_code (CharField, unique: HDFC, ICICI, AXIS, TATA_CAPITAL, OTHER)
├── contact_person (CharField, nullable)
├── email (EmailField)
├── phone (CharField)
├── address (TextField, nullable)
├── city (CharField, nullable)
├── state (CharField, nullable)
├── is_active (BooleanField)
├── created_by (ForeignKey to User)
├── created_at, updated_at
└── Indexes: source_code, is_active
```

#### Campaign Management

```
Campaign
├── bank_source (ForeignKey to BankSource)
├── name (CharField)
├── campaign_code (CharField, unique)
├── status (CharField: Active, Inactive, Paused, Completed)
├── description (TextField, nullable)
├── start_date (DateField)
├── end_date (DateField, nullable)
├── created_by (ForeignKey to User)
├── created_at, updated_at
└── Indexes: bank_source, status, created_at
```

#### Batch (Import)

```
Batch
├── campaign (ForeignKey to Campaign)
├── batch_number (CharField, unique)
├── source_file_path (CharField)
├── import_status (CharField: Pending, Processing, Completed, Failed, Partial)
├── file_type (CharField: Excel, PDF, CSV)
├── total_records (IntegerField)
├── processed_records (IntegerField)
├── failed_records (IntegerField)
├── import_date (DateTimeField)
├── uploaded_by (ForeignKey to User)
├── processed_by (ForeignKey to User, nullable)
├── error_log (JSONField, nullable)
├── created_at, updated_at
└── Indexes: campaign, import_status, created_at
```

#### Core Lead Management

```
Lead (Core Entity)
├── batch (ForeignKey to Batch)
├── lead_number (CharField, unique)
├── lead_source_id (CharField: Ex: HDFC_001_12345)
├── customer_name (CharField, db_index=True)
├── phone (CharField, db_index=True)
├── email (EmailField, nullable, db_index=True)
├── pan_number (CharField, nullable, db_index=True)
├── loan_amount (DecimalField, nullable)
├── loan_type (CharField, nullable)
├── property_value (DecimalField, nullable)
├── employment_type (CharField, nullable)
├── address (TextField)
├── city (CharField, db_index=True)
├── state (CharField, db_index=True)
├── pincode (CharField, nullable)
├── lead_status (CharField: New, Contacted, Qualified, Converted, Rejected, Lost, Reactivated)
├── priority (CharField: High, Medium, Low)
├── assigned_to (ForeignKey to User, nullable)
├── assigned_at (DateTimeField, nullable)
├── is_duplicate (BooleanField)
├── duplicate_of (ForeignKey to Lead, nullable, self-referential)
├── notes_summary (TextField, nullable)
├── is_deleted (BooleanField)
├── deleted_at (DateTimeField, nullable)
├── created_at, updated_at
└── Indexes: (customer_name, phone), (phone), (email), (pan_number), (batch, lead_status), assigned_to, is_deleted
```

#### Activity/Follow-up

```
Activity (Follow-up Records)
├── lead (ForeignKey to Lead)
├── assigned_to (ForeignKey to User)
├── activity_type (CharField: Call, Email, SMS, Site_Visit, Document_Submission, Feedback)
├── status (CharField: Scheduled, In_Progress, Completed, Cancelled, Pending)
├── scheduled_date (DateTimeField)
├── completed_date (DateTimeField, nullable)
├── completion_notes (TextField, nullable)
├── outcome (ForeignKey to Outcome, nullable)
├── duration_minutes (IntegerField, nullable)
├── created_by (ForeignKey to User)
├── created_at, updated_at
└── Indexes: lead, assigned_to, status, scheduled_date, activity_type
```

#### Notes

```
Note
├── lead (ForeignKey to Lead)
├── content (TextField)
├── note_type (CharField: Internal, Customer_Facing)
├── is_internal (BooleanField)
├── created_by (ForeignKey to User)
├── created_at, updated_at
└── Indexes: lead, created_at
```

#### Outcomes

```
Outcome
├── activity (OneToOneField to Activity, nullable)
├── lead (ForeignKey to Lead)
├── outcome_type (CharField: Converted, Rejected, Lost, Pending, Follow_Up_Required)
├── reason (CharField, nullable: Loan_Sanctioned, High_Interest_Rates, Rejected_For_Low_CIBIL, etc.)
├── converted_amount (DecimalField, nullable)
├── conversion_date (DateField, nullable)
├── created_at, updated_at
└── Indexes: lead, outcome_type
```

#### Lead Assignment History

```
LeadAssignment
├── lead (ForeignKey to Lead)
├── assigned_to (ForeignKey to User: Caller/Operator)
├── assigned_by (ForeignKey to User: Team Lead)
├── assignment_status (CharField: Active, Completed, Transferred, Rejected)
├── start_date (DateTimeField)
├── end_date (DateTimeField, nullable)
├── reason_for_transfer (CharField, nullable)
├── created_at, updated_at
└── Indexes: lead, assigned_to, assigned_by, assignment_status
```

#### Attachments

```
Attachment
├── lead (ForeignKey to Lead)
├── file_path (CharField)
├── file_name (CharField)
├── file_type (CharField: PDF, Excel, Image, Document)
├── file_size (IntegerField)
├── uploaded_by (ForeignKey to User)
├── created_at
└── Indexes: lead, created_at
```

#### Audit Logging

```
AuditLog
├── user (ForeignKey to User)
├── model_name (CharField: Lead, Activity, Outcome, etc.)
├── record_id (CharField)
├── action (CharField: Create, Update, Delete, View, Export)
├── old_values (JSONField, nullable)
├── new_values (JSONField, nullable)
├── ip_address (CharField)
├── user_agent (CharField)
├── timestamp (DateTimeField, db_index=True)
└── Indexes: user, model_name, action, timestamp
```

#### Analytics & Reporting

```
Report
├── report_type (CharField: Daily, Weekly, Monthly, Custom)
├── report_scope (CharField: Employee, Department, Source, Company_Wide)
├── report_date (DateField)
├── generated_by (ForeignKey to User)
├── data (JSONField)
├── file_path (CharField, nullable)
├── created_at
└── Indexes: report_type, report_date

DailyStats (Denormalized for performance)
├── date (DateField, unique)
├── total_leads (IntegerField)
├── new_leads (IntegerField)
├── leads_converted (IntegerField)
├── leads_rejected (IntegerField)
├── activities_completed (IntegerField)
├── calls_made (IntegerField)
├── emails_sent (IntegerField)
├── updated_at
└── Index: date

EmployeeAnalytics (Monthly aggregates)
├── user (ForeignKey to User)
├── year_month (CharField: YYYY-MM)
├── leads_assigned (IntegerField)
├── leads_converted (IntegerField)
├── conversion_rate (FloatField)
├── avg_follow_ups (FloatField)
├── activities_completed (IntegerField)
├── updated_at
└── Indexes: user, year_month
```

#### Import-Specific Models

```
ExcelImport
├── batch (ForeignKey to Batch)
├── file_path (CharField)
├── imported_at (DateTimeField)
├── processed_at (DateTimeField, nullable)
├── status (CharField: Pending, Processing, Completed, Failed)
├── error_log (JSONField, nullable)
└── created_at, updated_at

ExcelImportLog
├── excel_import (ForeignKey to ExcelImport)
├── row_number (IntegerField)
├── status (CharField: Success, Failed)
├── error_message (TextField, nullable)
└── created_at

PDFImport
├── batch (ForeignKey to Batch)
├── file_path (CharField)
├── extraction_status (CharField)
├── extracted_text (TextField, nullable)
├── extracted_data (JSONField, nullable)
└── created_at, updated_at

ImageUpload
├── lead (ForeignKey to Lead, nullable)
├── file_path (CharField)
├── file_name (CharField)
├── image_type (CharField: ID_Proof, Address_Proof, Signature, Document)
├── uploaded_by (ForeignKey to User)
└── created_at
```

#### Notifications

```
Notification
├── user (ForeignKey to User)
├── notification_type (CharField: Activity_Reminder, Assignment_Alert, Status_Change)
├── title (CharField)
├── message (TextField)
├── is_read (BooleanField)
├── read_at (DateTimeField, nullable)
├── created_at
└── Indexes: user, is_read, created_at

NotificationTemplate
├── name (CharField, unique)
├── notification_type (CharField)
├── title_template (CharField)
├── message_template (TextField)
├── is_active (BooleanField)
└── created_at, updated_at
```

---

## 7. API Planning

### 7.1 API Architecture

**Base URL**: `/api/v1/`
**Format**: JSON
**Authentication**: Token-based (JWT for future; Session for current)
**Response Format**: Consistent with JSON:API or custom standard

**Response Structure**:

```json
{
  "success": true,
  "data": {},
  "errors": null,
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 100,
    "total_pages": 5
  },
  "timestamp": "2026-06-10T10:30:00Z"
}
```

---

### 7.2 API Endpoints

#### Authentication APIs

```
POST   /auth/login                    → User login
POST   /auth/logout                   → User logout
POST   /auth/register                 → New user registration (admin only)
POST   /auth/refresh-token            → Refresh auth token
GET    /auth/me                       → Current user profile
PUT    /auth/me                       → Update current user
POST   /auth/change-password          → Change password
POST   /auth/forgot-password          → Password reset request
POST   /auth/reset-password           → Confirm password reset
```

#### User Management APIs

```
GET    /users/                        → List all users (SuperAdmin)
POST   /users/                        → Create user (SuperAdmin)
GET    /users/{id}/                   → Get user details
PUT    /users/{id}/                   → Update user
DELETE /users/{id}/                   → Soft delete user
GET    /users/{id}/activities/        → Get user's activities
GET    /users/{id}/analytics/         → Get user's performance metrics
GET    /users/{id}/assignments/       → Get user's lead assignments
POST   /users/{id}/assign-role/       → Change user role (SuperAdmin)
GET    /teams/                        → Get team structure
GET    /teams/{manager_id}/members/   → Get team members
```

#### Bank Source APIs

```
GET    /banks/                        → List all bank sources
POST   /banks/                        → Create bank source
GET    /banks/{id}/                   → Get bank details
PUT    /banks/{id}/                   → Update bank
DELETE /banks/{id}/                   → Delete bank (soft)
GET    /banks/{id}/campaigns/         → Get campaigns for bank
GET    /banks/{id}/analytics/         → Get analytics by bank
```

#### Campaign APIs

```
GET    /campaigns/                    → List campaigns (with filters)
POST   /campaigns/                    → Create campaign
GET    /campaigns/{id}/               → Get campaign details
PUT    /campaigns/{id}/               → Update campaign
DELETE /campaigns/{id}/               → Delete campaign (soft)
GET    /campaigns/{id}/batches/       → Get campaign batches
GET    /campaigns/{id}/leads/         → Get leads in campaign
GET    /campaigns/{id}/analytics/     → Get campaign analytics
```

#### Batch APIs

```
GET    /batches/                      → List batches (with filters)
POST   /batches/                      → Create batch (manual)
GET    /batches/{id}/                 → Get batch details
PUT    /batches/{id}/                 → Update batch
GET    /batches/{id}/leads/           → Get leads in batch
GET    /batches/{id}/status/          → Get import status
POST   /batches/{id}/retry-import/    → Retry failed imports
GET    /batches/{id}/logs/            → Get import logs
```

#### Lead APIs (Core)

```
GET    /leads/                        → List leads (with advanced filters)
POST   /leads/                        → Create lead manually
GET    /leads/{id}/                   → Get lead details
PUT    /leads/{id}/                   → Update lead
DELETE /leads/{id}/                   → Soft delete lead
GET    /leads/{id}/activities/        → Get lead activities
GET    /leads/{id}/notes/             → Get lead notes
GET    /leads/{id}/attachments/       → Get lead attachments
GET    /leads/{id}/history/           → Get lead change history
POST   /leads/{id}/assign/            → Assign lead to user
POST   /leads/{id}/reassign/          → Reassign lead
POST   /leads/{id}/add-note/          → Add note to lead
POST   /leads/{id}/change-status/     → Change lead status
POST   /leads/{id}/mark-duplicate/    → Mark as duplicate
GET    /leads/search/                 → Advanced search (phone, email, PAN)
GET    /leads/duplicates/             → Get potential duplicates
GET    /leads/export/                 → Export leads (Excel)
POST   /leads/bulk-import/            → Initiate bulk import
```

#### Bulk Import APIs

```
POST   /imports/excel/                → Upload Excel file
GET    /imports/excel/{id}/status/    → Get import status
GET    /imports/excel/{id}/logs/      → Get import logs
POST   /imports/pdf/                  → Upload PDF file
GET    /imports/pdf/{id}/status/      → Get PDF extraction status
POST   /imports/images/               → Upload images
GET    /imports/{id}/preview/         → Preview import data
POST   /imports/{id}/confirm/         → Confirm and process import
```

#### Activity APIs

```
GET    /activities/                   → List activities (with filters)
POST   /activities/                   → Create activity
GET    /activities/{id}/              → Get activity details
PUT    /activities/{id}/              → Update activity
DELETE /activities/{id}/              → Cancel activity
POST   /activities/{id}/complete/     → Mark as completed
GET    /activities/scheduled/         → Get upcoming activities
GET    /activities/overdue/           → Get overdue activities
POST   /activities/bulk-create/       → Create multiple activities
```

#### Outcome APIs

```
GET    /outcomes/                     → List outcomes
POST   /outcomes/                     → Create outcome
GET    /outcomes/{id}/                → Get outcome details
PUT    /outcomes/{id}/                → Update outcome
GET    /leads/{lead_id}/outcomes/     → Get outcomes for lead
```

#### Notes APIs

```
GET    /notes/                        → List notes
POST   /notes/                        → Create note
GET    /notes/{id}/                   → Get note details
PUT    /notes/{id}/                   → Update note
DELETE /notes/{id}/                   → Delete note
GET    /leads/{lead_id}/notes/        → Get notes for lead
```

#### Analytics & Reports APIs

```
GET    /analytics/dashboard/          → Overall metrics
GET    /analytics/daily-report/       → Daily summary
GET    /analytics/employee/           → Employee performance
GET    /analytics/employee/{id}/      → Specific employee analytics
GET    /analytics/source/             → Source-wise analytics
GET    /analytics/source/{bank_id}/   → Specific source analytics
GET    /reports/                      → List all reports
POST   /reports/generate/             → Generate custom report
GET    /reports/{id}/                 → Get report details
POST   /reports/{id}/download/        → Download report (Excel/PDF)
GET    /analytics/conversion-rate/    → Conversion metrics
GET    /analytics/sla-status/         → SLA compliance
GET    /analytics/team-performance/   → Team-wise metrics
```

#### Audit APIs

```
GET    /audit-logs/                   → List audit logs
GET    /audit-logs/user/{user_id}/    → Logs for specific user
GET    /audit-logs/model/{model_name}/→ Logs for specific model
GET    /audit-logs/record/{record_id}/→ Logs for specific record
POST   /audit-logs/export/            → Export audit logs
```

#### Notification APIs

```
GET    /notifications/                → Get user notifications
POST   /notifications/                → Create notification
PUT    /notifications/{id}/read/      → Mark as read
DELETE /notifications/{id}/           → Delete notification
POST   /notifications/mark-all-read/  → Mark all as read
GET    /notifications/settings/       → Get notification preferences
PUT    /notifications/settings/       → Update preferences
```

---

### 7.3 Query Parameters & Filters

#### Common Query Parameters

```
GET /leads/?
  page=1                             # Pagination
  page_size=20
  ordering=-created_at               # -field for DESC
  search=john%20doe                  # Full-text search
  filters[status]=Converted          # Status filter
  filters[city]=Mumbai               # City filter
  filters[assigned_to]=5             # Assigned user filter
  filters[created_after]=2026-01-01  # Date range
  filters[created_before]=2026-12-31
  include_deleted=false              # Include soft-deleted
  export=csv|excel                   # Export format

GET /activities/?
  filters[status]=Scheduled
  filters[activity_type]=Call
  filters[assigned_to]=5
  filters[due_date_after]=2026-06-10
  filters[due_date_before]=2026-06-30
```

---

### 7.4 API Rate Limiting

```
Tier 1 (Regular Users): 100 requests/minute
Tier 2 (Team Leads): 200 requests/minute
Tier 3 (Admins): Unlimited

Rate-Limit Headers:
X-RateLimit-Limit
X-RateLimit-Remaining
X-RateLimit-Reset
```

---

## 8. Security Architecture

### 8.1 Authentication Strategy

#### Multi-Layer Authentication

```
Layer 1: Session-Based (Web UI)
├── Django session framework
├── CSRF protection on forms
├── Secure cookies (HttpOnly, Secure, SameSite)
└── Session timeout: 24 hours

Layer 2: Token-Based (API - Future)
├── JWT (JSON Web Tokens)
├── Token expiration: 1 hour
├── Refresh token: 7 days
├── Token stored in HTTP-only cookie
└── No localStorage/sessionStorage for sensitive tokens

Layer 3: API Key (Backend Integrations - Future)
├── Long-lived API keys for backend services
├── Key rotation mechanism
├── Scoped permissions per key
└── Rate limiting per key
```

#### Password Security

```
Requirements:
├── Minimum 12 characters
├── Mix of uppercase, lowercase, numbers, special chars
├── Not in common password dictionary
├── No username/email in password
└── Change every 90 days (policy enforced)

Storage:
├── PBKDF2 with SHA-256 (Django default)
├── Minimum 260,000 iterations (updated yearly)
└── No reversible encryption
```

---

### 8.2 Authorization Strategy (RBAC)

#### Role Hierarchy

```
SuperAdmin (Highest)
├── All permissions
├── User management
├── System configuration
├── Audit log access
└── Full financial reports

TeamLead
├── Manage team members
├── View team performance
├── Assign leads
├── Generate team reports
├── View team analytics
├── Edit own profile
└── Limited user management (team only)

Caller
├── View assigned leads
├── Update lead status
├── Create activities
├── Add notes
├── View own activities
├── View own performance
└── Cannot assign leads

DataEntryOperator
├── Create leads (bulk import)
├── Upload Excel/PDF/Images
├── View import status
├── Edit lead contact details (initial data)
├── Cannot assign leads
└── Cannot change lead status
```

#### Permission Matrix

```
|                    | SuperAdmin | TeamLead | Caller | DataEntry |
|-------------------|-----------|----------|--------|-----------|
| User Management    | Full      | Team     | None   | None      |
| Lead Create        | Full      | Full     | Manual | Bulk      |
| Lead Edit          | Full      | Own Assign| Assign | Initial   |
| Lead Delete        | Full      | None     | None   | None      |
| Activity Manage    | Full      | Team     | Own    | None      |
| Assignment         | Full      | Own Team | None   | None      |
| Reports            | Full      | Team     | Self   | None      |
| Audit Logs         | Full      | None     | None   | None      |
| Settings           | Full      | None     | None   | None      |
| Financial Data     | Full      | None     | None   | None      |
```

---

### 8.3 Data Security

#### Data Protection

```
At Rest:
├── Database encryption (PostgreSQL pgcrypto)
├── Sensitive fields: Phone, Email, PAN (encrypted in DB)
├── File storage: Encrypted directories
└── Backup encryption

In Transit:
├── HTTPS only (TLS 1.3+)
├── HSTS headers
├── Secure cookies
└── No data in URLs

Sensitive Fields:
├── PAN Number: Encrypted
├── Phone: Encrypted
├── Email: Encrypted (limited)
├── Bank Details: Encrypted
├── Loan Amount: Masked in UI (show only last 4 digits in summaries)
└── Personal Address: Encrypted
```

#### Data Classification

```
Level 1 (Public):
├── Lead Status
├── Campaign Names
└── General Statistics

Level 2 (Internal):
├── Lead Names
├── Activity Types
├── Notes (non-sensitive)
└── Department Info

Level 3 (Confidential):
├── Phone Numbers
├── Email Addresses
├── PAN Numbers
├── Loan Amounts
├── Bank Details
├── Personal Addresses
└── Activity Details

Level 4 (Highly Confidential):
├── Password Hashes
├── Authentication Tokens
├── Credit Scores (if stored)
└── Financial Data
```

---

### 8.4 Access Control & Data Masking

#### Field-Level Access Control

```
Phone Number:
├── SuperAdmin: Full visibility
├── TeamLead: Full visibility
├── Caller: Full visibility
├── DataEntry: Full visibility (for import)
└── Other users: Hidden

Email:
├── SuperAdmin: Full visibility
├── TeamLead: Full visibility (team leads)
├── Caller: Full visibility (assigned)
└── Others: Hidden

PAN Number:
├── SuperAdmin: Full visibility
├── Others: Last 4 digits only (XXXX-XXXX-PAN)

Loan Amount:
├── SuperAdmin: Full amount
├── TeamLead: Full amount (team leads)
├── Caller: Full amount (assigned)
└── DataEntry: Full (import phase)
```

#### Row-Level Security (Record Access)

```
SuperAdmin:
└── All records

TeamLead:
├── Own records
├── Team members' records
└── Assigned leads

Caller:
├── Own activities
├── Assigned leads only
└── Own notes

DataEntry:
├── Imported batches
└── Records they created
```

---

### 8.5 API Security

#### Request Validation

```
Input Validation:
├── CSRF tokens on all state-changing requests
├── Content-Type validation
├── JSON schema validation
├── File type validation (Excel, PDF, Image)
├── File size limits (10MB per file)
└── Rate limiting per user/IP

CORS Configuration:
├── Allow only trusted domains
├── Credentials: true (if cross-domain)
├── Methods: GET, POST, PUT, DELETE, OPTIONS
└── Headers: Authorization, Content-Type
```

#### Error Handling

```
Error Responses:
├── 400 Bad Request: Invalid input
├── 401 Unauthorized: Missing auth
├── 403 Forbidden: Insufficient permissions
├── 404 Not Found: Record not found
├── 429 Too Many Requests: Rate limit exceeded
└── 500 Server Error: No sensitive info

Error Logging:
├── Log all errors with request ID
├── Stack traces (dev only)
├── Never expose sensitive data in errors
└── User-friendly error messages
```

---

## 9. Permissions & RBAC

### 9.1 Permission Groups

#### Built-in Permission Groups

```
Leads Managers
├── add_lead
├── change_lead
├── delete_lead
├── view_lead
├── assign_lead
└── export_leads

Activity Managers
├── add_activity
├── change_activity
├── delete_activity
├── view_activity
└── bulk_create_activity

Reports Access
├── view_reports
├── generate_reports
├── export_reports
└── view_analytics

Audit Access
├── view_audit_logs
├── export_audit_logs
└── (SuperAdmin only)

User Management
├── add_user
├── change_user
├── delete_user
├── view_user
├── assign_role
└── (SuperAdmin only)

Settings Management
├── change_settings
├── view_settings
└── (SuperAdmin only)
```

### 9.2 Granular Permissions

```
Lead Permissions:
├── leads.add_lead
├── leads.change_lead
├── leads.delete_lead
├── leads.view_lead
├── leads.assign_lead
├── leads.bulk_import_lead
├── leads.export_lead
└── leads.view_lead_notes

Activity Permissions:
├── activities.add_activity
├── activities.change_activity
├── activities.delete_activity
├── activities.view_activity
├── activities.complete_activity
└── activities.bulk_create

User Permissions:
├── accounts.add_user
├── accounts.change_user
├── accounts.delete_user
├── accounts.view_user
├── accounts.assign_role
└── accounts.change_user_permission

Analytics Permissions:
├── analytics.view_reports
├── analytics.generate_reports
├── analytics.export_reports
├── analytics.view_employee_analytics
└── analytics.view_source_analytics
```

### 9.3 Custom Permission Classes (DRF)

```python
Classes to Implement:
├── IsAuthenticated
├── IsTeamLead
├── IsSuperAdmin
├── IsAssignedUser
├── CanEditLead
├── CanAssignLead
├── CanViewAuditLogs
├── CanGenerateReports
├── IsOwner (for own records)
└── HasLeadAccess (row-level)
```

---

## 10. Integration Points

### 10.1 App Communication

#### Direct Imports

```
leads app
├── → accounts (User, UserProfile)
├── → activities (Activity creation on status change)
├── → notifications (Notify on assignment)
└── → audit (Log all changes)

activities app
├── → leads (Lead reference)
├── → accounts (User assignments)
├── → notifications (Remind about activities)
└── → audit (Log completions)

analytics app
├── → leads (Read-only for aggregation)
├── → activities (For KPIs)
├── → accounts (User data)
└── → audit (For audit reports)

excel, pdf, imager apps
├── → leads (Create leads from import)
├── → accounts (Track uploader)
└── → notifications (Notify on completion)
```

#### Django Signals

```
Post-Save Signals:
├── Lead.post_save → Create audit log
├── Activity.post_save → Create notification
├── LeadAssignment.post_save → Notify user
└── Batch.post_save → Trigger import processing

Post-Delete Signals:
├── Lead.post_delete → Create audit log (soft delete)
└── Activity.post_delete → Clean up notifications

Custom Signals:
├── lead_status_changed
├── lead_assigned
├── activity_completed
└── batch_imported
```

---

### 10.2 Celery Tasks Integration

#### Async Task Queue

```
Import Tasks:
├── process_excel_import.delay()
├── process_pdf_import.delay()
├── process_image_import.delay()
└── handle_import_failure.delay()

Report Generation:
├── generate_daily_report.delay()
├── generate_employee_analytics.delay()
├── generate_source_analytics.delay()
└── export_leads.delay()

Notification Tasks:
├── send_activity_reminder.delay()
├── send_assignment_notification.delay()
└── send_bulk_emails.delay()

Maintenance Tasks:
├── cleanup_old_audit_logs.delay()
├── cleanup_temp_files.delay()
├── deactivate_old_batches.delay()
└── archive_completed_campaigns.delay()

Scheduled Tasks (Celery Beat):
├── generate_daily_report (every 11:59 PM)
├── cleanup_temp_files (every 24 hours)
├── send_overdue_activity_reminders (every 8 AM)
└── calculate_employee_daily_stats (every 6 AM)
```

---

## 11. Scalability & Future Growth

### 11.1 Database Optimization

#### Indexing Strategy

```
Composite Indexes:
├── leads: (batch_id, lead_status)
├── leads: (customer_name, phone)
├── leads: (phone, email)
├── activities: (lead_id, scheduled_date)
├── activities: (assigned_to, status)
├── audit_logs: (user_id, timestamp)
└── batch: (campaign_id, import_status)

Partial Indexes:
├── leads: WHERE is_deleted = false
├── batches: WHERE import_status = 'Processing'
├── notifications: WHERE is_read = false
└── activities: WHERE status != 'Completed'

JSONB Indexes:
├── audit_logs: GIN index on old_values, new_values
└── batch: GIN index on error_log
```

#### Query Optimization

```
Strategies:
├── Select_related: ForeignKey relationships
├── Prefetch_related: ManyToMany relationships
├── Only/Defer: Load specific fields
├── Aggregate functions: COUNT, SUM at database level
├── Database views: For complex analytics queries
├── Materialized views: For frequently accessed reports
└── Connection pooling: PgBouncer for high concurrency
```

#### Partitioning Strategy (Future)

```
Activity Table (By date):
├── Partition by month
└── Archive yearly

Lead Table (By campaign):
├── Partition by campaign_id
└── Partition by year

Audit Log (By date):
├── Partition by year
└── Archive older data
```

---

### 11.2 Caching Strategy

#### Redis Cache Layers

```
Session Cache:
├── Django sessions
├── Cache duration: 24 hours
└── Key: sessionid:{session_id}

User Data Cache:
├── User profile data
├── Permissions
├── Cache duration: 1 hour
└── Key: user:{user_id}

Lead Cache:
├── Lead details
├── Cache duration: 15 minutes
└── Key: lead:{lead_id}

Report Cache:
├── Daily reports
├── Analytics data
├── Cache duration: 1 hour
└── Key: report:{type}:{date}

Statistics Cache:
├── Daily stats
├── Employee metrics
├── Cache duration: 5 minutes
└── Key: stats:{date}

Search Cache:
├── Duplicate detection results
├── Cache duration: 30 minutes
└── Key: duplicate_search:{hash}
```

#### Cache Invalidation

```
On Create:
├── Invalidate list cache
└── Invalidate stats

On Update:
├── Invalidate object cache
├── Invalidate list cache
└── Invalidate stats/reports

On Delete:
├── Invalidate object cache
├── Invalidate list cache
└── Invalidate stats/reports

Scheduled:
├── Clear old caches (hourly)
└── Rebuild important caches (daily)
```

---

### 11.3 Performance Targets

```
API Response Times:
├── List endpoints: < 500ms
├── Detail endpoints: < 300ms
├── Create: < 1 second
├── Update: < 1 second
├── Bulk import: < 2 minutes per 1000 records
└── Report generation: < 5 minutes

Database Targets:
├── Query execution: < 100ms (p95)
├── Connection pool: 20-50 connections
└── Avg queries per request: < 5

Infrastructure Targets:
├── CPU usage: < 70%
├── Memory usage: < 80%
├── Disk I/O: < 60%
└── Network bandwidth: < 70%
```

---

### 11.4 High Availability Architecture (Future)

```
Frontend:
├── Multiple web servers (Load balanced)
├── CDN for static files
└── SSL/TLS with auto-renewal

Backend:
├── Multiple app servers (Load balanced)
├── Horizontal scaling with Docker
├── Auto-scaling based on load
└── Blue-green deployment

Database:
├── Master-Slave replication
├── Automated backups (hourly)
├── Point-in-time recovery
├── Read replicas for analytics
└── Connection pooling

Cache:
├── Redis cluster
├── Sentinel for failover
└── Persistent storage (RDB + AOF)

File Storage:
├── Object storage (S3/GCS)
├── CDN distribution
└── Backup to separate region
```

---

### 11.5 Monitoring & Alerting

```
Application Monitoring:
├── Error rates (target: < 1%)
├── Response times (p50, p95, p99)
├── Active users
├── API endpoint performance
└── Task queue health

Database Monitoring:
├── Query performance
├── Slow query log
├── Connection count
├── Disk usage
└── Replication lag

Infrastructure Monitoring:
├── CPU/Memory/Disk
├── Network I/O
├── Container health
└── Load balancer status

Alerts:
├── Error rate > 5%
├── Response time > 1000ms
├── Database down
├── Low disk space (< 10%)
├── High memory usage (> 80%)
├── Failed task queue
└── Backup failure
```

---

### 11.6 Capacity Planning

```
Current Scale:
├── Expected users: 50-100
├── Expected leads: 100K-500K/year
├── Expected requests/day: 10K-50K
└── Database size: 10-50 GB (year 1)

1 Year Growth Target:
├── Users: 200-500
├── Leads: 1M+/year
├── Requests/day: 100K-500K
└── Database size: 50-200 GB

Scaling Approach:
├── Vertical scaling (current)
├── Horizontal scaling (after 1 year)
├── Data archiving (after 2 years)
└── Multi-region deployment (after 3 years)
```

---

## Appendix: Technology Stack Justification

| Component  | Choice                         | Rationale                                                    |
| ---------- | ------------------------------ | ------------------------------------------------------------ |
| Framework  | Django 4.2+                    | Enterprise-grade, batteries-included, RBAC support           |
| API        | Django REST Framework          | Industry standard, strong community, excellent documentation |
| Database   | PostgreSQL                     | ACID compliance, JSON support, excellent performance         |
| Cache      | Redis                          | Fast, in-memory, supports multiple data types                |
| Task Queue | Celery                         | Distributed, fault-tolerant, Pythonic                        |
| Front-end  | Django Templates + Bootstrap 5 | Server-rendered, quick development, responsive               |
| JS         | Vanilla JS                     | No heavy framework overhead, good for CRUD operations        |
| Testing    | pytest                         | Better than unittest, fixtures, plugins                      |
| Deployment | Docker                         | Containerization, environment consistency                    |
| Monitoring | (To be decided)                | Sentry for errors, Prometheus for metrics (future)           |

---

## Document Metadata

- **Version**: 1.0
- **Last Updated**: 2026-06-10
- **Next Review**: 2026-07-10
- **Prepared For**: Development Team
- **Status**: Ready for Implementation
- **Approval**: Pending

---

**End of Architecture Document**

This architecture provides a solid foundation for building a scalable, secure, and maintainable Loan Lead Management CRM. It emphasizes best practices in security, scalability, and maintainability without prescribing specific implementation details.
