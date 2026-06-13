from django import forms
from django.utils.translation import gettext_lazy as _
from leads.models import Campaign


class PDFUploadForm(forms.Form):
    file = forms.FileField(
        label=_("PDF File"),
        widget=forms.FileInput(attrs={"accept": ".pdf"}),
    )
    campaign = forms.ModelChoiceField(
        queryset=Campaign.objects.filter(status="ACTIVE").select_related("bank_source"),
        label=_("Campaign"),
        empty_label=_("-- Select Campaign --"),
        required=True,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": _("Add any notes about this upload...")}),
        required=False,
        label=_("Notes (Optional)"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != "campaign":
                field.widget.attrs.setdefault("class", "form-control")
