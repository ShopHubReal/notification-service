"""
Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, EmailStr, UUID4, Field
from typing import Optional, Dict, Any
from datetime import datetime


class EmailRequest(BaseModel):
    """Request schema for sending email."""
    to: EmailStr
    subject: str = Field(..., min_length=1, max_length=255)
    template: str = Field(..., min_length=1, max_length=100)
    context: Dict[str, Any] = Field(default_factory=dict)
    user_id: Optional[UUID4] = None


class SMSRequest(BaseModel):
    """Request schema for sending SMS."""
    to: str = Field(..., min_length=10, max_length=20)
    message: str = Field(..., min_length=1, max_length=1600)
    user_id: Optional[UUID4] = None


class NotificationResponse(BaseModel):
    """Response schema for notification."""
    id: UUID4
    type: str
    channel: str
    recipient: str
    status: str
    sent_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """Response schema for list of notifications."""
    total: int
    notifications: list[NotificationResponse]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    version: str
