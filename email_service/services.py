import csv
import io
from datetime import datetime
from django.core.files.storage import default_storage
from django.template import Template as DjangoTemplate, Context
from django.conf import settings
from celery import shared_task
from communications.models import Channel, Template, Message
from email_service.models import EmailBatch, EmailMessage

class EmailService:
    @staticmethod
    def create_batch(name, description, file):
        """Create a new email batch from uploaded CSV file"""
        batch = EmailBatch.objects.create(
            name=name,
            description=description,
            recipients_file=file
        )
        return batch
    
    @staticmethod
    def process_batch(batch_id, template_id, schedule_time=None):
        """Process an email batch by creating messages for each recipient"""
        batch = EmailBatch.objects.get(id=batch_id)
        template = Template.objects.get(id=template_id)
        channel = template.channel
        
        # Read CSV file
        file_path = batch.recipients_file.path
        with open(file_path, 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Ensure required field exists
                if 'email' not in row:
                    continue
                
                # Process template variables
                context = Context(row)
                django_template = DjangoTemplate(template.content)
                rendered_content = django_template.render(context)
                
                subject_template = DjangoTemplate(template.subject)
                rendered_subject = subject_template.render(context)
                
                # Create message
                message = Message.objects.create(
                    channel=channel,
                    template=template,
                    recipient=row['email'],
                    subject=rendered_subject,
                    content=rendered_content,
                    scheduled_at=schedule_time,
                    status='pending'
                )
                
                # Create email specific details
                EmailMessage.objects.create(
                    message=message,
                    batch=batch
                )
        
        batch.processed = True
        batch.save()
        
        # If immediate sending (no schedule)
        if not schedule_time:
            send_batch_emails.delay(batch_id)
        
        return batch
    
    @staticmethod
    def check_spam_score(content):
        """Calculate spam score for email content"""
        # This would be a more complex implementation in production
        # Simplified version for demonstration
        spam_keywords = ['free', 'discount', 'offer', 'limited time', 'act now', 'click here']
        score = 0
        content_lower = content.lower()
        
        for keyword in spam_keywords:
            if keyword in content_lower:
                score += 0.1
        
        return min(score, 1.0)
    
    @staticmethod
    def track_email_open(email_id, ip_address=None, user_agent=None):
        """Track email open event"""
        try:
            email = EmailMessage.objects.get(id=email_id)
            email.opens += 1
            email.save()
            return True
        except EmailMessage.DoesNotExist:
            return False
    
    @staticmethod
    def track_email_click(email_id, url, ip_address=None, user_agent=None):
        """Track email link click event"""
        try:
            email = EmailMessage.objects.get(id=email_id)
            email.clicks += 1
            email.save()
            
            # Create click event
            EmailClick.objects.create(
                email=email,
                url=url,
                ip_address=ip_address,
                user_agent=user_agent
            )
            return True
        except EmailMessage.DoesNotExist:
            return False


# Celery tasks for email service
@shared_task
def send_batch_emails(batch_id):
    """Send all emails in a batch"""
    batch = EmailBatch.objects.get(id=batch_id)
    email_messages = EmailMessage.objects.filter(batch=batch, message__status='pending')
    
    for email in email_messages:
        send_email.delay(email.message.id)


@shared_task
def send_email(message_id):
    """Send individual email through SendGrid"""
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
    
    message = Message.objects.get(id=message_id)
    email_details = message.email_details
    
    # Update spam score
    email_details.spam_score = EmailService.check_spam_score(message.content)
    email_details.save()
    
    # Skip sending if spam score is too high
    if email_details.spam_score > 0.7:
        message.status = 'failed'
        message.save()
        return False
    
    # Prepare email with tracking
    tracking_pixel = f"<img src='{settings.BASE_URL}/api/email/track/{email_details.id}/open' width='1' height='1' />"
    content_with_tracking = message.content + tracking_pixel
    
    # Add tracking to links
    # This is simplified - production would need proper HTML parsing
    # import re
    # content_with_tracking = re.sub(
    #     r'href=[\'"]([^\'"]+)[\'"]',
    #     f'href="{settings.BASE_URL}/api/email/track/{email_details.id}/click?url=\\1"',
    #     content_with_tracking
    # )
    
    try:
        sendgrid_email = Mail(
            from_email=settings.DEFAULT_FROM_EMAIL,
            to_emails=message.recipient,
            subject=message.subject,
            html_content=content_with_tracking
        )
        
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(sendgrid_email)
        
        # Update message status
        if response.status_code >= 200 and response.status_code < 300:
            message.status = 'sent'
            message.sent_at = datetime.now()
            message.save()
            return True
        else:
            message.status = 'failed'
            message.save()
            return False
            
    except Exception as e:
        message.status = 'failed'
        message.metadata = {'error': str(e)}
        message.save()
        return False


@shared_task
def check_scheduled_emails():
    """Check for emails that need to be sent based on schedule"""
    now = datetime.now()
    scheduled_messages = Message.objects.filter(
        status='pending',
        scheduled_at__lte=now
    )
    
    for message in scheduled_messages:
        send_email.delay(message.id)