from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel, EmailStr, Field

from app.api.dependencies import CurrentUserDep
from app.core.logging import get_logger
from app.services.email import (
    send_congratulations,
    send_email_message,
    send_notification,
    send_notification_email,
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


class BasicNotification(BaseModel):
    """Basic notification request model"""

    email_from: str = Field(..., description="Sender display name")
    recipient_email: EmailStr = Field(..., description="Recipient email address")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Email body content")


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


# ==============================================================================
# Enhanced Templated Email Endpoints
# ==============================================================================


class TemplatedEmailRequest(BaseModel):
    """
    Enhanced templated email request model.
    Supports multiple email types with dynamic content.
    """

    email_type: EmailType = Field(
        ...,
        description="Type of email template to use: welcome, notification, reminder, congratulations",
    )
    recipient_email: EmailStr = Field(..., description="Recipient email address")
    recipient_name: str = Field(..., description="Recipient's display name")
    subject: str = Field(..., description="Email subject line")

    # Common fields
    message: Optional[str] = Field(
        None, description="Main message content for the email"
    )
    details: Optional[Dict[str, str]] = Field(
        None, description="Key-value pairs to display in a details table"
    )
    action_url: Optional[str] = Field(None, description="URL for the action button")
    action_text: Optional[str] = Field(None, description="Text for the action button")

    # Welcome email specific
    employee_id: Optional[str] = Field(
        None, description="Employee ID (for welcome emails)"
    )
    department: Optional[str] = Field(
        None, description="Department name (for welcome emails)"
    )
    role: Optional[str] = Field(None, description="Job role/title (for welcome emails)")
    start_date: Optional[str] = Field(
        None, description="Start date (for welcome emails)"
    )

    # Reminder specific
    reminder_title: Optional[str] = Field(
        None, description="Reminder title (for reminder emails)"
    )
    reminder_message: Optional[str] = Field(
        None, description="Reminder message (for reminder emails)"
    )
    due_date: Optional[str] = Field(None, description="Due date (for reminder emails)")
    urgency: Optional[str] = Field(
        None, description="Urgency level: high, medium, low (for reminder emails)"
    )

    # Congratulations specific
    achievement: Optional[str] = Field(
        None, description="Achievement description (for congratulations emails)"
    )
    closing_message: Optional[str] = Field(
        None, description="Custom closing message (for congratulations emails)"
    )

    # General customization
    company_name: Optional[str] = Field(
        None, description="Company name override (default: HRMS Cloud Platform)"
    )
    sender_name: Optional[str] = Field(
        None, description="Sender name override (default: The HR Team)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email_type": "welcome",
                    "recipient_email": "john.doe@example.com",
                    "recipient_name": "John Doe",
                    "subject": "Welcome to HRMS Cloud Platform!",
                    "employee_id": "EMP001",
                    "department": "Engineering",
                    "role": "Software Engineer",
                    "start_date": "January 15, 2024",
                    "action_url": "https://hrms.example.com/login",
                    "action_text": "Get Started",
                },
                {
                    "email_type": "notification",
                    "recipient_email": "jane.smith@example.com",
                    "recipient_name": "Jane Smith",
                    "subject": "Leave Request Approved",
                    "message": "Your leave request has been approved by your manager.",
                    "details": {
                        "Leave Type": "Annual Leave",
                        "Start Date": "February 1, 2024",
                        "End Date": "February 5, 2024",
                        "Status": "Approved",
                    },
                    "action_url": "https://hrms.example.com/leaves",
                    "action_text": "View Details",
                },
                {
                    "email_type": "reminder",
                    "recipient_email": "bob.wilson@example.com",
                    "recipient_name": "Bob Wilson",
                    "subject": "Timesheet Submission Reminder",
                    "reminder_title": "Timesheet Due",
                    "reminder_message": "Please submit your timesheet for the current week.",
                    "due_date": "Friday, January 20, 2024",
                    "urgency": "high",
                    "action_url": "https://hrms.example.com/timesheets",
                    "action_text": "Submit Timesheet",
                },
                {
                    "email_type": "congratulations",
                    "recipient_email": "alice.johnson@example.com",
                    "recipient_name": "Alice Johnson",
                    "subject": "Congratulations on Your Promotion!",
                    "message": "We are delighted to inform you that you have been promoted!",
                    "achievement": "Promoted to Senior Software Engineer",
                    "details": {
                        "New Title": "Senior Software Engineer",
                        "Effective Date": "February 1, 2024",
                        "New Salary": "$120,000",
                    },
                    "closing_message": "Your hard work and dedication have been recognized. We look forward to your continued success!",
                },
            ]
        }
    }


class TemplatedEmailResponse(BaseModel):
    """Response model for templated email endpoint"""

    success: bool
    message: str
    email_type: str
    recipient: str


async def send_templated_email_background(
    email_type: EmailType,
    recipient_email: str,
    recipient_name: str,
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


@router.post("/templated/send", response_model=TemplatedEmailResponse)
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
        recipient_name=request.recipient_name,
        subject=request.subject,
        context=context,
    )

    return TemplatedEmailResponse(
        success=True,
        message=f"{request.email_type.value.capitalize()} email is being sent in the background",
        email_type=request.email_type.value,
        recipient=request.recipient_email,
    )


# ==============================================================================
# Convenience Endpoints for Specific Email Types
# ==============================================================================


class WelcomeEmailRequest(BaseModel):
    """Request model for welcome emails"""

    recipient_email: EmailStr
    username: str
    employee_id: Optional[str] = None
    department: Optional[str] = None
    role: Optional[str] = None
    start_date: Optional[str] = None
    action_url: Optional[str] = None
    company_name: Optional[str] = None


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


class ReminderEmailRequest(BaseModel):
    """Request model for reminder emails"""

    recipient_email: EmailStr
    username: str
    subject: str
    reminder_title: str
    reminder_message: str
    due_date: Optional[str] = None
    urgency: Optional[str] = Field(None, description="Urgency level: high, medium, low")
    details: Optional[Dict[str, str]] = None
    action_url: Optional[str] = None
    action_text: Optional[str] = None


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


class NotificationEmailRequest(BaseModel):
    """Request model for general notification emails"""

    recipient_email: EmailStr
    username: str
    title: str
    message: str
    notification_title: Optional[str] = None
    details: Optional[Dict[str, str]] = None
    action_url: Optional[str] = None
    action_text: Optional[str] = None


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


class CongratulationsEmailRequest(BaseModel):
    """Request model for congratulations emails"""

    recipient_email: EmailStr
    recipient_name: str
    message: str
    achievement: Optional[str] = None
    details: Optional[Dict[str, str]] = None
    action_url: Optional[str] = None
    action_text: Optional[str] = None
    closing_message: Optional[str] = None


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
