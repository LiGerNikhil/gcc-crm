import django_filters
from django.db.models import Q
from .models import Lead


class LeadFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="filter_search")
    status = django_filters.ChoiceFilter(field_name="lead_status", choices=Lead.LEAD_STATUS_CHOICES)
    campaign = django_filters.UUIDFilter(field_name="batch__campaign_id")
    assigned_to = django_filters.UUIDFilter(field_name="assigned_to")
    priority = django_filters.ChoiceFilter(choices=Lead.PRIORITY_CHOICES)
    loan_type = django_filters.ChoiceFilter(choices=Lead.LOAN_TYPE_CHOICES)
    date_from = django_filters.DateFilter(field_name="created_at__date", lookup_expr="gte")
    date_to = django_filters.DateFilter(field_name="created_at__date", lookup_expr="lte")

    class Meta:
        model = Lead
        fields = ["search", "status", "campaign", "assigned_to", "priority", "loan_type"]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(customer_name__icontains=value)
            | Q(phone__icontains=value)
            | Q(email__icontains=value)
            | Q(lead_number__icontains=value)
            | Q(pan_number__icontains=value)
        )
