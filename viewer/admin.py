from django.contrib import admin

from .models import AccessCode, Grade, HtmlPage, SiteSettings, Stage, Subject

admin.site.register(Stage)
admin.site.register(Grade)
admin.site.register(Subject)
admin.site.register(SiteSettings)


@admin.register(HtmlPage)
class HtmlPageAdmin(admin.ModelAdmin):
    list_display = ("title", "subject", "is_free", "uploaded_at")
    list_filter = ("is_free", "subject__grade__stage")
    exclude = ("content",)


@admin.register(AccessCode)
class AccessCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "label", "is_active", "expires_at", "last_used_at")
