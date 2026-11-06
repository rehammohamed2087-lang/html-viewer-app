from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("upload/", views.upload, name="upload"),
    path("delete/<int:pk>/", views.delete, name="delete"),
    path("raw/<int:pk>/", views.raw, name="raw"),
]
