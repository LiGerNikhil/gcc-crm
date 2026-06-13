from django import forms
from django.utils.translation import gettext_lazy as _
from leads.models import Campaign


class ExcelUploadForm(forms.Form):
    file = forms.FileField(
        label=_("File"),
        help_text=_("Select .xlsx, .xls, or .csv file"),
        widget=forms.FileInput(attrs={"accept": ".xlsx,.xls,.csv"}),
    )
    campaign = forms.ModelChoiceField(
        queryset=Campaign.objects.filter(status="ACTIVE").select_related("bank_source"),
        label=_("Campaign"),
        empty_label=_("-- Select Campaign --"),
        required=True,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    batch_name = forms.CharField(
        max_length=200,
        required=False,
        label=_("Batch Name (optional)"),
        help_text=_("Leave blank for auto-generated name"),
        widget=forms.TextInput(attrs={"placeholder": "e.g., HDFC June Week 2"}),
    )
    sheet_name = forms.CharField(
        max_length=100,
        required=False,
        initial="Sheet1",
        label=_("Sheet Name"),
        widget=forms.TextInput(attrs={"placeholder": "Sheet1"}),
    )
    header_row = forms.IntegerField(
        initial=1,
        min_value=1,
        required=False,
        label=_("Header Row"),
    )
    skip_duplicates = forms.BooleanField(
        initial=True,
        required=False,
        label=_("Skip duplicates (match by phone/email/PAN)"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == "skip_duplicates":
                field.widget.attrs.setdefault("class", "form-check-input")
            elif name not in ("campaign",):
                field.widget.attrs.setdefault("class", "form-control")
