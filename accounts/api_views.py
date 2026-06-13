from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import Role, UserProfile
from .serializers import (
    UserSerializer, UserDetailSerializer, UserCreateSerializer,
    UserUpdateSerializer, RoleSerializer, UserProfileSerializer,
    UserProfileDetailSerializer, ChangePasswordSerializer,
)
from .permissions import IsSuperAdmin, IsAdminOrTeamLead, IsSelfOrAdmin

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.prefetch_related("profile__role").all()
    permission_classes = [IsAuthenticated]
    search_fields = ["username", "email", "first_name", "last_name", "phone"]
    ordering_fields = ["username", "email", "date_joined", "last_login", "is_active"]
    filterset_fields = ["is_active"]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ("update", "partial_update"):
            return UserUpdateSerializer
        if self.action == "retrieve":
            return UserDetailSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ("create", "destroy", "list"):
            return [IsAuthenticated(), IsSuperAdmin()]
        if self.action in ("update", "partial_update"):
            return [IsAuthenticated(), IsAdminOrTeamLead()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        try:
            role_code = user.profile.role.role_code
            if role_code in ("CALLER", "ARO"):
                qs = qs.filter(id=user.id)
            elif role_code == "TEAM_LEAD":
                from .models import UserProfile
                profile = user.profile
                team = UserProfile.objects.filter(manager=profile).values_list("user_id", flat=True)
                qs = qs.filter(id__in=list(team) + [user.id])
            elif role_code == "MANAGER":
                from .models import UserProfile
                profile = user.profile
                team = UserProfile.objects.filter(manager=profile).values_list("user_id", flat=True)
                sub = UserProfile.objects.filter(manager__in=UserProfile.objects.filter(manager=profile)).values_list("user_id", flat=True)
                qs = qs.filter(id__in=list(team) + list(sub) + [user.id])
        except Exception:
            qs = qs.none()
        return qs

    @action(detail=True, methods=["post"])
    def change_password(self, request, pk=None):
        user = self.get_object()
        if user != request.user:
            return Response({"error": "You can only change your own password."}, status=status.HTTP_403_FORBIDDEN)
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not user.check_password(serializer.validated_data["old_password"]):
            return Response({"old_password": "Wrong password."}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(serializer.validated_data["new_password"])
        user.save()
        return Response({"status": "Password changed."})

    @action(detail=True, methods=["post"])
    def toggle_active(self, request, pk=None):
        user = self.get_object()
        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])
        return Response({"is_active": user.is_active})


class RoleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Role.objects.filter(is_active=True)
    permission_classes = [IsAuthenticated]
    serializer_class = RoleSerializer
    search_fields = ["name", "role_code"]
    ordering_fields = ["name", "role_code"]


class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.select_related("user", "role", "manager").all()
    permission_classes = [IsAuthenticated]
    search_fields = ["user__username", "user__email", "department", "role__name"]
    ordering_fields = ["user__username", "department", "role__name"]
    filterset_fields = ["department", "role", "is_active"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return UserProfileDetailSerializer
        return UserProfileSerializer

    def get_permissions(self):
        if self.action in ("create", "destroy"):
            return [IsAuthenticated(), IsSuperAdmin()]
        if self.action in ("update", "partial_update"):
            return [IsAuthenticated(), IsAdminOrTeamLead()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        try:
            role_code = user.profile.role.role_code
            if role_code in ("CALLER", "ARO"):
                qs = qs.filter(user=user)
            elif role_code == "TEAM_LEAD":
                qs = qs.filter(manager=user.profile) | qs.filter(user=user)
            elif role_code == "MANAGER":
                team_lead_profiles = UserProfile.objects.filter(manager=user.profile)
                aro_profiles = UserProfile.objects.filter(manager__in=team_lead_profiles)
                qs = qs.filter(
                    Q(pk=user.profile.pk) |
                    Q(pk__in=team_lead_profiles.values_list("pk", flat=True)) |
                    Q(pk__in=aro_profiles.values_list("pk", flat=True))
                )
        except Exception:
            pass
        return qs


class CurrentUserView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserDetailSerializer

    def get_object(self):
        return self.request.user
