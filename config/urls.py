from django.contrib import admin
from django.urls import include, path
from communications import urls

urlpatterns = [
    path("admin/", admin.site.urls),
    path("communications/", include(urls)),  # Correct this line
]
