# analytics/models.py
from django.db import models
from communications.models import Channel, Message, Conversation
from chatbot.models import ChatbotInteraction

class ChannelMetrics(models.Model):
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE)
    date = models.DateField()
    messages_sent = models.IntegerField(default=0)
    messages_delivered = models.IntegerField(default=0)
    messages_read = models.IntegerField(default=0)
    conversations_started = models.IntegerField(default=0)
    conversations_completed = models.IntegerField(default=0)
    average_response_time = models.FloatField(default=0)
    
    class Meta:
        unique_together = ('channel', 'date')
    
    def __str__(self):
        return f"{self.channel.name} - {self.date}"

class ChatbotMetrics(models.Model):
    date = models.DateField()
    interactions_count = models.IntegerField(default=0)
    successful_interactions = models.IntegerField(default=0)
    handoffs_count = models.IntegerField(default=0)
    average_confidence = models.FloatField(default=0)
    average_feedback = models.FloatField(default=0)
    
    class Meta:
        ordering = ['-date']
    
    def __str__(self):
        return f"Chatbot Metrics - {self.date}"