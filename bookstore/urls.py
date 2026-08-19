from django.urls import path

from . import views


urlpatterns = [
    path("", views.day2_dashboard, name="day2_dashboard"),
]

