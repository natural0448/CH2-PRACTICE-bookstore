from django.urls import path

from . import views


urlpatterns = [
    path("day2/", views.day2_dashboard, name="day2_dashboard"),
    path("day3/", views.day3_dashboard, name="day3_dashboard"),
]

