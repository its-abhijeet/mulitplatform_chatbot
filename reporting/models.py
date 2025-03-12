# reporting/models.py
from django.db import models
from accounts.models import User
from communications.models import Channel


class Report(models.Model):
    REPORT_TYPES = (
        ("email", "Email Performance"),
        ("whatsapp", "WhatsApp Activity"),
        ("chatbot", "Chatbot Performance"),
        ("conversation", "Conversation Analysis"),
        ("custom", "Custom Report"),
    )

    FORMAT_CHOICES = (
        ("pdf", "PDF"),
        ("csv", "CSV"),
        ("json", "JSON"),
    )

    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=REPORT_TYPES)
    channels = models.ManyToManyField(Channel, related_name="reports")
    parameters = models.JSONField(default=dict)
    date_from = models.DateField()
    date_to = models.DateField()
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES, default="pdf")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to="reports/", null=True, blank=True)

    def __str__(self):
        return self.name
