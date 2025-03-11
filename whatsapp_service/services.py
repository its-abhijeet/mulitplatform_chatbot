
from datetime import datetime
from django.template import Template as DjangoTemplate, Context
from django.conf import settings
from celery import shared_task
from twilio.rest import Client
from communications.models import Channel, Template, Message, Conversation, ConversationMessage
from whatsapp_service.models import WhatsAppAccount, WhatsAppMessage, AutoReply

class WhatsAppService:
    @staticmethod
    def get_twilio_client(account):
        """Get configured Twilio client for WhatsApp account"""
        return Client(account.twilio_account_sid, account.twilio_auth_token)
    
    @staticmethod
    def send_message(account_id, recipient, content, media_url=None, template_id=None):
        """Send a WhatsApp message to a recipient"""
        account = WhatsAppAccount.objects.get(id=account_id)
        channel = Channel.objects.get(type='whatsapp', configuration__account_id=account_id)
        
        # Get template if provided
        template = None
        if template_id:
            template = Template.objects.get(id=template_id)
            
            # Process template if variables provided
            if template:
                django_template = DjangoTemplate(template.content)
                content = django_template.render(Context({}))  # In real use, variables would be passed
        
        # Create message record
        message = Message.objects.create(
            channel=channel,
            template=template,
            recipient=recipient,
            content=content,
            status='pending'
        )
        
        # Create WhatsApp specific details
        whatsapp_message = WhatsAppMessage.objects.create(
            message=message,
            account=account,
            media_url=media_url or '',
            media_type=media_url.split('.')[-1] if media_url else '' if media_url else ''
        )
        
        # Queue actual sending
        send_whatsapp_message.delay(whatsapp_message.id)
        
        return message
    
    @staticmethod
    def send_broadcast(account_id, recipients, content, media_url=None, template_id=None):
        """Send WhatsApp message to multiple recipients"""
        messages = []
        for recipient in recipients:
            message = WhatsAppService.send_message(
                account_id, 
                recipient, 
                content, 
                media_url, 
                template_id
            )
            messages.append(message)
        
        return messages
    
    @staticmethod
    def process_incoming_message(account_id, from_number, message_content, media_url=None, twilio_message_id=None):
        """Process an incoming WhatsApp message"""
        account = WhatsAppAccount.objects.get(id=account_id)
        channel = Channel.objects.get(type='whatsapp', configuration__account_id=account_id)
        
        # Find or create conversation
        conversation, created = Conversation.objects.get_or_create(
            channel=channel,
            external_id=from_number,
            defaults={
                'metadata': {'account_id': account_id}
            }
        )
        
        # Create conversation message
        ConversationMessage.objects.create(
            conversation=conversation,
            is_from_user=True,
            content=message_content,
            attachments=[{'url': media_url}] if media_url else [],
            metadata={
                'twilio_message_id': twilio_message_id
            }
        )
        
        # Check for auto-replies
        auto_reply = WhatsAppService.check_auto_replies(account_id, message_content)
        if auto_reply:
            response = WhatsAppService.send_message(
                account_id,
                from_number,
                auto_reply.response_text
            )
            
            # Create system message in conversation
            ConversationMessage.objects.create(
                conversation=conversation,
                is_from_user=False,
                content=auto_reply.response_text,
                metadata={
                    'auto_reply_id': auto_reply.id,
                    'message_id': response.id
                }
            )
            
            return {
                'conversation_id': conversation.id,
                'auto_reply': True,
                'response_message_id': response.id
            }
        
        # If no auto-reply matches, this may need human attention
        return {
            'conversation_id': conversation.id,
            'auto_reply': False
        }
    
    @staticmethod
    def check_auto_replies(account_id, message_content):
        """Check if any auto-reply rules match the message content"""
        auto_replies = AutoReply.objects.filter(
            account_id=account_id,
            is_active=True
        )
        
        for auto_reply in auto_replies:
            # Simple pattern matching - could be enhanced with regex
            if auto_reply.trigger_pattern.lower() in message_content.lower():
                return auto_reply
        
        return None


# Celery tasks
@shared_task
def send_whatsapp_message(whatsapp_message_id):
    """Send a WhatsApp message via Twilio"""
    whatsapp_message = WhatsAppMessage.objects.get(id=whatsapp_message_id)
    message = whatsapp_message.message
    account = whatsapp_message.account
    
    try:
        client = WhatsAppService.get_twilio_client(account)
        
        # Format WhatsApp number with proper prefix
        to_whatsapp = f"whatsapp:{message.recipient}"
        from_whatsapp = f"whatsapp:{account.phone_number}"
        
        # Prepare message parameters
        message_params = {
            'from_': from_whatsapp,
            'body': message.content,
            'to': to_whatsapp
        }
        
        # Add media if present
        if whatsapp_message.media_url:
            message_params['media_url'] = [whatsapp_message.media_url]
        
        # Send message through Twilio
        twilio_message = client.messages.create(**message_params)
        
        # Update message status
        whatsapp_message.twilio_message_id = twilio_message.sid
        whatsapp_message.save()
        
        message.status = 'sent'
        message.sent_at = datetime.now()
        message.save()
        
        return True
        
    except Exception as e:
        message.status = 'failed'
        message.metadata = {'error': str(e)}
        message.save()
        return False


@shared_task
def update_message_status():
    """Update delivery status for WhatsApp messages"""
    # Get recent messages that are sent but not confirmed delivered
    recent_messages = WhatsAppMessage.objects.filter(
        message__status='sent'
    ).select_related('message', 'account')
    
    for whatsapp_message in recent_messages:
        try:
            # Skip if no Twilio message ID
            if not whatsapp_message.twilio_message_id:
                continue
                
            message = whatsapp_message.message
            account = whatsapp_message.account
            client = WhatsAppService.get_twilio_client(account)
            
            # Fetch message status from Twilio
            twilio_message = client.messages(whatsapp_message.twilio_message_id).fetch()
            
            # Update status
            if twilio_message.status == 'delivered':
                message.status = 'delivered'
                message.delivered_at = datetime.now()
            elif twilio_message.status == 'read':
                message.status = 'read'
                message.delivered_at = message.delivered_at or datetime.now()
                message.read_at = datetime.now()
            elif twilio_message.status in ['failed', 'undelivered']:
                message.status = 'failed'
                
            message.save()
            
        except Exception as e:
            print(f"Error updating message {whatsapp_message.id}: {str(e)}")