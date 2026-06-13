from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Lead, LeadNote, FollowUp, Campaign, Batch, AssignmentRule, LeadCall


class LeadForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = [
            "batch", "lead_number", "lead_source_id",
            "customer_name", "phone", "email", "pan_number",
            "loan_amount", "loan_type", "property_value",
            "employment_type", "address", "city", "state", "pincode",
            "priority",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
            "loan_amount": forms.NumberInput(attrs={"step": "0.01"}),
            "property_value": forms.NumberInput(attrs={"step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["batch"].queryset = Batch.objects.select_related("campaign__bank_source")
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")
        if phone and not phone.isdigit() and not phone.startswith("+"):
            raise forms.ValidationError(_("Enter a valid phone number."))
        return phone


class LeadNoteForm(forms.ModelForm):
    class Meta:
        model = LeadNote
        fields = ["note_type", "content"]
        widgets = {
            "content": forms.Textarea(attrs={"rows": 4, "placeholder": _("Enter note details...")}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class FollowUpForm(forms.ModelForm):
    class Meta:
        model = FollowUp
        fields = ["followup_type", "scheduled_at", "assigned_to", "notes"]
        widgets = {
            "scheduled_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class BulkAssignForm(forms.Form):
    assign_to = forms.ModelChoiceField(
        queryset=None,
        label=_("Assign To"),
        empty_label=_("-- Select User --"),
        required=True,
    )

    def __init__(self, *args, **kwargs):
        from accounts.models import User
        super().__init__(*args, **kwargs)
        self.fields["assign_to"].queryset = User.objects.filter(is_active=True).order_by("username")
        self.fields["assign_to"].widget.attrs.setdefault("class", "form-control")


class RoundRobinAssignForm(forms.Form):
    rule = forms.ModelChoiceField(
        queryset=None,
        label=_("Assignment Rule"),
        empty_label=_("-- Select Rule --"),
        required=True,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["rule"].queryset = AssignmentRule.objects.filter(
            team_lead=user, is_active=True
        ).order_by("name")


class ReassignForm(forms.Form):
    assign_to = forms.ModelChoiceField(
        queryset=None,
        label=_("Reassign To"),
        empty_label=_("-- Select User --"),
        required=True,
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2, "class": "form-control", "placeholder": "Reason for reassignment..."}),
        required=False,
        label=_("Reason"),
    )

    def __init__(self, *args, **kwargs):
        from accounts.models import User
        super().__init__(*args, **kwargs)
        self.fields["assign_to"].queryset = User.objects.filter(is_active=True).order_by("username")
        self.fields["assign_to"].widget.attrs.setdefault("class", "form-control")


class AssignmentRuleForm(forms.ModelForm):
    callers = forms.MultipleChoiceField(
        label=_("Callers"),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": 10}),
    )

    class Meta:
        model = AssignmentRule
        fields = ["name", "campaign", "max_active_leads", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "campaign": forms.Select(attrs={"class": "form-select"}),
            "max_active_leads": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["campaign"].queryset = Campaign.objects.filter(status="ACTIVE")
        caller_choices = self._get_caller_choices()
        self.fields["callers"].choices = caller_choices

        if self.instance.pk:
            existing = self.instance.round_robin_counters.values_list("caller_id", flat=True)
            self.fields["callers"].initial = [str(uid) for uid in existing]

    def _get_caller_choices(self):
        from accounts.models import User
        return [
            (str(u.id), f"{u.get_full_name() or u.username} ({u.profile.role.role_code})")
            for u in User.objects.filter(
                is_active=True, profile__is_active=True, profile__role__role_code="CALLER"
            ).select_related("profile__role").order_by("username")
        ]

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.pk:
            instance.team_lead = self.user
        if commit:
            instance.save()
            self._sync_callers(instance)
        return instance

    def _sync_callers(self, instance):
        from .services import setup_round_robin_rule
        selected = self.cleaned_data.get("callers", [])
        setup_round_robin_rule(instance, selected)


class QuickStatusForm(forms.Form):
    status = forms.ChoiceField(
        choices=Lead.LEAD_STATUS_CHOICES,
        label=_("Status"),
        required=True,
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
        required=False,
        label=_("Notes (optional)"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].widget.attrs.setdefault("class", "form-control")


class CallForm(forms.ModelForm):
    class Meta:
        model = LeadCall
        fields = ["call_type", "call_status", "duration_seconds", "notes", "recording_url", "call_time"]
        widgets = {
            "call_time": forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"}),
            "notes": forms.Textarea(attrs={"rows": 3, "class": "form-control", "placeholder": "Call notes..."}),
            "duration_seconds": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "recording_url": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["call_type"].widget.attrs.setdefault("class", "form-select")
        self.fields["call_status"].widget.attrs.setdefault("class", "form-select")
