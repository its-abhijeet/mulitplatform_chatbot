from django.urls import path
from . import views
from email_service.services import send_email

urlpatterns = [
    path("", views.index, name="index"),
    path("send", send_email, name="send_email"),
]
