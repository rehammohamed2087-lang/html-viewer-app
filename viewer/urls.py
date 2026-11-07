from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("stage/<int:pk>/", views.stage_view, name="stage"),
    path("grade/<int:pk>/", views.grade_view, name="grade"),
    path("subject/<int:pk>/", views.subject_view, name="subject"),
    path("view/<int:pk>/", views.page_view, name="page"),
    path("raw/<int:pk>/", views.raw, name="raw"),
    path("unlock/", views.unlock, name="unlock"),
    path("lock/", views.lock, name="lock"),
    # لوحة الأدمن
    path("panel/", views.panel, name="panel"),
    path("panel/upload/", views.panel_upload, name="panel_upload"),
    path("panel/file/<int:pk>/edit/", views.file_edit, name="file_edit"),
    path("panel/file/<int:pk>/free/", views.file_toggle_free, name="file_toggle_free"),
    path("panel/file/<int:pk>/delete/", views.file_delete, name="file_delete"),
    path("panel/structure/", views.panel_structure, name="panel_structure"),
    path("panel/codes/", views.panel_codes, name="panel_codes"),
    path("panel/settings/", views.panel_settings, name="panel_settings"),
]
