import re
from pathlib import Path

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError

from .models import AccessCode, HtmlPage, SiteSettings, Stage, Subject


def read_html_file(f):
    """بيتحقق من الملف المرفوع ويرجّع نص الـ HTML."""
    if Path(f.name).suffix.lower() not in (".html", ".htm"):
        raise ValidationError(f"«{f.name}»: لازم الملف يكون بصيغة .html أو .htm")
    if f.size > settings.MAX_HTML_FILE_SIZE:
        mb = settings.MAX_HTML_FILE_SIZE // (1024 * 1024)
        raise ValidationError(f"«{f.name}»: حجم الملف أكبر من {mb} ميجا")
    try:
        html = f.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValidationError(f"«{f.name}»: الملف لازم يكون بترميز UTF-8.")
    if "\x00" in html:
        raise ValidationError(f"«{f.name}»: الملف يحتوي على بيانات غير صالحة.")
    return html


class UploadForm(forms.Form):
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.select_related("stage"),
        error_messages={"required": "اختر المرحلة والمادة قبل رفع الملف."},
    )
    is_free = forms.BooleanField(required=False)


class StageForm(forms.ModelForm):
    class Meta:
        model = Stage
        fields = ["name"]


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ["stage", "name"]


class FileEditForm(forms.ModelForm):
    class Meta:
        model = HtmlPage
        fields = ["title", "subject", "is_free"]
        labels = {"title": "اسم الملف", "subject": "المرحلة › المادة", "is_free": "ملف مجاني"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field = self.fields["subject"]
        field.queryset = Subject.objects.select_related("stage")
        field.label_from_instance = lambda o: f"{o.stage.name} › {o.name}"
        field.empty_label = "— اختر —"
        field.required = True


class CodeCreateForm(forms.Form):
    label = forms.CharField(max_length=100, required=False)
    code = forms.CharField(max_length=40, required=False)
    days = forms.IntegerField(min_value=1, max_value=3650, required=False)

    def clean_code(self):
        code = re.sub(r"\s+", "", self.cleaned_data.get("code") or "").upper()
        if code and AccessCode.objects.filter(code__iexact=code).exists():
            raise ValidationError("هذا الكود مستخدم بالفعل.")
        return code


class SettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = ["site_name", "whatsapp_number", "whatsapp_message"]

    def clean_whatsapp_number(self):
        value = (self.cleaned_data.get("whatsapp_number") or "").strip()
        if value:
            digits = re.sub(r"\D", "", value)
            if not 8 <= len(digits) <= 15:
                raise ValidationError("رقم الواتساب غير صحيح. اكتبه بالصيغة الدولية مثل 201012345678")
        return value
