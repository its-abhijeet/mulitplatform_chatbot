# whatsapp_service/models.py
from django.db import models
from communications.models import Message, Conversation

class WhatsAppAccount(models.Model):
    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    twilio_account_sid = models.CharField(max_length=255)
    twilio_auth_token = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class WhatsAppMessage(models.Model):
    message = models.OneToOneField(Message, on_delete=models.CASCADE, related_name='whatsapp_details')
    account = models.ForeignKey(WhatsAppAccount, on_delete=models.CASCADE, related_name='messages')
    media_url = models.URLField(blank=True)
    media_type = models.CharField(max_length=50, blank=True)
    twilio_message_id = models.CharField(max_length=255, blank=True)
    
    def __str__(self):
        return f"WhatsApp: {self.message.recipient}"

class AutoReply(models.Model):
    account = models.ForeignKey(WhatsAppAccount, on_delete=models.CASCADE, related_name='auto_replies')
    name = models.CharField(max_length=255)
    trigger_pattern = models.CharField(max_length=255)
    response_text = models.TextField()
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name