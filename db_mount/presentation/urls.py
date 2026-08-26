from django.urls import path

from . import views

app_name = "db_mount"


urlpatterns = [
    path("form/", views.orm_item_form, name="orm_item_form"),
    path("orm/", views.orm_items, name="orm_items"),
    path("raw/", views.raw_items, name="raw_items"),
]