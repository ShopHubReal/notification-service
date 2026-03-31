"""
Email service using SendGrid API.
"""
import logging
from typing import Optional
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via SendGrid."""

    def __init__(self):
        """Initialize SendGrid client."""
        if not settings.SENDGRID_API_KEY:
            logger.warning("SENDGRID_API_KEY not configured")
            self.client = None
        else:
            self.client = SendGridAPIClient(settings.SENDGRID_API_KEY)

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Send an email via SendGrid.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            text_content: Plain text content (optional)

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        if not self.client:
            error_msg = "SendGrid client not configured"
            logger.error(error_msg)
            return False, error_msg

        try:
            from_email = Email(settings.SENDGRID_FROM_EMAIL, settings.SENDGRID_FROM_NAME)
            to = To(to_email)

            # Create mail object
            message = Mail(
                from_email=from_email,
                to_emails=to,
                subject=subject,
                html_content=html_content
            )

            # Add plain text content if provided
            if text_content:
                message.plain_text_content = Content("text/plain", text_content)

            # Send email
            response = self.client.send(message)

            if response.status_code >= 200 and response.status_code < 300:
                logger.info(f"Email sent successfully to {to_email}")
                return True, None
            else:
                error_msg = f"SendGrid returned status code {response.status_code}"
                logger.error(f"Failed to send email: {error_msg}")
                return False, error_msg

        except Exception as e:
            error_msg = f"Error sending email: {str(e)}"
            logger.exception(error_msg)
            return False, error_msg


# Singleton instance
email_service = EmailService()
