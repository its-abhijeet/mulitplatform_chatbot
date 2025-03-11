# reporting/services.py
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
import csv
import json
import io
from datetime import datetime
from weasyprint import HTML
from celery import shared_task
from analytics.services import AnalyticsService
from reporting.models import Report

class ReportingService:
    """Services for generating and managing reports"""
    
    @staticmethod
    def generate_report(report_id):
        """Generate a report based on stored parameters"""
        report = Report.objects.get(id=report_id)
        
        # Set date range
        start_date = report.date_from
        end_date = report.date_to
        
        # Get data based on report type
        data = {}
        
        if report.type == 'email':
            data = AnalyticsService.get_email_performance(start_date, end_date)
        elif report.type == 'whatsapp':
            data = AnalyticsService.get_whatsapp_performance(start_date, end_date)
        elif report.type == 'chatbot':
            data = AnalyticsService.get_chatbot_metrics(start_date, end_date)
        elif report.type == 'conversation':
            # Get data for all specified channels
            channels_data = {}
            for channel in report.channels.all():
                channels_data[channel.name] = AnalyticsService.get_channel_metrics(
                    channel.id, start_date, end_date
                )
            data = {'channels': channels_data}
        elif report.type == 'custom':
            # Custom report logic would use report.parameters
            pass
        
        # Generate file in requested format
        if report.format == 'pdf':
            file_content = ReportingService._generate_pdf(report, data)
            filename = f"{report.name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
        elif report.format == 'csv':
            file_content = ReportingService._generate_csv(report, data)
            filename = f"{report.name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv"
        elif report.format == 'json':
            file_content = ReportingService._generate_json(report, data)
            filename = f"{report.name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.json"
        
        # Save file to report
        report.file.save(filename, ContentFile(file_content))
        
        return report
    
    @staticmethod
    def _generate_pdf(report, data):
        """Generate PDF report"""
        # Create context for template
        context = {
            'report': report,
            'data': data,
            'generated_at': datetime.now()
        }
        
        # Render HTML template
        if report.type == 'email':
            html_content = render_to_string('reports/email_report.html', context)
        elif report.type == 'whatsapp':
            html_content = render_to_string('reports/whatsapp_report.html', context)
        elif report.type == 'chatbot':
            html_content = render_to_string('reports/chatbot_report.html', context)
        elif report.type == 'conversation':
            html_content = render_to_string('reports/conversation_report.html', context)
        else:
            html_content = render_to_string('reports/custom_report.html', context)
        
        # Generate PDF using WeasyPrint
        pdf = HTML(string=html_content).write_pdf()
        
        return pdf
    
    @staticmethod
    def _generate_csv(report, data):
        """Generate CSV report"""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers and data based on report type
        if report.type == 'email':
            # Write summary
            writer.writerow(['Email Performance Summary'])
            writer.writerow(['Metric', 'Value'])
            for key, value in data['summary'].items():
                writer.writerow([key, value])
            
            # Write daily stats
            writer.writerow([])
            writer.writerow(['Daily Performance'])
            writer.writerow(['Date', 'Sent', 'Opened', 'Clicked', 'Open Rate (%)', 'Click Rate (%)'])
            for day in data['daily']:
                writer.writerow([
                    day['date'],
                    day['sent'],
                    day['opened'],
                    day['clicked'],
                    f"{day['open_rate']:.2f}",
                    f"{day['click_rate']:.2f}"
                ])
        
        # Similar implementation for other report types
        
        return output.getvalue().encode('utf-8')
    
    @staticmethod
    def _generate_json(report, data):
        """Generate JSON report"""
        # Add metadata
        result = {
            'report_name': report.name,
            'report_type': report.type,
            'date_from': report.date_from.strftime('%Y-%m-%d'),
            'date_to': report.date_to.strftime('%Y-%m-%d'),
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data': data
        }
        
        return json.dumps(result, indent=2).encode('utf-8')


@shared_task
def generate_scheduled_report(report_id):
    """Celery task to generate a scheduled report"""
    ReportingService.generate_report(report_id)
    return True