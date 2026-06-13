from django.urls import path
from . import views

app_name = "documents"

urlpatterns = [
    # Batches
    path("", views.BatchListView.as_view(), name="batch_list"),
    path("batch/<uuid:pk>/", views.BatchDetailView.as_view(), name="batch_detail"),

    # PDF Upload
    path("pdf/upload/", views.PDFUploadView.as_view(), name="pdf_upload"),

    # Image Upload
    path("images/upload/", views.ImageUploadView.as_view(), name="image_upload"),

    # Excel Upload
    path("excel/upload/", views.ExcelUploadView.as_view(), name="excel_upload"),

    # Work Items
    path("work-item/<uuid:pk>/", views.WorkItemDetailView.as_view(), name="workitem_detail"),
    path("work-item/<uuid:pk>/assign/", views.WorkItemAssignView.as_view(), name="workitem_assign"),
    path("work-item/<uuid:pk>/status/", views.WorkItemStatusUpdateView.as_view(), name="workitem_status"),
    path("work-item/<uuid:pk>/notes/add/", views.WorkItemNoteCreateView.as_view(), name="workitem_note_add"),
    path("work-item/<uuid:pk>/revert/", views.WorkItemRevertView.as_view(), name="workitem_revert"),
    path("work-item/bulk-assign/", views.BulkAssignView.as_view(), name="workitem_bulk_assign"),

    # File serving
    path("work-item/<uuid:pk>/preview/", views.PagePreviewView.as_view(), name="page_preview"),
    path("work-item/<uuid:pk>/image/", views.ImagePreviewView.as_view(), name="image_preview"),
    path("work-item/<uuid:pk>/image/download/", views.OriginalImageDownloadView.as_view(), name="image_download"),
    path("batch/<uuid:pk>/download/", views.OriginalPDFDownloadView.as_view(), name="batch_download"),

    # Work Queue
    path("my-work/", views.WorkQueueView.as_view(), name="work_queue"),

    # Revert attachment
    path("revert/<uuid:pk>/attachment/", views.RevertAttachmentDownloadView.as_view(), name="revert_attachment"),
]
