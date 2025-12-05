from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import func, select

from app.api.dependencies import CurrentUserDep, SessionDep
from app.core.database import get_session
from app.core.logging import get_logger
from app.models.notification import (
    Notification,
    NotificationCreate,
    NotificationListResponse,
    NotificationPublic,
    NotificationStatus,
)
from app.services.email import send_email_message, send_notification_email

logger = get_logger(__name__)

# Create router with prefix and tags for better organization
router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
)


async def send_email_background(
    notification_id: int,
    recipient_email: str,
    recipient_name: str,
    subject: str,
    body: str,
) -> None:
    """
    Background task to send email and update notification status.
    Args:
        notification_id: ID of the notification
        recipient_email: Email address of recipient
        recipient_name: Name of recipient
        subject: Email subject
        body: Email body
    """
    session_gen = get_session()
    session = next(session_gen)

    try:
        success = await send_notification_email(
            to_email=recipient_email,
            to_name=recipient_name,
            subject=subject,
            body=body,
        )

        notification = session.get(Notification, notification_id)
        if notification:
            if success:
                notification.status = NotificationStatus.SENT
                notification.sent_at = datetime.now()
                logger.info(f"Notification {notification_id} sent successfully")
            else:
                notification.retry_count += 1
                if notification.retry_count >= 3:
                    notification.status = NotificationStatus.FAILED
                    notification.error_message = "Max retries exceeded"
                    logger.error(
                        f"Notification {notification_id} failed after max retries"
                    )
                else:
                    notification.status = NotificationStatus.RETRYING
                    notification.error_message = "Email send failed, will retry"
                    logger.warning(
                        f"Notification {notification_id} will be retried (attempt {notification.retry_count})"
                    )
            notification.updated_at = datetime.now()
            session.add(notification)
            session.commit()
    except Exception as e:
        logger.error(
            f"Error in background email task for notification {notification_id}: {str(e)}"
        )
        try:
            notification = session.get(Notification, notification_id)
            if notification:
                notification.status = NotificationStatus.FAILED
                notification.error_message = str(e)
                notification.retry_count += 1
                notification.updated_at = datetime.now()
                session.add(notification)
                session.commit()
        except Exception as db_error:
            logger.error(f"Failed to update notification status: {str(db_error)}")
    finally:
        session.close()


# Send notification endpoint
@router.post("/send", response_model=NotificationPublic, status_code=201)
async def send_notification(
    notification: NotificationCreate,
    session: SessionDep,
    background_tasks: BackgroundTasks,
) -> Notification:
    """
    Send a new notification.

    Args:
        notification: Notification data from request body
        session: Database session (injected)
        background_tasks: FastAPI background tasks
    """
    logger.info(
        f"Creating new notification for employee {notification.employee_id} to {notification.recipient_email}"
    )

    # Create notification in database
    db_notification = Notification.model_validate(notification)
    db_notification.status = NotificationStatus.PENDING
    db_notification.created_at = datetime.now()
    db_notification.updated_at = datetime.now()
    session.add(db_notification)
    session.commit()
    session.refresh(db_notification)

    logger.info(f"Notification {db_notification.id} created successfully")

    # Add background task to send email
    background_tasks.add_task(
        send_email_background,
        notification_id=db_notification.id,
        recipient_email=notification.recipient_email,
        recipient_name=notification.recipient_name,
        subject=notification.subject,
        body=notification.body,
    )

    return db_notification


@router.get("/{notification_id}", response_model=NotificationPublic)
def get_notification(notification_id: int, session: SessionDep) -> Notification:
    """
    Retrieve a single notification by ID.

    Args:
        notification_id: The ID of the notification to retrieve
        session: Database session (injected)
    """
    logger.info(f"Fetching notification with ID: {notification_id}")
    notification = session.get(Notification, notification_id)
    if not notification:
        logger.warning(f"Notification with ID {notification_id} not found")
        raise HTTPException(status_code=404, detail="Notification not found")
    logger.info(f"Notification {notification_id} found")
    return notification


@router.get("/employee/{employee_id}", response_model=NotificationListResponse)
def get_employee_notifications(
    employee_id: int,
    session: SessionDep,
    offset: int = Query(0, ge=0),
    limit: Annotated[int, Query(le=100)] = 100,
) -> NotificationListResponse:
    """
    Retrieve all notifications for a specific employee with pagination.

    Args:
        employee_id: The ID of the employee
        session: Database session (injected)
        offset: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: 100, max: 100)
    """
    logger.info(
        f"Fetching notifications for employee {employee_id} with offset={offset}, limit={limit}"
    )

    # Get total count
    total = session.exec(
        select(func.count(Notification.id)).where(
            Notification.employee_id == employee_id
        )
    ).first()

    # Get paginated results
    notifications = session.exec(
        select(Notification)
        .where(Notification.employee_id == employee_id)
        .offset(offset)
        .limit(limit)
    ).all()

    logger.info(
        f"Retrieved {len(notifications)} notification(s) for employee {employee_id}"
    )

    return NotificationListResponse(
        total=total or 0,
        offset=offset,
        limit=limit,
        items=list(notifications),
    )


# Protected endpoint for testing authentication is working
@router.get("/auth/check")
def auth_check(current_user: CurrentUserDep):
    return {
        "auth": "ok",
        "username": current_user.username,
    }


class BasicNotificaiton(BaseModel):
    recipient_email: str
    subject: str
    body: str


# Test Notification Endpoint (for testing)
@router.post("/basic/notify")
async def send_basic_notification_test(
    request: BasicNotificaiton, background_tasks: BackgroundTasks
):
    """
    Send an instant notification email without saving to database.
    Used for testing email functionality.

    Args:
        request: Instant notification request data
        background_tasks: FastAPI background tasks
    """
    logger.info(f"Sending instant notification to {request.recipient_email}")

    # Add background task to send email
    background_tasks.add_task(
        send_email_message,
        msg_from="HRMS",
        msg_to=request.recipient_email,
        msg_subject=request.subject,
        msg_body=request.body,
    )

    return {"message": "Instant notification is being sent in the background"}
