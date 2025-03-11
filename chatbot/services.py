# chatbot/services.py
import re
import json
from django.conf import settings
from celery import shared_task
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from communications.models import Conversation, ConversationMessage
from chatbot.models import Intent, KnowledgeBase, ChatbotResponse, ChatbotInteraction, HandoffRule

class ChatbotService:
    """Service for handling chatbot interactions"""
    
    @staticmethod
    def load_nlp_model():
        """Load NLP model or create a new one if needed"""
        # For demonstration - in production would use a more sophisticated NLP system
        # like Rasa or a dedicated NLP service
        intents = Intent.objects.all()
        phrases = []
        intent_ids = []
        
        for intent in intents:
            for phrase in intent.training_phrases:
                phrases.append(phrase)
                intent_ids.append(intent.id)
        
        # Create a simple TF-IDF based classifier
        vectorizer = TfidfVectorizer(max_features=1000)
        if not phrases:
            return {"vectorizer": vectorizer, "phrases": [], "intent_ids": []}
            
        X = vectorizer.fit_transform(phrases)
        
        return {
            "vectorizer": vectorizer,
            "X": X,
            "phrases": phrases,
            "intent_ids": intent_ids
        }
    
    @staticmethod
    def detect_intent(text, nlp_model=None):
        """Detect user intent from input text"""
        if nlp_model is None:
            nlp_model = ChatbotService.load_nlp_model()
        
        # If no training data yet
        if not nlp_model["phrases"]:
            return None, 0.0
            
        # Vectorize input text
        text_vector = nlp_model["vectorizer"].transform([text])
        
        # Calculate similarity with all training phrases
        similarities = cosine_similarity(text_vector, nlp_model["X"]).flatten()
        
        # Get the highest similarity
        best_match_index = np.argmax(similarities)
        confidence = similarities[best_match_index]
        
        # Get corresponding intent
        if confidence > 0.3:  # Minimum threshold
            intent_id = nlp_model["intent_ids"][best_match_index]
            intent = Intent.objects.get(id=intent_id)
            return intent, float(confidence)
        
        return None, 0.0
    
    @staticmethod
    def get_response(intent, user_input):
        """Get appropriate response for detected intent"""
        if not intent:
            # Fallback response
            return "I'm not sure I understand. Could you rephrase that?", None
        
        # Get available responses for this intent
        responses = ChatbotResponse.objects.filter(intent=intent)
        
        if not responses:
            return "I understand you're asking about {}, but I don't have specific information on that yet.".format(intent.name), None
        
        # For now, just get a random response
        # In production, would implement more sophisticated selection
        import random
        response = random.choice(responses)
        
        # Check if response uses knowledge base
        if response.knowledge_base:
            # Extract entities and parameters from user input
            # This is simplified - would use NER in production
            kb_content = response.knowledge_base.content
            
            # Look for relevant info in knowledge base
            # This is a very basic implementation
            for key, value in kb_content.items():
                if key.lower() in user_input.lower():
                    return value, response
            
            # If no specific match found
            return response.text, response
        
        return response.text, response
    
    @staticmethod
    def process_user_message(conversation_id, user_input):
        """Process incoming user message and generate chatbot response"""
        conversation = Conversation.objects.get(id=conversation_id)
        
        # Create user message
        user_message = ConversationMessage.objects.create(
            conversation=conversation,
            is_from_user=True,
            content=user_input
        )
        
        # Detect intent
        nlp_model = ChatbotService.load_nlp_model()
        intent, confidence = ChatbotService.detect_intent(user_input, nlp_model)
        
        # Check for handoff rules
        needs_handoff = ChatbotService.check_handoff_rules(intent, confidence)
        
        if needs_handoff:
            response_text = "I'll connect you with a human agent who can better assist you."
            
            # Update conversation metadata to indicate handoff needed
            conversation.metadata['needs_handoff'] = True
            conversation.metadata['handoff_requested_at'] = str(datetime.now())
            conversation.save()
        else:
            # Get appropriate response
            response_text, response_obj = ChatbotService.get_response(intent, user_input)
        
        # Create bot response message
        bot_message = ConversationMessage.objects.create(
            conversation=conversation,
            is_from_user=False,
            content=response_text,
            metadata={
                'intent': intent.name if intent else None,
                'confidence': confidence,
                'needs_handoff': needs_handoff
            }
        )
        
        # Record interaction for analytics
        interaction = ChatbotInteraction.objects.create(
            conversation=conversation,
            user_input=user_input,
            detected_intent=intent,
            confidence_score=confidence,
            response=response_text
        )
        
        return {
            'response': response_text,
            'needs_handoff': needs_handoff,
            'intent': intent.name if intent else None,
            'confidence': confidence,
            'message_id': bot_message.id,
            'interaction_id': interaction.id
        }
    
    @staticmethod
    def check_handoff_rules(intent, confidence):
        """Check if conversation should be handed off to human agent"""
        # If no intent detected with reasonable confidence
        if not intent or confidence < 0.4:
            return True
            
        # Check specific handoff rules
        handoff_rules = HandoffRule.objects.filter(is_active=True)
        
        for rule in handoff_rules:
            # Intent-specific rules
            if rule.intent and rule.intent.id == intent.id:
                if confidence < rule.confidence_threshold:
                    return True
            
            # General threshold rule (applies to all intents)
            elif not rule.intent and confidence < rule.confidence_threshold:
                return True
        
        return False
    
    @staticmethod
    def record_feedback(interaction_id, rating):
        """Record user feedback for a chatbot interaction"""
        interaction = ChatbotInteraction.objects.get(id=interaction_id)
        interaction.feedback_rating = rating
        interaction.save()
        
        # In production, would add logic to improve responses based on feedback
        return True
    
    @staticmethod
    def update_knowledge_base(kb_id, content):
        """Update or add to knowledge base content"""
        kb = KnowledgeBase.objects.get(id=kb_id)
        
        # Merge new content with existing content
        updated_content = kb.content.copy()
        updated_content.update(content)
        
        kb.content = updated_content
        kb.save()
        
        return kb


@shared_task
def train_intent_model():
    """Periodically retrain the NLP model"""
    ChatbotService.load_nlp_model()
    return True