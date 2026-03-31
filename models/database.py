"""
SQLAlchemy database models for notification service.
"""
from sqlalchemy import Column, String, Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from database import Base
import uuid


class NotificationLog(Base):
    """
    Notification log table for tracking all sent notifications.
    """
    __tablename__ = "notification_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    type = Column(String(50), nullable=False)  # email, sms
    channel = Column(String(50), nullable=False)  # sendgrid, twilio
    recipient = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=True)
    template = Column(String(100), nullable=True)
    status = Column(String(20), default="pending", index=True)  # pending, sent, failed
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<NotificationLog(id={self.id}, type={self.type}, status={self.status})>"
