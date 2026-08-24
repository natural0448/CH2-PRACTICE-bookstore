from django.urls import path

from . import views


urlpatterns = [
    path("day2/", views.day2_dashboard, name="day2_dashboard"),
    path("day3/", views.day3_dashboard, name="day3_dashboard"),
    path("day4/", views.day4_dashboard, name="day4_dashboard"),
    path("day5/", views.day5_orm_dashboard, name="day5_dashboard"),
    path("day5/raw/", views.day5_raw_dashboard, name="day5_raw_dashboard"),

]

