"""
SMS service using Twilio API.
"""
import logging
from typing import Optional
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from config import settings

logger = logging.getLogger(__name__)


class SMSService:
    """Service for sending SMS via Twilio."""

    def __init__(self):
        """Initialize Twilio client."""
        if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
            logger.warning("Twilio credentials not configured")
            self.client = None
        else:
            self.client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )

    async def send_sms(
        self,
        to_phone: str,
        message: str
    ) -> tuple[bool, Optional[str]]:
        """
        Send an SMS via Twilio.

        Args:
            to_phone: Recipient phone number (E.164 format)
            message: SMS message content

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        if not self.client:
            error_msg = "Twilio client not configured"
            logger.error(error_msg)
            return False, error_msg

        if not settings.TWILIO_FROM_PHONE:
            error_msg = "TWILIO_FROM_PHONE not configured"
            logger.error(error_msg)
            return False, error_msg

        try:
            # Send SMS
            twilio_message = self.client.messages.create(
                body=message,
                from_=settings.TWILIO_FROM_PHONE,
                to=to_phone
            )

            if twilio_message.sid:
                logger.info(f"SMS sent successfully to {to_phone}, SID: {twilio_message.sid}")
                return True, None
            else:
                error_msg = "Failed to get message SID from Twilio"
                logger.error(error_msg)
                return False, error_msg

        except TwilioRestException as e:
            error_msg = f"Twilio error: {e.msg} (code: {e.code})"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Error sending SMS: {str(e)}"
            logger.exception(error_msg)
            return False, error_msg


# Singleton instance
sms_service = SMSService()
