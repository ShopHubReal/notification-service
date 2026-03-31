"""
API routes for notification endpoints.
"""
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
from uuid import UUID

from database import get_db
from models.database import NotificationLog
from models.schemas import (
    EmailRequest,
    SMSRequest,
    NotificationResponse,
    NotificationListResponse
)
from services.email_service import email_service
from services.sms_service import sms_service
from services.template_service import template_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/email", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
async def send_email(
    request: EmailRequest,
    db: Session = Depends(get_db)
):
    """
    Send an email notification.

    Args:
        request: Email request details
        db: Database session

    Returns:
        Notification response with status
    """
    try:
        # Render template
        subject, html_content = template_service.render_template(
            request.template,
            {**request.context, "subject": request.subject}
        )

        # Send email
        success, error_message = await email_service.send_email(
            to_email=request.to,
            subject=subject,
            html_content=html_content
        )

        # Create notification log
        notification = NotificationLog(
            user_id=request.user_id,
            type="email",
            channel="sendgrid",
            recipient=request.to,
            subject=subject,
            template=request.template,
            status="sent" if success else "failed",
            error_message=error_message,
            sent_at=datetime.utcnow() if success else None
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)

        if not success:
            logger.error(f"Failed to send email: {error_message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send email: {error_message}"
            )

        logger.info(f"Email sent successfully to {request.to}")
        return notification

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error sending email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/sms", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
async def send_sms(
    request: SMSRequest,
    db: Session = Depends(get_db)
):
    """
    Send an SMS notification.

    Args:
        request: SMS request details
        db: Database session

    Returns:
        Notification response with status
    """
    try:
        # Send SMS
        success, error_message = await sms_service.send_sms(
            to_phone=request.to,
            message=request.message
        )

        # Create notification log
        notification = NotificationLog(
            user_id=request.user_id,
            type="sms",
            channel="twilio",
            recipient=request.to,
            subject=None,
            template=None,
            status="sent" if success else "failed",
            error_message=error_message,
            sent_at=datetime.utcnow() if success else None
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)

        if not success:
            logger.error(f"Failed to send SMS: {error_message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send SMS: {error_message}"
            )

        logger.info(f"SMS sent successfully to {request.to}")
        return notification

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error sending SMS: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/user/{user_id}", response_model=NotificationListResponse)
async def get_user_notifications(
    user_id: UUID,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Get notification history for a user.

    Args:
        user_id: User ID
        limit: Maximum number of notifications to return
        offset: Offset for pagination
        db: Database session

    Returns:
        List of notifications for the user
    """
    try:
        # Query notifications
        query = db.query(NotificationLog).filter(
            NotificationLog.user_id == user_id
        ).order_by(desc(NotificationLog.created_at))

        total = query.count()
        notifications = query.limit(limit).offset(offset).all()

        return NotificationListResponse(
            total=total,
            notifications=[
                NotificationResponse.model_validate(notif)
                for notif in notifications
            ]
        )

    except Exception as e:
        logger.exception(f"Error fetching notifications: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get notification details by ID.

    Args:
        notification_id: Notification ID
        db: Database session

    Returns:
        Notification details
    """
    try:
        notification = db.query(NotificationLog).filter(
            NotificationLog.id == notification_id
        ).first()

        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )

        return notification

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error fetching notification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )
