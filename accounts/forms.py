import uuid
from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import (
    AuthenticationForm, PasswordChangeForm as AuthPasswordChangeForm,
    PasswordResetForm as AuthPasswordResetForm, SetPasswordForm,
)
from django.utils.translation import gettext_lazy as _
from .models import User, UserProfile, Role


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label=_("Username or Email"),
        widget=forms.TextInput(attrs={
            "class": "form-control", "placeholder": _("Username or Email"),
            "autofocus": True,
        }),
    )
    password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            "class": "form-control", "placeholder": _("Password"),
        }),
    )
    remember_me = forms.BooleanField(
        label=_("Remember Me"),
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def clean(self):
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")
        if username and password:
            user = authenticate(
                self.request, username=username, password=password
            )
            if user is None:
                try:
                    user_obj = User.objects.get(email=username)
                    user = authenticate(
                        self.request, username=user_obj.username,
                        password=password,
                    )
                except User.DoesNotExist:
                    pass
            if user is None:
                raise forms.ValidationError(
                    _("Invalid username/email or password."),
                    code="invalid_login",
                )
            if not user.is_active:
                raise forms.ValidationError(
                    _("This account is inactive."),
                    code="inactive",
                )
            self.user_cache = user
        return self.cleaned_data


class CustomPasswordChangeForm(AuthPasswordChangeForm):
    old_password = forms.CharField(
        label=_("Old Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            "class": "form-control", "placeholder": _("Enter old password"),
        }),
    )
    new_password1 = forms.CharField(
        label=_("New Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            "class": "form-control", "placeholder": _("Enter new password"),
        }),
    )
    new_password2 = forms.CharField(
        label=_("Confirm New Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": _("Confirm new password"),
        }),
    )


class CustomPasswordResetForm(AuthPasswordResetForm):
    email = forms.EmailField(
        label=_("Email"),
        max_length=254,
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": _("Enter your registered email"),
            "autocomplete": "email",
        }),
    )


class CustomSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        label=_("New Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            "class": "form-control", "placeholder": _("Enter new password"),
            "autocomplete": "new-password",
        }),
    )
    new_password2 = forms.CharField(
        label=_("Confirm New Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": _("Confirm new password"),
            "autocomplete": "new-password",
        }),
    )


class UserCreateForm(forms.ModelForm):
    ROLE_CHOICES = [
        ("", _("Select a role")),
        ("MANAGER", _("Manager")),
        ("TEAM_LEAD", _("Team Leader")),
        ("ARO", _("ARO (Agent)")),
        ("CALLER", _("Caller")),
        ("DATA_ENTRY", _("Data Entry Operator")),
    ]

    email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(attrs={
            "class": "form-control", "placeholder": _("Enter email address"),
        }),
    )
    username = forms.CharField(
        label=_("Username"),
        widget=forms.TextInput(attrs={
            "class": "form-control", "placeholder": _("Enter username"),
        }),
    )
    first_name = forms.CharField(
        label=_("First Name"),
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control", "placeholder": _("Enter first name"),
        }),
    )
    last_name = forms.CharField(
        label=_("Last Name"),
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control", "placeholder": _("Enter last name"),
        }),
    )
    password1 = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            "class": "form-control", "placeholder": _("Enter password"),
        }),
    )
    password2 = forms.CharField(
        label=_("Confirm Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            "class": "form-control", "placeholder": _("Confirm password"),
        }),
    )
    role = forms.ChoiceField(
        label=_("Role"),
        choices=ROLE_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    phone = forms.CharField(
        label=_("Phone"),
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control", "placeholder": _("Enter phone number"),
        }),
    )
    department = forms.ChoiceField(
        label=_("Department"),
        choices=[("", _("Select department"))] + UserProfile.DEPARTMENT_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    manager = forms.ModelChoiceField(
        label=_("Manager"),
        queryset=UserProfile.objects.filter(is_active=True).select_related("user"),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = User
        fields = [
            "username", "email", "first_name", "last_name",
            "password1", "password2",
        ]

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("A user with this email already exists."))
        return email

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(_("A user with this username already exists."))
        return username

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(_("Passwords do not match."))
        return password2

    def clean_role(self):
        role_code = self.cleaned_data.get("role")
        if not role_code:
            raise forms.ValidationError(_("Role is required."))
        return role_code

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            role = Role.objects.get(role_code=self.cleaned_data["role"])
            UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    "role": role,
                    "phone": self.cleaned_data.get("phone", ""),
                    "department": self.cleaned_data.get("department", ""),
                    "manager": self.cleaned_data.get("manager"),
                },
            )
        return user


class UserUpdateForm(forms.ModelForm):
    ROLE_CHOICES = [
        ("", _("Select a role")),
        ("SUPER_ADMIN", _("Super Admin")),
        ("MANAGER", _("Manager")),
        ("TEAM_LEAD", _("Team Leader")),
        ("ARO", _("ARO (Agent)")),
        ("CALLER", _("Caller")),
        ("DATA_ENTRY", _("Data Entry Operator")),
    ]

    email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(attrs={
            "class": "form-control", "placeholder": _("Enter email address"),
        }),
    )
    username = forms.CharField(
        label=_("Username"),
        widget=forms.TextInput(attrs={
            "class": "form-control", "placeholder": _("Enter username"),
        }),
    )
    first_name = forms.CharField(
        label=_("First Name"),
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control", "placeholder": _("Enter first name"),
        }),
    )
    last_name = forms.CharField(
        label=_("Last Name"),
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control", "placeholder": _("Enter last name"),
        }),
    )
    role = forms.ChoiceField(
        label=_("Role"),
        choices=ROLE_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    phone = forms.CharField(
        label=_("Phone"),
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control", "placeholder": _("Enter phone number"),
        }),
    )
    department = forms.ChoiceField(
        label=_("Department"),
        choices=[("", _("Select department"))] + UserProfile.DEPARTMENT_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    manager = forms.ModelChoiceField(
        label=_("Manager"),
        queryset=UserProfile.objects.filter(is_active=True).select_related("user"),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    is_active = forms.BooleanField(
        label=_("Active"),
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    class Meta:
        model = User
        fields = [
            "username", "email", "first_name", "last_name", "is_active",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            try:
                profile = self.instance.profile
                self.fields["role"].initial = profile.role.role_code
                self.fields["phone"].initial = profile.phone
                self.fields["department"].initial = profile.department
                self.fields["manager"].initial = profile.manager
            except UserProfile.DoesNotExist:
                pass

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    "role": Role.objects.get(
                        role_code=self.cleaned_data["role"]
                    ),
                    "phone": self.cleaned_data.get("phone", ""),
                    "department": self.cleaned_data.get("department", ""),
                    "manager": self.cleaned_data.get("manager"),
                },
            )
        return user


class UserActivationForm(forms.Form):
    user_id = forms.UUIDField(widget=forms.HiddenInput())
    action = forms.ChoiceField(
        choices=[("activate", _("Activate")), ("deactivate", _("Deactivate"))],
        widget=forms.HiddenInput(),
    )
    reason = forms.CharField(
        label=_("Reason"),
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-control", "rows": 2,
            "placeholder": _("Optional reason for this action"),
        }),
    )
