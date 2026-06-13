from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from .api_views import UserViewSet, RoleViewSet, UserProfileViewSet, CurrentUserView

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="api_user")
router.register(r"roles", RoleViewSet, basename="api_role")
router.register(r"profiles", UserProfileViewSet, basename="api_profile")

app_name = "accounts_api"

urlpatterns = [
    path("", include(router.urls)),
    path("auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("auth/me/", CurrentUserView.as_view(), name="current_user"),
]
