from pathlib import Path

from django import forms
from django.conf import settings


class UploadForm(forms.Form):
    file = forms.FileField()

    def clean_file(self):
        f = self.cleaned_data["file"]
        if Path(f.name).suffix.lower() not in (".html", ".htm"):
            raise forms.ValidationError("لازم الملف يكون بصيغة .html أو .htm")
        if f.size > settings.MAX_HTML_FILE_SIZE:
            mb = settings.MAX_HTML_FILE_SIZE // (1024 * 1024)
            raise forms.ValidationError(f"حجم الملف أكبر من {mb} ميجا")
        return f
