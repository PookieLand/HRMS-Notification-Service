"""
Internal API routes for programmatic notification triggering.

These endpoints are meant to be called by other services to trigger
notifications without going through Kafka. Useful for direct integrations
and testing.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from app.core.logging import get_logger
from app.services.email import (
    send_congratulations,
    send_notification,
    send_reminder,
    send_templated_email,
    send_welcome_email,
)
from app.services.template_service import EmailType

logger = get_logger(__name__)

router = APIRouter(
    prefix="/internal",
    tags=["internal"],
)


# ==========================================
# Request Models
# ==========================================


class OnboardingInvitationRequest(BaseModel):
    """Request model for sending onboarding invitation email."""

    recipient_email: EmailStr
    recipient_name: str
    role: str
    job_title: Optional[str] = None
    department: Optional[str] = None
    start_date: Optional[str] = None
    invitation_url: str
    company_name: Optional[str] = None


class WelcomeNotificationRequest(BaseModel):
    """Request model for sending welcome email after onboarding."""

    recipient_email: EmailStr
    recipient_name: str
    employee_id: Optional[str] = None
    role: str
    job_title: Optional[str] = None
    department: Optional[str] = None
    start_date: Optional[str] = None
    login_url: Optional[str] = None
    company_name: Optional[str] = None


class LeaveNotificationRequest(BaseModel):
    """Request model for leave notification emails."""

    recipient_email: EmailStr
    recipient_name: str
    status: str = Field(..., description="approved, rejected, or pending")
    leave_type: str
    start_date: str
    end_date: str
    days: int
    reason: Optional[str] = None
    rejection_reason: Optional[str] = None
    approved_by: Optional[str] = None
    rejected_by: Optional[str] = None
    action_url: Optional[str] = None


class CelebrationNotificationRequest(BaseModel):
    """Request model for celebration emails (birthday/anniversary)."""

    recipient_email: EmailStr
    recipient_name: str
    celebration_type: str = Field(..., description="birthday or anniversary")
    years_of_service: Optional[int] = None
    department: Optional[str] = None
    custom_message: Optional[str] = None


class HRAlertNotificationRequest(BaseModel):
    """Request model for HR alert notifications."""

    recipient_email: EmailStr
    recipient_name: str
    alert_type: str = Field(
        ...,
        description="probation_ending, contract_expiring, performance_review_due, salary_increment_due",
    )
    employee_name: str
    employee_email: str
    due_date: str
    days_remaining: int
    additional_info: Optional[Dict[str, str]] = None
    action_url: Optional[str] = None


class AttendanceAlertRequest(BaseModel):
    """Request model for attendance alert notifications."""

    recipient_email: EmailStr
    recipient_name: str
    alert_type: str = Field(..., description="late_arrival, absent, overtime")
    employee_name: str
    employee_email: str
    details: Dict[str, Any]


class GenericNotificationRequest(BaseModel):
    """Request model for generic notification emails."""

    recipient_email: EmailStr
    recipient_name: str
    subject: str
    title: str
    message: str
    details: Optional[Dict[str, str]] = None
    action_url: Optional[str] = None
    action_text: Optional[str] = None


class NotificationResponse(BaseModel):
    """Standard response model for notification endpoints."""

    success: bool
    message: str
    recipient: str


# ==========================================
# Internal Endpoints
# ==========================================


@router.post("/onboarding/invitation", response_model=NotificationResponse)
async def send_onboarding_invitation(
    request: OnboardingInvitationRequest,
    background_tasks: BackgroundTasks,
):
    """
    Send an onboarding invitation email to a new employee.

    Called by user-management-service when initiating onboarding.
    """
    logger.info(f"Sending onboarding invitation to {request.recipient_email}")

    async def _send():
        try:
            await send_reminder(
                to_email=request.recipient_email,
                username=request.recipient_name,
                subject="You're Invited to Join Our Team!",
                reminder_title="Complete Your Onboarding",
                reminder_message=(
                    f"Welcome to the team! You have been invited to join as {request.role}. "
                    f"Please click the button below to complete your account setup."
                ),
                due_date=None,
                urgency="medium",
                details={
                    "Position": request.job_title or request.role,
                    "Department": request.department or "Not Assigned",
                },
                action_url=request.invitation_url,
                action_text="Complete Onboarding",
            )
            logger.info(f"Onboarding invitation sent to {request.recipient_email}")
        except Exception as e:
            logger.error(f"Failed to send onboarding invitation: {e}")

    background_tasks.add_task(_send)

    return NotificationResponse(
        success=True,
        message="Onboarding invitation email is being sent",
        recipient=request.recipient_email,
    )


@router.post("/onboarding/welcome", response_model=NotificationResponse)
async def send_welcome_notification(
    request: WelcomeNotificationRequest,
    background_tasks: BackgroundTasks,
):
    """
    Send a welcome email after onboarding is complete.

    Called by user-management-service when onboarding completes.
    """
    logger.info(f"Sending welcome email to {request.recipient_email}")

    async def _send():
        try:
            await send_welcome_email(
                to_email=request.recipient_email,
                username=request.recipient_name,
                employee_id=request.employee_id,
                department=request.department,
                role=request.job_title or request.role,
                start_date=request.start_date,
                action_url=request.login_url,
                company_name=request.company_name,
            )
            logger.info(f"Welcome email sent to {request.recipient_email}")
        except Exception as e:
            logger.error(f"Failed to send welcome email: {e}")

    background_tasks.add_task(_send)

    return NotificationResponse(
        success=True,
        message="Welcome email is being sent",
        recipient=request.recipient_email,
    )


@router.post("/leave/notification", response_model=NotificationResponse)
async def send_leave_notification(
    request: LeaveNotificationRequest,
    background_tasks: BackgroundTasks,
):
    """
    Send a leave status notification email.

    Called by leave-management-service when leave status changes.
    """
    logger.info(
        f"Sending leave {request.status} notification to {request.recipient_email}"
    )

    async def _send():
        try:
            if request.status == "approved":
                title = "Leave Request Approved"
                message = (
                    f"Your {request.leave_type} leave request has been approved! "
                    f"Enjoy your time off."
                )
            elif request.status == "rejected":
                title = "Leave Request Not Approved"
                message = (
                    f"Unfortunately, your {request.leave_type} leave request was not approved. "
                    f"Please contact your manager if you have questions."
                )
            else:
                title = "Leave Request Submitted"
                message = (
                    f"Your {request.leave_type} leave request has been submitted "
                    f"and is pending approval."
                )

            details = {
                "Leave Type": request.leave_type,
                "Start Date": request.start_date,
                "End Date": request.end_date,
                "Days": str(request.days),
            }

            if request.status == "approved" and request.approved_by:
                details["Approved By"] = request.approved_by
            elif request.status == "rejected":
                if request.rejected_by:
                    details["Reviewed By"] = request.rejected_by
                if request.rejection_reason:
                    details["Reason"] = request.rejection_reason

            await send_notification(
                to_email=request.recipient_email,
                username=request.recipient_name,
                title=title,
                message=message,
                notification_title=title,
                details=details,
                action_url=request.action_url,
                action_text="View Details",
            )
            logger.info(f"Leave notification sent to {request.recipient_email}")
        except Exception as e:
            logger.error(f"Failed to send leave notification: {e}")

    background_tasks.add_task(_send)

    return NotificationResponse(
        success=True,
        message=f"Leave {request.status} notification is being sent",
        recipient=request.recipient_email,
    )


@router.post("/celebration", response_model=NotificationResponse)
async def send_celebration_notification(
    request: CelebrationNotificationRequest,
    background_tasks: BackgroundTasks,
):
    """
    Send a celebration email (birthday or work anniversary).

    Called by employee-management-service scheduler.
    """
    logger.info(
        f"Sending {request.celebration_type} celebration to {request.recipient_email}"
    )

    async def _send():
        try:
            if request.celebration_type == "birthday":
                message = (
                    request.custom_message
                    or "Wishing you a wonderful birthday filled with joy and happiness!"
                )
                achievement = "Happy Birthday!"
                closing = (
                    "May this year bring you great success, happiness, and prosperity!"
                )
            else:
                years = request.years_of_service or 1
                year_word = "year" if years == 1 else "years"
                message = (
                    request.custom_message
                    or f"Congratulations on your {years} {year_word} work anniversary! "
                    f"Thank you for being an invaluable part of our team."
                )
                achievement = f"{years} {year_word.title()} of Service"
                closing = (
                    "Your dedication and contributions have made a significant impact. "
                    "Here's to many more successful years together!"
                )

            details = {}
            if request.department:
                details["Department"] = request.department
            if request.years_of_service:
                details["Years of Service"] = str(request.years_of_service)

            await send_congratulations(
                to_email=request.recipient_email,
                recipient_name=request.recipient_name,
                message=message,
                achievement=achievement,
                details=details if details else None,
                closing_message=closing,
            )
            logger.info(f"Celebration email sent to {request.recipient_email}")
        except Exception as e:
            logger.error(f"Failed to send celebration email: {e}")

    background_tasks.add_task(_send)

    return NotificationResponse(
        success=True,
        message=f"{request.celebration_type.title()} celebration email is being sent",
        recipient=request.recipient_email,
    )


@router.post("/hr/alert", response_model=NotificationResponse)
async def send_hr_alert(
    request: HRAlertNotificationRequest,
    background_tasks: BackgroundTasks,
):
    """
    Send an HR alert notification (probation ending, contract expiring, etc.).

    Called by employee-management-service scheduler.
    """
    logger.info(f"Sending HR alert ({request.alert_type}) to {request.recipient_email}")

    async def _send():
        try:
            alert_titles = {
                "probation_ending": "Probation Review Required",
                "contract_expiring": "Contract Renewal Required",
                "performance_review_due": "Performance Review Due",
                "salary_increment_due": "Salary Increment Due",
            }

            alert_messages = {
                "probation_ending": (
                    f"The probation period for {request.employee_name} is ending in "
                    f"{request.days_remaining} days. Please complete the probation review."
                ),
                "contract_expiring": (
                    f"The contract for {request.employee_name} is expiring in "
                    f"{request.days_remaining} days. Please initiate the renewal process."
                ),
                "performance_review_due": (
                    f"The annual performance review for {request.employee_name} is due on "
                    f"{request.due_date}."
                ),
                "salary_increment_due": (
                    f"A salary increment for {request.employee_name} is due on "
                    f"{request.due_date}."
                ),
            }

            title = alert_titles.get(request.alert_type, "HR Alert")
            message = alert_messages.get(
                request.alert_type,
                f"Action required for {request.employee_name}.",
            )

            urgency = "high" if request.days_remaining <= 7 else "medium"

            details = {
                "Employee": request.employee_name,
                "Email": request.employee_email,
                "Due Date": request.due_date,
                "Days Remaining": str(request.days_remaining),
            }

            if request.additional_info:
                details.update(request.additional_info)

            await send_reminder(
                to_email=request.recipient_email,
                username=request.recipient_name,
                subject=f"HR Alert: {title}",
                reminder_title=title,
                reminder_message=message,
                due_date=request.due_date,
                urgency=urgency,
                details=details,
                action_url=request.action_url,
                action_text="Take Action",
            )
            logger.info(f"HR alert sent to {request.recipient_email}")
        except Exception as e:
            logger.error(f"Failed to send HR alert: {e}")

    background_tasks.add_task(_send)

    return NotificationResponse(
        success=True,
        message=f"HR alert ({request.alert_type}) is being sent",
        recipient=request.recipient_email,
    )


@router.post("/attendance/alert", response_model=NotificationResponse)
async def send_attendance_alert(
    request: AttendanceAlertRequest,
    background_tasks: BackgroundTasks,
):
    """
    Send an attendance alert notification.

    Called by attendance-management-service.
    """
    logger.info(
        f"Sending attendance alert ({request.alert_type}) to {request.recipient_email}"
    )

    async def _send():
        try:
            alert_configs = {
                "late_arrival": {
                    "title": "Late Arrival Notification",
                    "message": f"{request.employee_name} arrived late today.",
                },
                "absent": {
                    "title": "Employee Absence Alert",
                    "message": f"{request.employee_name} was absent.",
                },
                "overtime": {
                    "title": "Overtime Alert",
                    "message": f"{request.employee_name} worked overtime.",
                },
            }

            config = alert_configs.get(
                request.alert_type,
                {"title": "Attendance Alert", "message": "Attendance update."},
            )

            await send_notification(
                to_email=request.recipient_email,
                username=request.recipient_name,
                title=config["title"],
                message=config["message"],
                notification_title="Attendance Alert",
                details=request.details,
            )
            logger.info(f"Attendance alert sent to {request.recipient_email}")
        except Exception as e:
            logger.error(f"Failed to send attendance alert: {e}")

    background_tasks.add_task(_send)

    return NotificationResponse(
        success=True,
        message=f"Attendance alert ({request.alert_type}) is being sent",
        recipient=request.recipient_email,
    )


@router.post("/generic", response_model=NotificationResponse)
async def send_generic_notification(
    request: GenericNotificationRequest,
    background_tasks: BackgroundTasks,
):
    """
    Send a generic notification email.

    Can be used by any service for ad-hoc notifications.
    """
    logger.info(f"Sending generic notification to {request.recipient_email}")

    async def _send():
        try:
            await send_notification(
                to_email=request.recipient_email,
                username=request.recipient_name,
                title=request.title,
                message=request.message,
                notification_title=request.subject,
                details=request.details,
                action_url=request.action_url,
                action_text=request.action_text,
            )
            logger.info(f"Generic notification sent to {request.recipient_email}")
        except Exception as e:
            logger.error(f"Failed to send generic notification: {e}")

    background_tasks.add_task(_send)

    return NotificationResponse(
        success=True,
        message="Notification is being sent",
        recipient=request.recipient_email,
    )


@router.get("/health")
async def internal_health():
    """Health check for internal API."""
    return {"status": "ok", "service": "notification-internal-api"}
