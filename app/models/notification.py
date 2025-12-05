from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class NotificationStatus(str, Enum):
    """Notification status enumeration."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RETRYING = "retrying"


class NotificationChannel(str, Enum):
    """Notification channel enumeration."""

    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


class Notification(SQLModel, table=True):
    """
    Notification database table model.
    Stores all notification records and their delivery status.
    """

    __tablename__ = "notifications"

    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(index=True, nullable=False)
    recipient_email: str = Field(index=True, max_length=255, nullable=False)
    recipient_name: str = Field(max_length=255, nullable=False)
    subject: str = Field(max_length=500, nullable=False)
    body: str = Field(nullable=False)
    channel: NotificationChannel = Field(
        default=NotificationChannel.EMAIL, nullable=False
    )
    status: NotificationStatus = Field(
        default=NotificationStatus.PENDING, nullable=False, index=True
    )
    retry_count: int = Field(default=0, nullable=False)
    error_message: Optional[str] = Field(default=None, nullable=True)
    created_at: datetime = Field(
        default_factory=datetime.utcnow, nullable=False, index=True
    )
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    sent_at: Optional[datetime] = Field(default=None, nullable=True)


# Pydantic Schemas for API requests/responses


class NotificationBase(SQLModel):
    """
    Base notification schema with shared fields.
    Used as foundation for other notification schemas.
    """

    employee_id: int
    recipient_email: str = Field(max_length=255)
    recipient_name: str = Field(max_length=255)
    subject: str = Field(max_length=500)
    body: str
    channel: NotificationChannel = NotificationChannel.EMAIL


class NotificationCreate(NotificationBase):
    """
    Schema for creating a new notification.
    Inherits all required fields from NotificationBase.
    """

    pass


class NotificationUpdate(SQLModel):
    """
    Schema for updating an existing notification.
    All fields are optional to support partial updates.
    """

    status: Optional[NotificationStatus] = None
    retry_count: Optional[int] = None
    error_message: Optional[str] = None


class NotificationPublic(NotificationBase):
    """
    Schema for notification responses.
    Includes the id field and computed fields from database.
    """

    id: int
    status: NotificationStatus
    retry_count: int
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    sent_at: Optional[datetime] = None


class NotificationListResponse(SQLModel):
    """
    Schema for list response with pagination info.
    """

    total: int
    offset: int
    limit: int
    items: list[NotificationPublic]
