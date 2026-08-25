from django.urls import path
from django.urls import include, path

from . import views


urlpatterns += [
    path("orm/", views.orm_items, name="orm_items"),
    path("raw/", views.raw_items, name="raw_items"),
    path("db-mount/", include("db_mount.presentation.urls")),

    
]