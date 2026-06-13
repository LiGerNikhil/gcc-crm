from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Count, F
from .models import Lead, LeadAssignment, LeadStatusLog, AssignmentRule, RoundRobinCounter


def assign_lead_manual(lead, assigned_to, assigned_by=None):
    with transaction.atomic():
        _close_active_assignments(lead)
        assignment = LeadAssignment.objects.create(
            lead=lead,
            assigned_to=assigned_to,
            assigned_by=assigned_by,
            assignment_type="MANUAL",
        )
        _update_lead_assignment(lead, assigned_to)
    return assignment


def assign_lead_bulk(lead_ids, assigned_to, assigned_by=None):
    leads = Lead.objects.filter(id__in=lead_ids, is_deleted=False)
    results = []
    with transaction.atomic():
        for lead in leads:
            try:
                _close_active_assignments(lead)
                assignment = LeadAssignment.objects.create(
                    lead=lead,
                    assigned_to=assigned_to,
                    assigned_by=assigned_by,
                    assignment_type="BULK",
                )
                _update_lead_assignment(lead, assigned_to)
                results.append({"lead_id": str(lead.id), "success": True})
            except Exception as e:
                results.append({"lead_id": str(lead.id), "success": False, "error": str(e)})
    return results


def assign_round_robin(lead_ids, rule_id, assigned_by=None):
    rule = AssignmentRule.objects.select_related("team_lead").get(id=rule_id)
    if not rule.is_active:
        raise ValueError("Assignment rule is not active")

    callers = list(
        RoundRobinCounter.objects.filter(rule=rule)
        .select_related("caller")
        .order_by("current_index")
    )
    if not callers:
        raise ValueError("No callers configured in this rule")

    leads = Lead.objects.filter(id__in=lead_ids, is_deleted=False)
    results = []
    num_callers = len(callers)

    with transaction.atomic():
        for idx, lead in enumerate(leads):
            caller_entry = callers[idx % num_callers]
            caller = caller_entry.caller

            active_count = LeadAssignment.objects.filter(
                assigned_to=caller, assignment_status="ACTIVE"
            ).count()
            if active_count >= rule.max_active_leads:
                results.append({
                    "lead_id": str(lead.id), "success": False,
                    "error": f"Caller {caller.username} at max capacity ({rule.max_active_leads})",
                    "assigned_to": None,
                })
                continue

            _close_active_assignments(lead)
            assignment = LeadAssignment.objects.create(
                lead=lead,
                assigned_to=caller,
                assigned_by=assigned_by,
                assignment_type="AUTO_ROUND_ROBIN",
            )
            _update_lead_assignment(lead, caller)

            caller_entry.assigned_count = F("assigned_count") + 1
            caller_entry.last_assigned_at = timezone.now()
            caller_entry.save(update_fields=["assigned_count", "last_assigned_at"])

            results.append({
                "lead_id": str(lead.id), "success": True,
                "assigned_to": str(caller.id),
                "assigned_to_name": caller.get_full_name() or caller.username,
            })

        _advance_round_robin_counters(callers, leads.count(), num_callers)

    return results, rule


def _advance_round_robin_counters(callers, lead_count, num_callers):
    for i, entry in enumerate(callers):
        new_index = (entry.current_index + lead_count) % num_callers
        RoundRobinCounter.objects.filter(id=entry.id).update(current_index=new_index)


def reassign_lead(lead, new_assigned_to, assigned_by=None, reason=""):
    with transaction.atomic():
        previous = LeadAssignment.objects.filter(
            lead=lead, assignment_status="ACTIVE"
        ).first()
        if previous:
            previous.assignment_status = "TRANSFERRED"
            previous.end_date = timezone.now()
            previous.reason_for_transfer = reason
            previous.save(update_fields=["assignment_status", "end_date", "reason_for_transfer"])

        assignment = LeadAssignment.objects.create(
            lead=lead,
            assigned_to=new_assigned_to,
            assigned_by=assigned_by,
            assignment_type="REASSIGNMENT",
        )
        _update_lead_assignment(lead, new_assigned_to)
    return assignment


def get_available_callers(team_lead=None, rule_id=None):
    from accounts.models import User

    qs = User.objects.filter(is_active=True, profile__is_active=True)
    if team_lead:
        from accounts.models import UserProfile
        team = UserProfile.objects.filter(manager__user=team_lead).values_list("user_id", flat=True)
        qs = qs.filter(
            Q(id__in=team) | Q(id=team_lead.id)
        )
    if rule_id:
        rule = AssignmentRule.objects.get(id=rule_id)
        caller_ids = RoundRobinCounter.objects.filter(rule=rule).values_list("caller_id", flat=True)
        qs = qs.filter(id__in=caller_ids)
    return qs.filter(profile__role__role_code="CALLER").order_by("username")


def get_caller_load(caller):
    return LeadAssignment.objects.filter(
        assigned_to=caller, assignment_status="ACTIVE"
    ).count()


def get_team_load(team_lead):
    from accounts.models import UserProfile
    team = UserProfile.objects.filter(manager__user=team_lead).values_list("user_id", flat=True)
    return {
        str(u["assigned_to"]): u["count"]
        for u in LeadAssignment.objects.filter(
            assigned_to__in=team, assignment_status="ACTIVE"
        ).values("assigned_to").annotate(count=Count("id"))
    }


def setup_round_robin_rule(rule, caller_ids):
    rule.round_robin_counters.all().delete()
    entries = []
    for idx, caller_id in enumerate(caller_ids):
        from accounts.models import User
        caller = User.objects.get(id=caller_id)
        entries.append(RoundRobinCounter(
            rule=rule, caller=caller, current_index=idx,
        ))
    RoundRobinCounter.objects.bulk_create(entries)
    return entries


def get_assignment_history(lead=None, assigned_to=None, limit=50):
    qs = LeadAssignment.objects.select_related(
        "lead", "assigned_to", "assigned_by"
    )
    if lead:
        qs = qs.filter(lead=lead)
    if assigned_to:
        qs = qs.filter(assigned_to=assigned_to)
    return qs.order_by("-created_at")[:limit]


def get_assignment_stats(team_lead=None):
    qs = LeadAssignment.objects.filter(assignment_status="ACTIVE")
    if team_lead:
        from accounts.models import UserProfile
        team = UserProfile.objects.filter(manager__user=team_lead).values_list("user_id", flat=True)
        qs = qs.filter(assigned_to__in=team)
    return {
        "total_active": qs.count(),
        "by_type": dict(
            qs.values("assignment_type").annotate(count=Count("id"))
            .values_list("assignment_type", "count")
        ),
    }


def _close_active_assignments(lead):
    previous = LeadAssignment.objects.filter(lead=lead, assignment_status="ACTIVE")
    for pa in previous:
        pa.assignment_status = "COMPLETED"
        pa.end_date = timezone.now()
        pa.save(update_fields=["assignment_status", "end_date"])


def _update_lead_assignment(lead, assigned_to):
    lead.assigned_to = assigned_to
    lead.assigned_at = timezone.now()
    if lead.lead_status == "NEW":
        lead.lead_status = "ASSIGNED"
    lead.save(update_fields=["assigned_to", "assigned_at", "lead_status", "updated_at"])


# Preserved aliases for backward compatibility
def assign_lead(lead, assigned_to, assigned_by=None):
    return assign_lead_manual(lead, assigned_to, assigned_by)


def bulk_assign(lead_ids, assigned_to, assigned_by=None):
    return assign_lead_bulk(lead_ids, assigned_to, assigned_by)


def change_lead_status(lead, new_status, changed_by=None, notes=""):
    old_status = lead.lead_status
    if old_status == new_status:
        return False
    with transaction.atomic():
        lead.lead_status = new_status
        lead.save(update_fields=["lead_status", "updated_at"])
        LeadStatusLog.objects.create(
            lead=lead,
            old_status=old_status,
            new_status=new_status,
            changed_by=changed_by,
            notes=notes,
        )
    return True


def get_lead_stats():
    from django.db.models import Count
    return {
        "total": Lead.objects.filter(is_deleted=False).count(),
        **{
            entry["lead_status"]: entry["count"]
            for entry in Lead.objects.filter(is_deleted=False)
            .values("lead_status")
            .annotate(count=Count("id"))
        },
    }


def get_caller_leads(user):
    return Lead.objects.filter(
        assigned_to=user,
        is_deleted=False,
    ).select_related("batch__campaign__bank_source")


def get_team_leads(user):
    from accounts.models import UserProfile
    try:
        profile = user.profile
        team = UserProfile.objects.filter(manager=profile).values_list("user_id", flat=True)
        return Lead.objects.filter(
            Q(assigned_to__in=team) | Q(assigned_to=user),
            is_deleted=False
        ).select_related("assigned_to", "batch__campaign__bank_source")
    except Exception:
        return get_caller_leads(user)


def _user_name(user):
    if user:
        return user.get_full_name() or user.username
    return None


def get_lead_timeline(lead, limit=100):
    """Aggregate all lead events into a chronological timeline."""
    events = []

    # Status changes
    for log in lead.status_logs.select_related("changed_by").all():
        events.append({
            "timestamp": log.created_at,
            "event_type": "status_change",
            "title": f"Status changed: {log.old_status or 'NEW'} → {log.new_status}",
            "description": log.notes,
            "user": log.changed_by,
            "user_name": _user_name(log.changed_by),
            "icon": "bi-arrow-repeat",
            "color": "primary",
            "url": None,
            "sort_key": log.created_at,
        })

    # Notes
    for note in lead.lead_notes.select_related("created_by").all():
        events.append({
            "timestamp": note.created_at,
            "event_type": "note",
            "title": f"{note.get_note_type_display()} note",
            "description": note.content[:500],
            "user": note.created_by,
            "user_name": _user_name(note.created_by),
            "icon": "bi-sticky",
            "color": "info",
            "url": None,
            "sort_key": note.created_at,
        })

    # Follow-ups
    for fup in lead.lead_followups.select_related("assigned_to", "created_by").all():
        events.append({
            "timestamp": fup.created_at,
            "event_type": "followup",
            "title": f"Follow-up ({fup.get_followup_type_display()}) — {fup.get_status_display()}",
            "description": fup.notes,
            "user": fup.created_by,
            "user_name": _user_name(fup.created_by),
            "icon": "bi-calendar-check",
            "color": "warning",
            "url": None,
            "sort_key": fup.created_at,
        })

    # Assignments
    for a in get_assignment_history(lead=lead):
        events.append({
            "timestamp": a.created_at,
            "event_type": "assignment",
            "title": f"Assigned to {a.assigned_to.get_full_name() or a.assigned_to.username} ({a.get_assignment_type_display()})",
            "description": a.reason_for_transfer or "",
            "user": a.assigned_by,
            "user_name": _user_name(a.assigned_by),
            "icon": "bi-person-check",
            "color": a.assignment_type,
            "url": None,
            "sort_key": a.created_at,
        })

    # Calls
    try:
        for call in lead.calls.select_related("caller").all():
            events.append({
                "timestamp": call.call_time,
                "event_type": "call",
                "title": f"{call.get_call_type_display()} call ({call.get_call_status_display()}) — {call.duration_seconds}s",
                "description": call.notes,
                "user": call.caller,
                "user_name": _user_name(call.caller),
                "icon": "bi-telephone",
                "color": "success",
                "url": call.recording_url or None,
                "sort_key": call.call_time,
            })
    except AttributeError:
        pass

    # Documents (from imager app)
    try:
        from imager.models import DocumentImage
        for doc in DocumentImage.objects.filter(lead=lead).select_related("verified_by", "image").all():
            events.append({
                "timestamp": doc.created_at,
                "event_type": "document",
                "title": f"Document uploaded: {doc.get_document_type_display()}",
                "description": f"Status: {doc.get_verification_status_display()}. {doc.remarks or ''}",
                "user": doc.verified_by,
                "user_name": _user_name(doc.verified_by),
                "icon": "bi-file-earmark-text",
                "color": "secondary",
                "url": None,
                "sort_key": doc.created_at,
            })
    except (ImportError, AttributeError):
        pass

    events.sort(key=lambda e: e["sort_key"], reverse=True)
    return events[:limit]
