"""
Email service for OTP sending and user communications
Uses Django's email backend with professional HTML templates
"""

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import random
import string
import logging

logger = logging.getLogger(__name__)


class OTPService:
    """Service for generating and sending OTPs via email"""
    
    # Get config from Django settings
    OTP_LENGTH = getattr(settings, 'OTP_LENGTH', 6)
    OTP_EXPIRY_MINUTES = getattr(settings, 'OTP_EXPIRY_MINUTES', 10)
    OTP_MAX_ATTEMPTS = getattr(settings, 'OTP_MAX_ATTEMPTS', 5)
    
    @staticmethod
    def generate_otp():
        """Generate a random 6-digit OTP"""
        return ''.join(random.choices(string.digits, k=OTPService.OTP_LENGTH))
    
    @staticmethod
    def send_driver_otp_email(email, phone_number, otp):
        """
        Send OTP to driver via email with professional template
        
        Args:
            email (str): Driver's email address
            phone_number (str): Driver's phone number
            otp (str): 6-digit OTP code
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        try:
            # Prepare context for template
            context = {
                'email': email,
                'phone_number': phone_number,
                'otp': otp,
                'otp_expiry_minutes': OTPService.OTP_EXPIRY_MINUTES,
                'app_name': 'AIMall Driver',
                'support_email': settings.DEFAULT_FROM_EMAIL,
            }
            
            # Render HTML template
            html_message = render_to_string('emails/driver_otp.html', context)
            plain_message = render_to_string('emails/driver_otp.txt', context)
            
            # Create email
            subject = 'Your AIMall Driver Login Code'
            from_email = settings.DEFAULT_FROM_EMAIL
            to_email = email
            
            email_obj = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,
                from_email=from_email,
                to=[to_email]
            )
            
            # Attach HTML version
            email_obj.attach_alternative(html_message, "text/html")
            
            # Send email
            email_obj.send(fail_silently=False)
            logger.info(f"OTP email sent successfully to {email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send OTP email to {email}: {str(e)}")
            return False
    
    @staticmethod
    def send_verification_email(email, verification_link):
        """
        Send email verification link
        
        Args:
            email (str): User's email address
            verification_link (str): Full verification URL
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        try:
            context = {
                'email': email,
                'verification_link': verification_link,
                'app_name': 'AIMall Driver',
                'support_email': settings.DEFAULT_FROM_EMAIL,
            }
            
            html_message = render_to_string('emails/verify_email.html', context)
            plain_message = render_to_string('emails/verify_email.txt', context)
            
            subject = 'Verify Your AIMall Driver Account'
            from_email = settings.DEFAULT_FROM_EMAIL
            
            email_obj = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,
                from_email=from_email,
                to=[email]
            )
            
            email_obj.attach_alternative(html_message, "text/html")
            email_obj.send(fail_silently=False)
            logger.info(f"Verification email sent to {email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send verification email to {email}: {str(e)}")
            return False


class EmailTemplateRenderer:
    """Utility class for rendering email templates with consistent styling"""
    
    @staticmethod
    def get_base_styles():
        """Get consistent CSS styles for emails"""
        return """
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                background-color: #f5f5f5;
            }
            
            .email-container {
                max-width: 600px;
                margin: 0 auto;
                background-color: #ffffff;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                overflow: hidden;
            }
            
            .email-header {
                background: linear-gradient(135deg, #2E7D32 0%, #1B5E20 100%);
                padding: 40px 20px;
                text-align: center;
                color: white;
            }
            
            .email-header h1 {
                margin: 0;
                font-size: 28px;
                font-weight: 600;
            }
            
            .email-header p {
                margin: 5px 0 0 0;
                font-size: 14px;
                opacity: 0.9;
            }
            
            .email-body {
                padding: 40px 30px;
            }
            
            .email-body h2 {
                color: #2E7D32;
                font-size: 20px;
                margin-top: 0;
            }
            
            .email-body p {
                margin: 15px 0;
                font-size: 15px;
                line-height: 1.8;
            }
            
            .otp-section {
                background-color: #f0f7f4;
                border-left: 4px solid #2E7D32;
                padding: 20px;
                margin: 25px 0;
                border-radius: 4px;
            }
            
            .otp-code {
                font-size: 32px;
                font-weight: 700;
                letter-spacing: 8px;
                text-align: center;
                color: #2E7D32;
                font-family: 'Courier New', monospace;
                margin: 15px 0;
                padding: 15px;
                background-color: #ffffff;
                border-radius: 4px;
                border: 2px dashed #2E7D32;
            }
            
            .otp-label {
                text-align: center;
                font-size: 13px;
                color: #666;
                margin-bottom: 10px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            
            .expiry-warning {
                font-size: 13px;
                color: #d32f2f;
                text-align: center;
                margin-top: 10px;
                font-weight: 500;
            }
            
            .action-button {
                display: inline-block;
                background-color: #2E7D32;
                color: white;
                padding: 12px 30px;
                text-decoration: none;
                border-radius: 4px;
                font-weight: 600;
                margin: 20px auto;
                display: block;
                width: fit-content;
            }
            
            .action-button:hover {
                background-color: #1B5E20;
            }
            
            .info-box {
                background-color: #e8f5e9;
                border-radius: 4px;
                padding: 15px;
                margin: 20px 0;
                border-left: 3px solid #4caf50;
            }
            
            .info-box strong {
                color: #2E7D32;
            }
            
            .email-footer {
                background-color: #f5f5f5;
                padding: 30px;
                text-align: center;
                border-top: 1px solid #eee;
                font-size: 12px;
                color: #999;
            }
            
            .email-footer p {
                margin: 5px 0;
            }
            
            .footer-link {
                color: #2E7D32;
                text-decoration: none;
            }
            
            .footer-link:hover {
                text-decoration: underline;
            }
            
            .divider {
                border: none;
                border-top: 1px solid #eee;
                margin: 30px 0;
            }
            
            .highlight {
                color: #2E7D32;
                font-weight: 600;
            }
        </style>
        """
