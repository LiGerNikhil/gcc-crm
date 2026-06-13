from django.utils import timezone
from django.db import transaction

from .models import WorkItem, WorkItemStatus, WorkTimeline

# ── Valid Status Transitions ──────────────────────────────────
# Maps current_status → set of allowed next statuses

TRANSITIONS = {
    "NEW": {"ASSIGNED", "REJECTED"},
    "ASSIGNED": {"IN_PROGRESS", "NEED_CLARIFICATION", "REJECTED"},
    "IN_PROGRESS": {"PENDING", "NEED_CLARIFICATION", "COMPLETED", "REJECTED"},
    "PENDING": {"IN_PROGRESS", "NEED_CLARIFICATION", "COMPLETED", "REJECTED"},
    "NEED_CLARIFICATION": {"IN_PROGRESS", "PENDING", "REJECTED"},
    "COMPLETED": {"CLOSED", "REJECTED"},
    "REJECTED": {"NEW", "CLOSED"},
    "CLOSED": set(),  # Terminal — no transitions
}

STATUS_ACTION_MAP = {
    "COMPLETED": "COMPLETED",
    "REJECTED": "REJECTED",
    "CLOSED": "CLOSED",
    "NEED_CLARIFICATION": "NEED_CLARIFICATION",
    "PENDING": "PENDING",
    "NEW": "REOPENED" if False else "STATUS_CHANGED",  # handled dynamically
}

HUMAN_LABELS = dict(WorkItem.ITEM_STATUS)


def get_allowed_transitions(status):
    """Return the set of status codes the work item can move to."""
    return TRANSITIONS.get(status, set())


def get_allowed_transition_choices(status):
    """Return list of (code, label) tuples for allowed transitions."""
    allowed = get_allowed_transitions(status)
    return [(c, HUMAN_LABELS[c]) for c in sorted(allowed)]


def is_valid_transition(from_status, to_status):
    """Check if moving from from_status to to_status is allowed."""
    return to_status in TRANSITIONS.get(from_status, set())


def change_status(work_item, new_status, changed_by=None, notes="", is_system=False):
    """Change a work item's status, logging the change in history and timeline.

    Returns the updated work_item.
    Raises ValueError if the transition is invalid.
    """
    if not is_valid_transition(work_item.status, new_status):
        raise ValueError(
            f"Cannot change status from {HUMAN_LABELS.get(work_item.status, work_item.status)} "
            f"to {HUMAN_LABELS.get(new_status, new_status)}."
        )

    old_status = work_item.status

    with transaction.atomic():
        # Update the work item
        work_item.status = new_status
        if new_status == "COMPLETED" and old_status != "COMPLETED":
            work_item.completed_at = timezone.now()
        elif new_status == "REJECTED":
            work_item.completed_at = None
        work_item.save(update_fields=["status", "completed_at"] if new_status in ("COMPLETED", "REJECTED") else ["status"])

        # Log to WorkItemStatus history
        WorkItemStatus.objects.create(
            work_item=work_item,
            status=new_status,
            changed_by=changed_by,
            changed_at=timezone.now(),
            from_status=old_status,
            notes=notes,
            is_system=is_system,
        )

        # Determine timeline action label
        action = STATUS_ACTION_MAP.get(new_status, "STATUS_CHANGED")
        if new_status == "NEW" and old_status == "REJECTED":
            action = "REOPENED"

        # Log to WorkTimeline
        WorkTimeline.objects.create(
            work_item=work_item,
            action=action,
            description=notes or f"Status changed from {HUMAN_LABELS.get(old_status, old_status)} to {HUMAN_LABELS.get(new_status, new_status)}",
            from_status=old_status,
            to_status=new_status,
            performed_by=changed_by,
            timestamp=timezone.now(),
            is_system_generated=is_system,
        )

    return work_item
