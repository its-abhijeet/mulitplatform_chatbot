# chatbot/models.py
from django.db import models
from communications.models import Conversation


class Intent(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    training_phrases = models.JSONField(default=list)

    def __str__(self):
        return self.name


class KnowledgeBase(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    content = models.JSONField(default=dict)

    def __str__(self):
        return self.name


class ChatbotResponse(models.Model):
    intent = models.ForeignKey(
        Intent, on_delete=models.CASCADE, related_name="responses"
    )
    text = models.TextField()
    parameters = models.JSONField(default=list)
    knowledge_base = models.ForeignKey(
        KnowledgeBase, on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        return f"{self.intent.name} Response"


class ChatbotInteraction(models.Model):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="chatbot_interactions"
    )
    user_input = models.TextField()
    detected_intent = models.ForeignKey(Intent, on_delete=models.SET_NULL, null=True)
    confidence_score = models.FloatField(default=0.0)
    response = models.TextField()
    feedback_rating = models.IntegerField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Interaction: {self.conversation.id} - {self.detected_intent}"


class HandoffRule(models.Model):
    intent = models.ForeignKey(Intent, on_delete=models.SET_NULL, null=True, blank=True)
    confidence_threshold = models.FloatField(default=0.7)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Handoff: {self.intent.name if self.intent else 'General'}"
