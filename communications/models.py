# communications/models.py
from django.db import models
from accounts.models import User


class Channel(models.Model):
    CHANNEL_TYPES = (
        ("email", "Email"),
        ("whatsapp", "WhatsApp"),
        ("webchat", "Web Chat"),
    )

    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=CHANNEL_TYPES)
    configuration = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"


class Template(models.Model):
    name = models.CharField(max_length=200)
    channel = models.ForeignKey(
        Channel, on_delete=models.CASCADE, related_name="templates"
    )
    subject = models.CharField(max_length=255, blank=True)
    content = models.TextField()
    variables = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Message(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("sent", "Sent"),
        ("delivered", "Delivered"),
        ("read", "Read"),
        ("failed", "Failed"),
    )

    channel = models.ForeignKey(
        Channel, on_delete=models.CASCADE, related_name="messages"
    )
    template = models.ForeignKey(
        Template, on_delete=models.SET_NULL, null=True, blank=True
    )
    sender = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="sent_messages"
    )
    recipient = models.CharField(max_length=255)  # Email or phone number
    subject = models.CharField(max_length=255, blank=True)
    content = models.TextField()
    metadata = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.channel.name} - {self.recipient} - {self.status}"


class Conversation(models.Model):
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE)
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="conversations"
    )
    external_id = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict)
    tags = models.JSONField(default=list)
    started_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.channel.name} - {self.user or self.external_id}"


class ConversationMessage(models.Model):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    is_from_user = models.BooleanField(default=True)
    content = models.TextField()
    attachments = models.JSONField(default=list)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.conversation.id} - {'User' if self.is_from_user else 'System'}"
