# email_service/models.py
from django.db import models
from communications.models import Message


class EmailBatch(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    recipients_file = models.FileField(upload_to="email_batches/")
    created_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class EmailMessage(models.Model):
    message = models.OneToOneField(
        Message, on_delete=models.CASCADE, related_name="email_details"
    )
    batch = models.ForeignKey(
        EmailBatch, on_delete=models.SET_NULL, null=True, related_name="emails"
    )
    opens = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    spam_score = models.FloatField(default=0.0)

    def __str__(self):
        return f"Email: {self.message.recipient}"


class EmailClick(models.Model):
    email = models.ForeignKey(
        EmailMessage, on_delete=models.CASCADE, related_name="click_events"
    )
    url = models.URLField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Click: {self.email.message.recipient} - {self.url}"
