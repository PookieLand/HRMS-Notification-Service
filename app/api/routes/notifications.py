from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks

from app.api.dependencies import CurrentUserDep
from app.core.logging import get_logger
from app.models.notifications import (
    BasicNotification,
    CongratulationsEmailRequest,
    NotificationEmailRequest,
    ReminderEmailRequest,
    TemplatedEmailRequest,
    TemplatedEmailResponse,
    WelcomeEmailRequest,
)
from app.services.email import (
    get_email_health_status,
    send_congratulations,
    send_email_message,
    send_notification,
    send_reminder,
    send_templated_email,
    send_welcome_email,
)
from app.services.template_service import EmailType

logger = get_logger(__name__)

# Create router with prefix and tags for better organization
router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
)


# Protected endpoint for testing authentication is working
@router.get("/auth/check")
def auth_check(current_user: CurrentUserDep):
    return {
        "auth": "ok",
        "username": current_user.username,
    }


@router.get("/health/providers")
async def get_email_provider_health():
    """
    Get health status of all configured email providers.

    Returns information about:
    - Primary email provider (SES or SMTP)
    - Fallback provider status
    - Provider-specific metrics (e.g., SES quota)

    Useful for monitoring and debugging email delivery issues.
    """
    logger.info("Checking email provider health status")
    health_status = await get_email_health_status()
    return health_status


@router.post("/basic/notify")
async def send_basic_notification_test(
    request: BasicNotification, background_tasks: BackgroundTasks
):
    """
    Send an instant notification email without saving to database.
    Used for testing email functionality.

    Args:
        request: Instant notification request data
        background_tasks: FastAPI background tasks
    """
    logger.info(f"Sending instant notification to {request.recipient_email}")

    background_tasks.add_task(
        send_email_message,
        msg_from=request.email_from,
        msg_to=request.recipient_email,
        msg_subject=request.subject,
        msg_body=request.body,
    )

    return {"message": "Instant notification is being sent in the background"}


async def send_templated_email_background(
    email_type: EmailType,
    recipient_email: str,
    subject: str,
    context: Dict[str, Any],
) -> None:
    """Background task to send templated email."""
    try:
        success = await send_templated_email(
            to_email=recipient_email,
            subject=subject,
            email_type=email_type,
            context=context,
        )
        if success:
            logger.info(
                f"Templated email ({email_type.value}) sent successfully to {recipient_email}"
            )
        else:
            logger.error(
                f"Failed to send templated email ({email_type.value}) to {recipient_email}"
            )
    except Exception as e:
        logger.error(
            f"Error sending templated email ({email_type.value}) to {recipient_email}: {str(e)}"
        )


@router.post("/generic/send", response_model=TemplatedEmailResponse)
async def send_templated_notification(
    request: TemplatedEmailRequest,
    background_tasks: BackgroundTasks,
):
    """
    Send a professionally styled, templated notification email.

    This endpoint supports multiple email types with dynamic content:
    - **welcome**: New employee welcome emails with account details
    - **notification**: General notifications (leave approvals, updates, etc.)
    - **reminder**: Time-sensitive reminders with urgency levels
    - **congratulations**: Celebration emails for achievements/promotions

    All templates are responsive and work across email clients.
    """
    logger.info(
        f"Sending {request.email_type.value} email to {request.recipient_email}"
    )

    # Build context based on email type
    context: Dict[str, Any] = {
        "username": request.recipient_name,
        "recipient_name": request.recipient_name,
        "subject": request.subject,
    }

    # Add optional common fields
    if request.message:
        context["message"] = request.message
    if request.details:
        context["details"] = request.details
    if request.action_url:
        context["action_url"] = request.action_url
    if request.action_text:
        context["action_text"] = request.action_text
    if request.company_name:
        context["company_name"] = request.company_name
    if request.sender_name:
        context["sender_name"] = request.sender_name

    # Add type-specific fields
    if request.email_type == EmailType.WELCOME:
        if request.employee_id:
            context["employee_id"] = request.employee_id
        if request.department:
            context["department"] = request.department
        if request.role:
            context["role"] = request.role
        if request.start_date:
            context["start_date"] = request.start_date
        context["email"] = request.recipient_email

    elif request.email_type == EmailType.REMINDER:
        if request.reminder_title:
            context["reminder_title"] = request.reminder_title
        if request.reminder_message:
            context["reminder_message"] = request.reminder_message
        if request.due_date:
            context["due_date"] = request.due_date
        if request.urgency:
            context["urgency"] = request.urgency

    elif request.email_type == EmailType.NOTIFICATION:
        context["title"] = request.subject
        if request.message:
            context["notification_title"] = request.subject
            context["intro_message"] = request.message

    elif request.email_type == EmailType.CONGRATULATIONS:
        if request.achievement:
            context["achievement"] = request.achievement
        if request.closing_message:
            context["closing_message"] = request.closing_message

    # Send email in background
    background_tasks.add_task(
        send_templated_email_background,
        email_type=request.email_type,
        recipient_email=request.recipient_email,
        subject=request.subject,
        context=context,
    )

    return TemplatedEmailResponse(
        success=True,
        message=f"{request.email_type.value.capitalize()} email is being sent in the background",
        email_type=request.email_type.value,
        recipient=request.recipient_email,
    )


@router.post("/send/welcome")
async def send_welcome_notification(
    request: WelcomeEmailRequest,
    background_tasks: BackgroundTasks,
):
    """
    Send a welcome email to a new employee.

    Perfect for onboarding new team members with their account details.
    """
    logger.info(f"Sending welcome email to {request.recipient_email}")

    async def _send():
        await send_welcome_email(
            to_email=request.recipient_email,
            username=request.username,
            employee_id=request.employee_id,
            department=request.department,
            role=request.role,
            start_date=request.start_date,
            action_url=request.action_url,
            company_name=request.company_name,
        )

    background_tasks.add_task(_send)

    return {
        "success": True,
        "message": "Welcome email is being sent",
        "recipient": request.recipient_email,
    }


@router.post("/send/reminder")
async def send_reminder_notification(
    request: ReminderEmailRequest,
    background_tasks: BackgroundTasks,
):
    """
    Send a reminder email.

    Great for timesheet submissions, document reviews, deadline reminders, etc.
    """
    logger.info(f"Sending reminder email to {request.recipient_email}")

    async def _send():
        await send_reminder(
            to_email=request.recipient_email,
            username=request.username,
            subject=request.subject,
            reminder_title=request.reminder_title,
            reminder_message=request.reminder_message,
            due_date=request.due_date,
            urgency=request.urgency,
            details=request.details,
            action_url=request.action_url,
            action_text=request.action_text,
        )

    background_tasks.add_task(_send)

    return {
        "success": True,
        "message": "Reminder email is being sent",
        "recipient": request.recipient_email,
    }


@router.post("/send/notification")
async def send_general_notification(
    request: NotificationEmailRequest,
    background_tasks: BackgroundTasks,
):
    """
    Send a general notification email.

    Useful for leave approvals, system updates, announcements, etc.
    """
    logger.info(f"Sending notification email to {request.recipient_email}")

    async def _send():
        await send_notification(
            to_email=request.recipient_email,
            username=request.username,
            title=request.title,
            message=request.message,
            notification_title=request.notification_title,
            details=request.details,
            action_url=request.action_url,
            action_text=request.action_text,
        )

    background_tasks.add_task(_send)

    return {
        "success": True,
        "message": "Notification email is being sent",
        "recipient": request.recipient_email,
    }


@router.post("/send/congratulations")
async def send_congratulations_notification(
    request: CongratulationsEmailRequest,
    background_tasks: BackgroundTasks,
):
    """
    Send a congratulations email.

    Perfect for promotions, work anniversaries, achievements, and milestones.
    """
    logger.info(f"Sending congratulations email to {request.recipient_email}")

    async def _send():
        await send_congratulations(
            to_email=request.recipient_email,
            recipient_name=request.recipient_name,
            message=request.message,
            achievement=request.achievement,
            details=request.details,
            action_url=request.action_url,
            action_text=request.action_text,
            closing_message=request.closing_message,
        )

    background_tasks.add_task(_send)

    return {
        "success": True,
        "message": "Congratulations email is being sent",
        "recipient": request.recipient_email,
    }
