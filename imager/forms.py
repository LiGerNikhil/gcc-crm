from django import forms
from django.utils.translation import gettext_lazy as _
from leads.models import Campaign
from .models import ImageBatch


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={"accept": ".jpg,.jpeg,.png,.webp,.gif,.bmp"}))
        super().__init__(*args, **kwargs)

    def to_python(self, data):
        if not data:
            return []
        if isinstance(data, list):
            return data
        return [data]

    def validate(self, data):
        if not data and self.required:
            raise forms.ValidationError(self.error_messages["required"])
        if data:
            for f in data:
                super().validate(f)
                super().run_validators(f)


class ImageUploadForm(forms.Form):
    files = MultipleFileField(
        label=_("Images"),
        help_text=_("Select .jpg, .png, .webp images (up to 20MB each)"),
    )
    campaign = forms.ModelChoiceField(
        queryset=Campaign.objects.filter(status="ACTIVE").select_related("bank_source"),
        label=_("Campaign"),
        empty_label=_("-- Select Campaign (optional) --"),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    batch_name = forms.CharField(
        max_length=255,
        required=False,
        label=_("Batch Name (optional)"),
        help_text=_("Group images into a batch for easier management"),
        widget=forms.TextInput(attrs={"placeholder": "e.g., KYC Documents June 2026"}),
    )
    description = forms.CharField(
        max_length=500,
        required=False,
        label=_("Description (optional)"),
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Brief description..."}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == "description":
                field.widget.attrs.setdefault("class", "form-control")
            elif name != "campaign":
                field.widget.attrs.setdefault("class", "form-control")


class ImageBatchAssignForm(forms.Form):
    lead_id = forms.UUIDField(
        label=_("Lead"),
        required=True,
        widget=forms.HiddenInput(),
    )
    lead_display = forms.CharField(
        label=_("Lead"),
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "readonly": "readonly"}),
    )


class ImageBatchForm(forms.ModelForm):
    class Meta:
        model = ImageBatch
        fields = ["name", "description", "campaign"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "campaign": forms.Select(attrs={"class": "form-select"}),
        }
