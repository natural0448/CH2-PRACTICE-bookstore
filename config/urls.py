
from django.contrib import admin
from django.urls import path
from django.http import HttpResponse
from django.urls import include, path
from bookstore.presentation.views import day2_dashboard


urlpatterns = [
    path('admin/', admin.site.urls),
    path("bookstore/", include("bookstore.presentation.urls")),
    path("db_mount/", include("db_mount.presentation.urls")),
]

