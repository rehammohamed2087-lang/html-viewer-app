import re
import secrets
from urllib.parse import quote

from django.db import models, transaction
from django.utils import timezone


class Stage(models.Model):
    """المرحلة الدراسية (ابتدائي / إعدادي / ثانوي ...)."""
    name = models.CharField(max_length=100, unique=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.name


class Grade(models.Model):
    """الصف داخل مرحلة (الصف الأول، الثاني ...)."""
    stage = models.ForeignKey(Stage, on_delete=models.CASCADE, related_name="grades")
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["stage", "name"], name="uniq_grade_per_stage"),
        ]

    def __str__(self):
        return f"{self.stage.name} › {self.name}"


class Subject(models.Model):
    """المادة داخل صف."""
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name="subjects")
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["grade", "name"], name="uniq_subject_per_grade"),
        ]

    def __str__(self):
        return f"{self.grade.stage.name} › {self.grade.name} › {self.name}"


class HtmlPage(models.Model):
    """الـ HTML بيتخزن في قاعدة البيانات نفسها (Render مبيحفظش ملفات على القرص)."""
    title = models.CharField(max_length=150)
    content = models.TextField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
    # PROTECT: مينفعش نحذف مادة وفيها ملفات بالغلط
    subject = models.ForeignKey(
        Subject, null=True, blank=True, on_delete=models.PROTECT, related_name="pages"
    )
    # ملف واحد فقط يكون مجاني في أي وقت
    is_free = models.BooleanField(default=False)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.is_free:
                HtmlPage.objects.filter(is_free=True).exclude(pk=self.pk).update(is_free=False)
            super().save(*args, **kwargs)


_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"   # من غير حروف/أرقام متشابهة


class AccessCode(models.Model):
    """كود دخول بيديه الأدمن للطالب لفتح كل الملفات."""
    code = models.CharField(max_length=40, unique=True)
    label = models.CharField(max_length=100, blank=True)   # اسم الطالب / ملاحظة
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.code

    @classmethod
    def generate(cls):
        while True:
            code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(8))
            if not cls.objects.filter(code=code).exists():
                return code

    def is_valid(self):
        if not self.is_active:
            return False
        return self.expires_at is None or self.expires_at > timezone.now()

    @property
    def status(self):
        if not self.is_active:
            return "موقوف"
        if self.expires_at and self.expires_at <= timezone.now():
            return "منتهي"
        return "فعّال"

    @property
    def share_text(self):
        return f"كود الدخول الخاص بك: {self.code}"


class SiteSettings(models.Model):
    """إعدادات الموقع (صف واحد فقط)."""
    site_name = models.CharField(max_length=80, default="مكتبة الدروس")
    whatsapp_number = models.CharField(max_length=30, blank=True)
    whatsapp_message = models.CharField(
        max_length=200, default="السلام عليكم، أريد كود الدخول لمشاهدة الملفات."
    )

    def __str__(self):
        return self.site_name

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def wa_digits(self):
        digits = re.sub(r"\D", "", self.whatsapp_number or "")
        if digits.startswith("00"):
            digits = digits[2:]
        elif digits.startswith("0"):          # رقم مصري محلي مثل 01012345678
            digits = "20" + digits[1:]
        return digits

    @property
    def wa_url(self):
        if not self.wa_digits:
            return ""
        return f"https://wa.me/{self.wa_digits}?text={quote(self.whatsapp_message)}"
