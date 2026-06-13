from django import forms
from django.utils.translation import gettext_lazy as _
from .models import User, UserProfile, Role


def _make_user_fields(include_password=True):
    fields = {
        "email": forms.EmailField(
            label=_("Email"),
            widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": _("Enter email address")}),
        ),
        "username": forms.CharField(
            label=_("Username"),
            widget=forms.TextInput(attrs={"class": "form-control", "placeholder": _("Enter username")}),
        ),
        "first_name": forms.CharField(
            label=_("First Name"), required=False,
            widget=forms.TextInput(attrs={"class": "form-control", "placeholder": _("Enter first name")}),
        ),
        "last_name": forms.CharField(
            label=_("Last Name"), required=False,
            widget=forms.TextInput(attrs={"class": "form-control", "placeholder": _("Enter last name")}),
        ),
        "phone": forms.CharField(
            label=_("Phone"), required=False,
            widget=forms.TextInput(attrs={"class": "form-control", "placeholder": _("Enter phone number")}),
        ),
        "department": forms.ChoiceField(
            label=_("Department"), required=False,
            choices=[("", _("Select department"))] + UserProfile.DEPARTMENT_CHOICES,
            widget=forms.Select(attrs={"class": "form-select"}),
        ),
    }
    if include_password:
        fields["password1"] = forms.CharField(
            label=_("Password"), strip=False,
            widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": _("Enter password")}),
        )
        fields["password2"] = forms.CharField(
            label=_("Confirm Password"), strip=False,
            widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": _("Confirm password")}),
        )
    return fields


class BaseOrgUserCreateForm(forms.ModelForm):
    role_code = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in _make_user_fields().items():
            self.fields[name] = field

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name"]

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("A user with this email already exists."))
        return email

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if username and User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(_("A user with this username already exists."))
        return username

    def clean_password2(self):
        p1 = self.cleaned_data.get("password1")
        p2 = self.cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError(_("Passwords do not match."))
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    "role": Role.objects.get(role_code=self.role_code),
                    "phone": self.cleaned_data.get("phone", ""),
                    "department": self.cleaned_data.get("department", ""),
                    "manager": self.cleaned_data.get("manager"),
                },
            )
        return user


class ManagerCreateForm(BaseOrgUserCreateForm):
    role_code = "MANAGER"


class TeamLeadCreateForm(BaseOrgUserCreateForm):
    role_code = "TEAM_LEAD"

    manager = forms.ModelChoiceField(
        label=_("Assign to Manager"),
        queryset=UserProfile.objects.filter(is_active=True, role__role_code="MANAGER").select_related("user"),
        required=True,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            manager = self.cleaned_data.get("manager")
            UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    "role": Role.objects.get(role_code="TEAM_LEAD"),
                    "phone": self.cleaned_data.get("phone", ""),
                    "department": self.cleaned_data.get("department", ""),
                    "manager": manager,
                },
            )
        return user


class AROCreateForm(BaseOrgUserCreateForm):
    role_code = "ARO"

    team_lead = forms.ModelChoiceField(
        label=_("Assign to Team Lead"),
        queryset=UserProfile.objects.filter(is_active=True, role__role_code="TEAM_LEAD").select_related("user"),
        required=True,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            tl = self.cleaned_data.get("team_lead")
            UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    "role": Role.objects.get(role_code="ARO"),
                    "phone": self.cleaned_data.get("phone", ""),
                    "department": self.cleaned_data.get("department", ""),
                    "manager": tl,
                },
            )
        return user


# ------------------------------------------------------------------ #
#  UPDATE FORMS
# ------------------------------------------------------------------ #
class BaseOrgUserUpdateForm(forms.ModelForm):
    first_name = forms.CharField(
        label=_("First Name"), required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": _("Enter first name")}),
    )
    last_name = forms.CharField(
        label=_("Last Name"), required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": _("Enter last name")}),
    )
    email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": _("Enter email address")}),
    )
    phone = forms.CharField(
        label=_("Phone"), required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": _("Enter phone number")}),
    )
    department = forms.ChoiceField(
        label=_("Department"), required=False,
        choices=[("", _("Select department"))] + UserProfile.DEPARTMENT_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    is_active = forms.BooleanField(
        label=_("Active"), required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            try:
                profile = self.instance.profile
                self.fields["phone"].initial = profile.phone
                self.fields["department"].initial = profile.department
            except UserProfile.DoesNotExist:
                pass

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            try:
                profile = user.profile
                profile.phone = self.cleaned_data.get("phone", "")
                profile.department = self.cleaned_data.get("department", "")
                profile.save()
            except UserProfile.DoesNotExist:
                pass
        return user


class ManagerUpdateForm(BaseOrgUserUpdateForm):
    pass


class TeamLeadUpdateForm(BaseOrgUserUpdateForm):
    manager = forms.ModelChoiceField(
        label=_("Assign to Manager"),
        queryset=UserProfile.objects.filter(is_active=True, role__role_code="MANAGER").select_related("user"),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            try:
                self.fields["manager"].initial = self.instance.profile.manager
            except UserProfile.DoesNotExist:
                pass

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            try:
                profile = user.profile
                profile.manager = self.cleaned_data.get("manager")
                profile.save()
            except UserProfile.DoesNotExist:
                pass
        return user


class AROUpdateForm(BaseOrgUserUpdateForm):
    team_lead = forms.ModelChoiceField(
        label=_("Assign to Team Lead"),
        queryset=UserProfile.objects.filter(is_active=True, role__role_code="TEAM_LEAD").select_related("user"),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            try:
                self.fields["team_lead"].initial = self.instance.profile.manager
            except UserProfile.DoesNotExist:
                pass

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            try:
                profile = user.profile
                profile.manager = self.cleaned_data.get("team_lead")
                profile.save()
            except UserProfile.DoesNotExist:
                pass
        return user
