from django.db import models


class HtmlPage(models.Model):
    """الـ HTML بيتخزن في قاعدة البيانات نفسها (Render مبيحفظش ملفات على القرص)."""
    title = models.CharField(max_length=150)
    content = models.TextField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.title
