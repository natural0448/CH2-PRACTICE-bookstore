
from django.contrib import admin
from django.urls import path
from django.http import HttpResponse
from django.urls import include, path


urlpatterns = [
    path('admin/', admin.site.urls),
    path("bookstore/", include("bookstore.urls")),
]

