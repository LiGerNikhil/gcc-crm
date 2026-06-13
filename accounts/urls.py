from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("password-change/", views.PasswordChangeView.as_view(), name="password_change"),
    path(
        "password-change/done/",
        views.PasswordChangeDoneView.as_view(),
        name="password_change_done",
    ),
    path(
        "password-reset/",
        views.PasswordResetView.as_view(),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        views.PasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "password-reset/confirm/<uidb64>/<token>/",
        views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "password-reset/complete/",
        views.PasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
    path("users/", views.UserListView.as_view(), name="user_list"),
    path("users/create/", views.UserCreateView.as_view(), name="user_create"),
    path("users/<uuid:pk>/edit/", views.UserUpdateView.as_view(), name="user_edit"),
    path(
        "users/<uuid:pk>/toggle-active/",
        views.UserActivateView.as_view(),
        name="user_toggle_active",
    ),
]
