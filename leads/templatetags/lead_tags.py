from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def status_badge(status):
    colors = {
        "NEW": "badge bg-secondary",
        "ASSIGNED": "badge bg-info",
        "IN_PROGRESS": "badge bg-primary",
        "CALLBACK": "badge bg-warning text-dark",
        "INTERESTED": "badge bg-success",
        "DOCUMENTS_REQUESTED": "badge bg-info text-dark",
        "DOCUMENTS_RECEIVED": "badge bg-primary",
        "BANK_LOGIN": "badge bg-warning text-dark",
        "APPROVED": "badge bg-success",
        "REJECTED": "badge bg-danger",
        "DISBURSED": "badge bg-success",
    }
    css = colors.get(status, "badge bg-secondary")
    return mark_safe(f'<span class="{css}">{status.replace("_", " ").title()}</span>')


@register.filter
def priority_badge(priority):
    colors = {
        "HIGH": "badge bg-danger",
        "MEDIUM": "badge bg-warning text-dark",
        "LOW": "badge bg-info",
    }
    css = colors.get(priority, "badge bg-secondary")
    return mark_safe(f'<span class="{css}">{priority.title()}</span>')


@register.filter
def currency(value):
    try:
        return f"₹ {float(value):,.2f}"
    except (ValueError, TypeError):
        return ""


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key) if isinstance(dictionary, dict) else None


@register.simple_tag
def url_with_params(url_name, *args, **kwargs):
    from django.urls import reverse
    params = kwargs.pop("params", {})
    base = reverse(url_name, args=args)
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items() if v)
        return f"{base}?{qs}"
    return base
