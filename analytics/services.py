from datetime import datetime, timedelta
from django.db.models import Avg, Count, Sum, F, ExpressionWrapper, fields
from django.db.models.functions import TruncDate
from celery import shared_task
from communications.models import Channel, Message, Conversation, ConversationMessage
from chatbot.models import ChatbotInteraction
from analytics.models import ChannelMetrics, ChatbotMetrics

class AnalyticsService:
    """Services for analytics data processing and retrieval"""
    
    @staticmethod
    def get_channel_metrics(channel_id, start_date, end_date):
        """Get metrics for a specific channel in date range"""
        metrics = ChannelMetrics.objects.filter(
            channel_id=channel_id,
            date__gte=start_date,
            date__lte=end_date
        ).order_by('date')
        
        # Format for charts and tables
        result = {
            'dates': [],
            'messages_sent': [],
            'messages_delivered': [],
            'messages_read': [],
            'conversations_started': [],
            'conversations_completed': [],
            'average_response_time': []
        }
        
        for metric in metrics:
            result['dates'].append(metric.date.strftime('%Y-%m-%d'))
            result['messages_sent'].append(metric.messages_sent)
            result['messages_delivered'].append(metric.messages_delivered)
            result['messages_read'].append(metric.messages_read)
            result['conversations_started'].append(metric.conversations_started)
            result['conversations_completed'].append(metric.conversations_completed)
            result['average_response_time'].append(metric.average_response_time)
        
        # Calculate totals and averages
        result['totals'] = {
            'messages_sent': sum(result['messages_sent']),
            'messages_delivered': sum(result['messages_delivered']),
            'messages_read': sum(result['messages_read']),
            'conversations_started': sum(result['conversations_started']),
            'conversations_completed': sum(result['conversations_completed']),
            'average_response_time': sum(result['average_response_time']) / len(result['average_response_time']) if result['average_response_time'] else 0,
            'delivery_rate': sum(result['messages_delivered']) / sum(result['messages_sent']) * 100 if sum(result['messages_sent']) > 0 else 0,
            'read_rate': sum(result['messages_read']) / sum(result['messages_delivered']) * 100 if sum(result['messages_delivered']) > 0 else 0
        }
        
        return result
    
    @staticmethod
    def get_email_performance(start_date, end_date):
        """Get email specific performance metrics"""
        from email_service.models import EmailMessage, EmailClick
        
        # Get basic delivery metrics
        emails = EmailMessage.objects.filter(
            message__sent_at__gte=start_date,
            message__sent_at__lte=end_date
        ).select_related('message')
        
        total_sent = emails.count()
        total_opened = emails.filter(opens__gt=0).count()
        total_clicked = emails.filter(clicks__gt=0).count()
        
        # Calculate rates
        open_rate = (total_opened / total_sent * 100) if total_sent > 0 else 0
        click_rate = (total_clicked / total_opened * 100) if total_opened > 0 else 0
        click_to_sent = (total_clicked / total_sent * 100) if total_sent > 0 else 0
        
        # Get daily stats
        daily_stats = emails.annotate(
            date=TruncDate('message__sent_at')
        ).values('date').annotate(
            sent=Count('id'),
            opened=Count('id', filter=F('opens') > 0),
            clicked=Count('id', filter=F('clicks') > 0)
        ).order_by('date')
        
        # Format for response
        result = {
            'summary': {
                'total_sent': total_sent,
                'total_opened': total_opened,
                'total_clicked': total_clicked,
                'open_rate': open_rate,
                'click_rate': click_rate,
                'click_to_sent_rate': click_to_sent
            },
            'daily': [{
                'date': stat['date'].strftime('%Y-%m-%d'),
                'sent': stat['sent'],
                'opened': stat['opened'],
                'clicked': stat['clicked'],
                'open_rate': (stat['opened'] / stat['sent'] * 100) if stat['sent'] > 0 else 0,
                'click_rate': (stat['clicked'] / stat['opened'] * 100) if stat['opened'] > 0 else 0
            } for stat in daily_stats]
        }
        
        return result
    
    @staticmethod
    def get_whatsapp_performance(start_date, end_date):
        """Get WhatsApp specific performance metrics"""
        from whatsapp_service.models import WhatsAppMessage
        
        # Get basic delivery metrics
        whatsapp_messages = WhatsAppMessage.objects.filter(
            message__sent_at__gte=start_date,
            message__sent_at__lte=end_date
        ).select_related('message', 'account')
        
        total_sent = whatsapp_messages.count()
        total_delivered = whatsapp_messages.filter(message__status='delivered').count()
        total_read = whatsapp_messages.filter(message__status='read').count()
        
        # Calculate delivery and read rates
        delivery_rate = (total_delivered / total_sent * 100) if total_sent > 0 else 0
        read_rate = (total_read / total_delivered * 100) if total_delivered > 0 else 0
        
        # Get stats by account
        account_stats = whatsapp_messages.values(
            'account__name'
        ).annotate(
            sent=Count('id'),
            delivered=Count('id', filter=F('message__status') == 'delivered'),
            read=Count('id', filter=F('message__status') == 'read'),
            failed=Count('id', filter=F('message__status') == 'failed')
        )
        
        # Get daily stats
        daily_stats = whatsapp_messages.annotate(
            date=TruncDate('message__sent_at')
        ).values('date').annotate(
            sent=Count('id'),
            delivered=Count('id', filter=F('message__status') == 'delivered'),
            read=Count('id', filter=F('message__status') == 'read')
        ).order_by('date')
        
        # Format for response
        result = {
            'summary': {
                'total_sent': total_sent,
                'total_delivered': total_delivered,
                'total_read': total_read,
                'delivery_rate': delivery_rate,
                'read_rate': read_rate
            },
            'by_account': [{
                'account': stat['account__name'],
                'sent': stat['sent'],
                'delivered': stat['delivered'],
                'read': stat['read'],
                'failed': stat['failed'],
                'delivery_rate': (stat['delivered'] / stat['sent'] * 100) if stat['sent'] > 0 else 0,
                'read_rate': (stat['read'] / stat['delivered'] * 100) if stat['delivered'] > 0 else 0
            } for stat in account_stats],
            'daily': [{
                'date': stat['date'].strftime('%Y-%m-%d'),
                'sent': stat['sent'],
                'delivered': stat['delivered'],
                'read': stat['read'],
                'delivery_rate': (stat['delivered'] / stat['sent'] * 100) if stat['sent'] > 0 else 0,
                'read_rate': (stat['read'] / stat['delivered'] * 100) if stat['delivered'] > 0 else 0
            } for stat in daily_stats]
        }
        
        return result
    
    @staticmethod
    def get_chatbot_metrics(start_date, end_date):
        """Get chatbot performance metrics"""
        # Get all chatbot interactions in time period
        interactions = ChatbotInteraction.objects.filter(
            timestamp__gte=start_date,
            timestamp__lte=end_date
        )
        
        total_interactions = interactions.count()
        
        # Calculate success rate (interactions with confidence above threshold)
        successful = interactions.filter(confidence_score__gte=0.7).count()
        success_rate = (successful / total_interactions * 100) if total_interactions > 0 else 0
        
        # Get handoffs
        handoffs = interactions.filter(conversation__metadata__has_key='needs_handoff').count()
        handoff_rate = (handoffs / total_interactions * 100) if total_interactions > 0 else 0
        
        # Calculate average feedback
        avg_feedback = interactions.exclude(
            feedback_rating=None
        ).aggregate(
            avg=Avg('feedback_rating')
        )['avg'] or 0
        
        # Get intents breakdown
        intent_stats = interactions.exclude(
            detected_intent=None
        ).values(
            'detected_intent__name'
        ).annotate(
            count=Count('id'),
            avg_confidence=Avg('confidence_score'),
            avg_feedback=Avg('feedback_rating')
        ).order_by('-count')
        
        # Format for response
        result = {
            'summary': {
                'total_interactions': total_interactions,
                'successful_interactions': successful,
                'success_rate': success_rate,
                'handoffs': handoffs,
                'handoff_rate': handoff_rate,
                'avg_feedback': avg_feedback
            },
            'by_intent': [{
                'intent': stat['detected_intent__name'],
                'count': stat['count'],
                'percentage': (stat['count'] / total_interactions * 100) if total_interactions > 0 else 0,
                'avg_confidence': stat['avg_confidence'],
                'avg_feedback': stat['avg_feedback'] or 0
            } for stat in intent_stats]
        }
        
        return result


@shared_task
def generate_daily_metrics():
    """Generate daily metrics for all channels"""
    yesterday = datetime.now().date() - timedelta(days=1)
    start_of_day = datetime.combine(yesterday, datetime.min.time())
    end_of_day = datetime.combine(yesterday, datetime.max.time())
    
    # Process each channel
    channels = Channel.objects.filter(is_active=True)
    for channel in channels:
        # Count messages
        messages = Message.objects.filter(
            channel=channel,
            sent_at__gte=start_of_day,
            sent_at__lte=end_of_day
        )
        
        messages_sent = messages.count()
        messages_delivered = messages.filter(status='delivered').count()
        messages_read = messages.filter(status='read').count()
        
        # Count conversations
        conversations = Conversation.objects.filter(
            channel=channel,
            started_at__gte=start_of_day,
            started_at__lte=end_of_day
        )
        
        conversations_started = conversations.count()
        
        # Count completed conversations
        # A conversation is considered completed if the last message is from the system
        # and there's been no user message in the last 4 hours
        cutoff_time = end_of_day - timedelta(hours=4)
        conversations_completed = 0
        
        for conv in conversations:
            last_message = ConversationMessage.objects.filter(
                conversation=conv
            ).order_by('-created_at').first()
            
            if last_message and not last_message.is_from_user and last_message.created_at <= cutoff_time:
                conversations_completed += 1
        
        # Calculate average response time
        # Time between user message and subsequent system response
        response_times = []
        
        for conv in conversations:
            messages = ConversationMessage.objects.filter(
                conversation=conv
            ).order_by('created_at')
            
            user_message_time = None
            
            for msg in messages:
                if msg.is_from_user:
                    user_message_time = msg.created_at
                elif user_message_time:
                    # Calculate response time in seconds
                    response_time = (msg.created_at - user_message_time).total_seconds()
                    response_times.append(response_time)
                    user_message_time = None
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Create or update metrics record
        ChannelMetrics.objects.update_or_create(
            channel=channel,
            date=yesterday,
            defaults={
                'messages_sent': messages_sent,
                'messages_delivered': messages_delivered,
                'messages_read': messages_read,
                'conversations_started': conversations_started,
                'conversations_completed': conversations_completed,
                'average_response_time': avg_response_time
            }
        )
    
    # Generate chatbot metrics
    interactions = ChatbotInteraction.objects.filter(
        timestamp__gte=start_of_day,
        timestamp__lte=end_of_day
    )
    
    interactions_count = interactions.count()
    successful_interactions = interactions.filter(confidence_score__gte=0.7).count()
    handoffs_count = interactions.filter(conversation__metadata__has_key='needs_handoff').count()
    
    avg_confidence = interactions.aggregate(avg=Avg('confidence_score'))['avg'] or 0
    avg_feedback = interactions.exclude(feedback_rating=None).aggregate(avg=Avg('feedback_rating'))['avg'] or 0
    
    # Create or update chatbot metrics
    ChatbotMetrics.objects.update_or_create(
        date=yesterday,
        defaults={
            'interactions_count': interactions_count,
            'successful_interactions': successful_interactions,
            'handoffs_count': handoffs_count,
            'average_confidence': avg_confidence,
            'average_feedback': avg_feedback
        }
    )
    
    return True
