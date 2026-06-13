import os

from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

from .models import WorkItem, WorkNote, WorkAssignment, WorkRevert
from .status import get_allowed_transition_choices

User = get_user_model()

ALLOWED_IMAGE_TYPES = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp")


class MultipleFileInput(forms.Widget):
    template_name = "documents/forms/multiple_file_input.html"
    needs_multipart_form = True

    def value_from_datadict(self, data, files, name):
        if files:
            return files.getlist(name)
        return []

    def format_value(self, value):
        return ""

    def get_context(self, name, value, attrs):
        ctx = super().get_context(name, value, attrs)
        if attrs:
            ctx["widget"]["attrs"].update(attrs)
        ctx["widget"]["attrs"]["type"] = "file"
        ctx["widget"]["attrs"]["multiple"] = "multiple"
        return ctx


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def to_python(self, data):
        if not data:
            return []
        if isinstance(data, list):
            return data
        return [data]

    def validate(self, value):
        if self.required and not value:
            raise forms.ValidationError(self.error_messages["required"])


class PDFUploadForm(forms.Form):
    file = forms.FileField(
        label=_("PDF File"),
        widget=forms.FileInput(attrs={"accept": ".pdf", "class": "form-control"}),
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2, "class": "form-control", "placeholder": _("Add any notes about this upload...")}),
        required=False,
        label=_("Notes (Optional)"),
    )

    def clean_file(self):
        f = self.cleaned_data["file"]
        if not f.name.lower().endswith(".pdf"):
            raise forms.ValidationError(_("Only PDF files are supported."))
        if f.size > 500 * 1024 * 1024:
            raise forms.ValidationError(_("File size must be under 500 MB."))
        return f


class WorkItemAssignForm(forms.Form):
    assigned_to = forms.ModelChoiceField(
        queryset=None,
        label=_("Assign To"),
        empty_label=_("-- Select User --"),
        required=True,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2, "class": "form-control", "placeholder": _("Reason for assignment...")}),
        required=False,
        label=_("Assignment Notes"),
    )

    def __init__(self, *args, **kwargs):
        user_queryset = kwargs.pop("user_queryset", None)
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].queryset = user_queryset or User.objects.none()


class WorkItemStatusForm(forms.Form):
    new_status = forms.ChoiceField(
        choices=[],
        label=_("New Status"),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2, "class": "form-control", "placeholder": _("Notes about this status change...")}),
        required=False,
        label=_("Notes"),
    )

    def __init__(self, *args, **kwargs):
        current_status = kwargs.pop("current_status", "NEW")
        super().__init__(*args, **kwargs)
        self.fields["new_status"].choices = get_allowed_transition_choices(current_status)


class WorkNoteForm(forms.ModelForm):
    class Meta:
        model = WorkNote
        fields = ["content", "is_feedback"]
        widgets = {
            "content": forms.Textarea(attrs={"rows": 3, "class": "form-control", "placeholder": _("Enter note...")}),
            "is_feedback": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "is_feedback": _("Mark as feedback (visible to Manager & Team Lead)"),
        }


class WorkRevertForm(forms.ModelForm):
    class Meta:
        model = WorkRevert
        fields = ["reason", "reason_details", "remarks", "attachment"]
        widgets = {
            "reason": forms.Select(attrs={"class": "form-select"}),
            "reason_details": forms.Textarea(attrs={"rows": 2, "class": "form-control", "placeholder": _("Describe why this item is being reverted...")}),
            "remarks": forms.Textarea(attrs={"rows": 2, "class": "form-control", "placeholder": _("Additional remarks...")}),
            "attachment": forms.FileInput(attrs={"class": "form-control"}),
        }


class ImageUploadForm(forms.Form):
    files = MultipleFileField(
        label=_("Image Files"),
        widget=MultipleFileInput(attrs={"accept": ",".join(ALLOWED_IMAGE_TYPES), "class": "form-control"}),
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2, "class": "form-control", "placeholder": _("Add any notes about this upload...")}),
        required=False,
        label=_("Notes (Optional)"),
    )

    def clean_files(self):
        files = self.cleaned_data.get("files", [])
        if not files:
            raise forms.ValidationError(_("Please select at least one image file."))
        allowed = ALLOWED_IMAGE_TYPES
        for f in files:
            ext = os.path.splitext(f.name.lower())[1]
            if ext not in allowed:
                raise forms.ValidationError(_("%(name)s: unsupported image type. Allowed: %(types)s") % {
                    "name": f.name, "types": ", ".join(allowed),
                })
            if f.size > 50 * 1024 * 1024:
                raise forms.ValidationError(_("%(name)s: file size must be under 50 MB.") % {"name": f.name})
        return files


class ExcelUploadForm(forms.Form):
    file = forms.FileField(
        label=_("Excel File"),
        widget=forms.FileInput(attrs={"accept": ".xlsx,.xls,.csv", "class": "form-control"}),
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2, "class": "form-control", "placeholder": _("Add any notes about this upload...")}),
        required=False,
        label=_("Notes (Optional)"),
    )

    def clean_file(self):
        f = self.cleaned_data["file"]
        ext = os.path.splitext(f.name.lower())[1]
        if ext not in (".xlsx", ".xls", ".csv"):
            raise forms.ValidationError(_("Only .xlsx, .xls, and .csv files are supported."))
        if f.size > 500 * 1024 * 1024:
            raise forms.ValidationError(_("File size must be under 500 MB."))
        return f
