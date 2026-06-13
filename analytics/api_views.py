from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .services import (
    get_source_wise_stats,
    get_lead_metrics,
    get_employee_metrics,
    get_lead_status_distribution,
    get_monthly_trends,
)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def source_wise_stats(request):
    return Response(get_source_wise_stats())


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def lead_metrics(request):
    return Response(get_lead_metrics())


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def employee_metrics(request):
    return Response(get_employee_metrics())


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def status_distribution(request):
    return Response(get_lead_status_distribution())


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def monthly_trends(request):
    months = int(request.GET.get("months", 6))
    return Response(get_monthly_trends(months))
