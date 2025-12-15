"""
Kafka Event Consumers for Notification Service.

Handles events from multiple services and triggers appropriate notifications.
Each handler processes events from specific topics and sends notifications.
"""

import asyncio
from typing import Any

from app.core.cache import get_cache_service
from app.core.events import (
    AbsentEmployeeEvent,
    BirthdayEvent,
    ContractExpiringEvent,
    EmployeeCreatedEvent,
    EmployeePromotedEvent,
    EmployeeTerminatedEvent,
    EventEnvelope,
    LateArrivalEvent,
    LeaveApprovedEvent,
    LeaveRejectedEvent,
    LeaveRequestedEvent,
    NotificationSentEvent,
    NotificationType,
    OnboardingCompletedEvent,
    OnboardingFailedEvent,
    OnboardingInitiatedEvent,
    OnboardingInvitationSentEvent,
    OvertimeAlertEvent,
    PerformanceReviewDueEvent,
    ProbationEndingEvent,
    SalaryIncrementDueEvent,
    SalaryIncrementEvent,
    WorkAnniversaryEvent,
    create_event,
)
from app.core.kafka import get_consumer, get_producer
from app.core.logging import get_logger
from app.core.topics import KafkaTopics
from app.services.email import (
    send_congratulations,
    send_notification,
    send_reminder,
    send_welcome_email,
)
from app.services.template_service import EmailType

logger = get_logger(__name__)


def run_async(coro):
    """Run an async coroutine in a sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(coro)
        else:
            loop.run_until_complete(coro)
    except RuntimeError:
        asyncio.run(coro)


class NotificationEventHandlers:
    """
    Collection of event handlers for notification service.
    Each handler processes events from specific topics.
    """

    def __init__(self):
        self._cache = get_cache_service()

    def _check_duplicate(self, event_id: str) -> bool:
        """Check if event has already been processed."""
        return self._cache.is_duplicate_event(event_id)

    def _publish_notification_sent(
        self,
        notification_type: NotificationType,
        recipient_email: str,
        recipient_name: str,
        subject: str,
        related_event_id: str | None = None,
        related_event_type: str | None = None,
    ) -> None:
        """Publish notification sent event for audit trail."""
        try:
            event_data = NotificationSentEvent(
                notification_type=notification_type,
                recipient_email=recipient_email,
                recipient_name=recipient_name,
                subject=subject,
                channel="email",
                related_event_id=related_event_id,
                related_event_type=related_event_type,
            )
            event = create_event(
                event_type="notification.sent",
                data=event_data,
            )
            producer = get_producer()
            producer.publish_event(KafkaTopics.NOTIFICATION_SENT, event)
        except Exception as e:
            logger.error(f"Failed to publish notification sent event: {e}")

    # ==========================================
    # Onboarding Event Handlers
    # ==========================================

    async def handle_onboarding_initiated(self, event_data: dict[str, Any]) -> None:
        """Handle onboarding initiated event - send invitation email."""
        try:
            envelope = EventEnvelope(**event_data)
            data = OnboardingInitiatedEvent(**envelope.data)

            if self._check_duplicate(envelope.event_id):
                logger.debug(f"Duplicate event {envelope.event_id}, skipping")
                return

            logger.info(f"Sending invitation email to {data.email}")

            # Build invitation email context
            invitation_url = data.invitation_url or "https://hrms.example.com/signup"

            success = await send_reminder(
                to_email=data.email,
                username=f"{data.first_name} {data.last_name}",
                subject="You're Invited to Join Our Team!",
                reminder_title="Complete Your Onboarding",
                reminder_message=(
                    f"Welcome to the team! You have been invited to join as {data.role}. "
                    f"Please click the button below to complete your account setup and start your journey with us."
                ),
                due_date=None,
                urgency="medium",
                details={
                    "Position": data.job_title or data.role,
                    "Department": data.department or "Not Assigned",
                },
                action_url=invitation_url,
                action_text="Complete Onboarding",
            )

            if success:
                self._publish_notification_sent(
                    notification_type=NotificationType.INVITATION,
                    recipient_email=data.email,
                    recipient_name=f"{data.first_name} {data.last_name}",
                    subject="You're Invited to Join Our Team!",
                    related_event_id=envelope.event_id,
                    related_event_type=envelope.event_type,
                )

        except Exception as e:
            logger.error(f"Error handling onboarding initiated event: {e}")

    async def handle_invitation_email(self, event_data: dict[str, Any]) -> None:
        """Handle invitation email event - send invitation to new employee."""
        try:
            envelope = EventEnvelope(**event_data)
            data = OnboardingInvitationSentEvent(**envelope.data)

            if self._check_duplicate(envelope.event_id):
                logger.debug(f"Duplicate event {envelope.event_id}, skipping")
                return

            logger.info(f"Sending invitation email to {data.email}")

            success = await send_reminder(
                to_email=data.email,
                username=data.email,  # We don't have first/last name yet
                subject="You're Invited to Join Our Team!",
                reminder_title="Complete Your Onboarding",
                reminder_message=(
                    f"Welcome! You have been invited to join our team as {data.role}. "
                    f"Please click the button below to complete your account setup and start your journey with us."
                ),
                due_date=data.expires_at.strftime("%Y-%m-%d")
                if data.expires_at
                else None,
                urgency="medium",
                details={
                    "Position": data.job_title,
                    "Role": data.role,
                },
                action_url=data.invitation_link,
                action_text="Complete Onboarding",
            )

            if success:
                self._publish_notification_sent(
                    notification_type=NotificationType.INVITATION,
                    recipient_email=data.email,
                    recipient_name=data.email,
                    subject="You're Invited to Join Our Team!",
                    related_event_id=envelope.event_id,
                    related_event_type=envelope.event_type,
                )

        except Exception as e:
            logger.error(f"Error handling invitation email event: {e}")

    async def handle_onboarding_completed(self, event_data: dict[str, Any]) -> None:
        """Handle onboarding completed event - send welcome email."""
        try:
            envelope = EventEnvelope(**event_data)
            data = OnboardingCompletedEvent(**envelope.data)

            if self._check_duplicate(envelope.event_id):
                logger.debug(f"Duplicate event {envelope.event_id}, skipping")
                return

            logger.info(f"Sending welcome email to {data.email}")

            login_url = data.login_url or "https://hrms.example.com/login"

            success = await send_welcome_email(
                to_email=data.email,
                username=f"{data.first_name} {data.last_name}",
                employee_id=str(data.employee_id) if data.employee_id else None,
                department=data.department,
                role=data.job_title or data.role,
                start_date=data.start_date,
                action_url=login_url,
                company_name="HRMS Cloud Platform",
            )

            if success:
                self._publish_notification_sent(
                    notification_type=NotificationType.WELCOME,
                    recipient_email=data.email,
                    recipient_name=f"{data.first_name} {data.last_name}",
                    subject="Welcome to the Team!",
                    related_event_id=envelope.event_id,
                    related_event_type=envelope.event_type,
                )

        except Exception as e:
            logger.error(f"Error handling onboarding completed event: {e}")

    async def handle_onboarding_failed(self, event_data: dict[str, Any]) -> None:
        """Handle onboarding failed event - notify relevant parties."""
        try:
            envelope = EventEnvelope(**event_data)
            data = OnboardingFailedEvent(**envelope.data)

            if self._check_duplicate(envelope.event_id):
                return

            logger.info(f"Sending onboarding failed notification for {data.email}")

            await send_notification(
                to_email=data.email,
                username=f"{data.first_name} {data.last_name}",
                title="Onboarding Issue",
                message=(
                    f"There was an issue with your onboarding process at step: {data.failure_step}. "
                    f"Our HR team has been notified and will contact you shortly."
                ),
                notification_title="Onboarding Status Update",
                details={
                    "Issue": data.failure_reason,
                    "Step": data.failure_step,
                },
                action_url="https://hrms.example.com/support",
                action_text="Contact Support",
            )

        except Exception as e:
            logger.error(f"Error handling onboarding failed event: {e}")

    # ==========================================
    # Employee Lifecycle Event Handlers
    # ==========================================

    async def handle_employee_created(self, event_data: dict[str, Any]) -> None:
        """Handle employee created event."""
        try:
            envelope = EventEnvelope(**event_data)
            data = EmployeeCreatedEvent(**envelope.data)

            if self._check_duplicate(envelope.event_id):
                return

            logger.info(f"Processing employee created event for {data.email}")

            # This is typically handled by onboarding completed,
            # but we can send a confirmation if needed
            await send_notification(
                to_email=data.email,
                username=f"{data.first_name} {data.last_name}",
                title="Employee Profile Created",
                message=(
                    f"Your employee profile has been successfully created. "
                    f"Welcome to {data.department or 'the team'}!"
                ),
                details={
                    "Employee ID": str(data.employee_id),
                    "Role": data.role,
                    "Job Title": data.job_title,
                    "Department": data.department or "Not Assigned",
                },
            )

        except Exception as e:
            logger.error(f"Error handling employee created event: {e}")

    async def handle_employee_promoted(self, event_data: dict[str, Any]) -> None:
        """Handle employee promoted event - send congratulations."""
        try:
            envelope = EventEnvelope(**event_data)
            data = EmployeePromotedEvent(**envelope.data)

            if self._check_duplicate(envelope.event_id):
                return

            logger.info(f"Sending promotion congratulations to {data.email}")

            await send_congratulations(
                to_email=data.email,
                recipient_name=f"{data.first_name} {data.last_name}",
                message=(
                    f"Congratulations on your well-deserved promotion! "
                    f"Your hard work and dedication have been recognized."
                ),
                achievement=f"Promoted to {data.new_job_title}",
                details={
                    "Previous Position": data.old_job_title,
                    "New Position": data.new_job_title,
                    "Effective Date": str(data.effective_date),
                },
                closing_message=(
                    "We're excited to see you take on new challenges and "
                    "continue to excel in your career. Best wishes for continued success!"
                ),
            )

            self._publish_notification_sent(
                notification_type=NotificationType.PROMOTION,
                recipient_email=data.email,
                recipient_name=f"{data.first_name} {data.last_name}",
                subject="Congratulations on Your Promotion!",
                related_event_id=envelope.event_id,
                related_event_type=envelope.event_type,
            )

        except Exception as e:
            logger.error(f"Error handling employee promoted event: {e}")

    async def handle_employee_terminated(self, event_data: dict[str, Any]) -> None:
        """Handle employee terminated event."""
        try:
            envelope = EventEnvelope(**event_data)
            data = EmployeeTerminatedEvent(**envelope.data)

            if self._check_duplicate(envelope.event_id):
                return

            logger.info(f"Sending termination notification to {data.email}")

            await send_notification(
                to_email=data.email,
                username=f"{data.first_name} {data.last_name}",
                title="Employment Status Update",
                message=(
                    f"Your employment has been terminated effective {data.termination_date}. "
                    f"Please contact HR for any questions about your final pay or benefits."
                ),
                details={
                    "Termination Date": str(data.termination_date),
                    "Reason": data.reason or "Not specified",
                },
                action_url="https://hrms.example.com/hr-contact",
                action_text="Contact HR",
            )

        except Exception as e:
            logger.error(f"Error handling employee terminated event: {e}")

    async def handle_salary_increment(self, event_data: dict[str, Any]) -> None:
        """Handle salary increment event - send congratulations."""
        try:
            envelope = EventEnvelope(**event_data)
            data = SalaryIncrementEvent(**envelope.data)

            if self._check_duplicate(envelope.event_id):
                return

            logger.info(f"Sending salary increment notification to {data.email}")

            await send_congratulations(
                to_email=data.email,
                recipient_name=f"{data.first_name} {data.last_name}",
                message=(
                    f"We're pleased to inform you of your salary increment! "
                    f"This reflects your valuable contributions to the organization."
                ),
                achievement=f"{data.increment_percentage:.1f}% Salary Increment",
                details={
                    "New Salary": f"{data.salary_currency} {data.new_salary:,.2f}",
                    "Effective Date": str(data.effective_date),
                    "Years of Service": str(data.years_of_service),
                },
                closing_message="Thank you for your continued dedication and hard work!",
            )

            self._publish_notification_sent(
                notification_type=NotificationType.SALARY_INCREMENT,
                recipient_email=data.email,
                recipient_name=f"{data.first_name} {data.last_name}",
                subject="Congratulations on Your Salary Increment!",
                related_event_id=envelope.event_id,
                related_event_type=envelope.event_type,
            )

        except Exception as e:
            logger.error(f"Error handling salary increment event: {e}")

    # ==========================================
    # Special Event Handlers (Celebrations)
    # ==========================================

    async def handle_birthday(self, event_data: dict[str, Any]) -> None:
        """Handle birthday event - send birthday wishes."""
        try:
            envelope = EventEnvelope(**event_data)
            data = BirthdayEvent(**envelope.data)

            if self._check_duplicate(envelope.event_id):
                return

            logger.info(f"Sending birthday wishes to {data.email}")

            await send_congratulations(
                to_email=data.email,
                recipient_name=f"{data.first_name} {data.last_name}",
                message="Wishing you a wonderful birthday filled with joy and happiness!",
                achievement="Happy Birthday!",
                details={
                    "Department": data.department or "Our Team",
                },
                closing_message=(
                    "May this year bring you great success, happiness, and prosperity. "
                    "Enjoy your special day!"
                ),
            )

            self._publish_notification_sent(
                notification_type=NotificationType.BIRTHDAY,
                recipient_email=data.email,
                recipient_name=f"{data.first_name} {data.last_name}",
                subject="Happy Birthday!",
                related_event_id=envelope.event_id,
                related_event_type=envelope.event_type,
            )

        except Exception as e:
            logger.error(f"Error handling birthday event: {e}")

    async def handle_work_anniversary(self, event_data: dict[str, Any]) -> None:
        """Handle work anniversary event - send anniversary wishes."""
        try:
            envelope = EventEnvelope(**event_data)
            data = WorkAnniversaryEvent(**envelope.data)

            if self._check_duplicate(envelope.event_id):
                return

            logger.info(f"Sending work anniversary wishes to {data.email}")

            year_word = "year" if data.years_of_service == 1 else "years"

            await send_congratulations(
                to_email=data.email,
                recipient_name=f"{data.first_name} {data.last_name}",
                message=(
                    f"Congratulations on your {data.years_of_service} {year_word} work anniversary! "
                    f"Thank you for being an invaluable part of our team."
                ),
                achievement=f"{data.years_of_service} {year_word.title()} of Service",
                details={
                    "Joined": str(data.joining_date),
                    "Department": data.department or "Our Team",
                    "Years of Service": str(data.years_of_service),
                },
                closing_message=(
                    "Your dedication and contributions have made a significant impact. "
                    "Here's to many more successful years together!"
                ),
            )

            self._publish_notification_sent(
                notification_type=NotificationType.WORK_ANNIVERSARY,
                recipient_email=data.email,
                recipient_name=f"{data.first_name} {data.last_name}",
                subject=f"Happy {data.years_of_service} Year Work Anniversary!",
                related_event_id=envelope.event_id,
                related_event_type=envelope.event_type,
            )

        except Exception as e:
            logger.error(f"Error handling work anniversary event: {e}")

    # ==========================================
    # HR Event Handlers
    # ==========================================

    async def handle_probation_ending(self, event_data: dict[str, Any]) -> None:
        """Handle probation ending event - notify manager and HR."""
        try:
            envelope = EventEnvelope(**event_data)
            data = ProbationEndingEvent(**envelope.data)

            if self._check_duplicate(envelope.event_id):
                return

            # Notify manager if email is available
            if data.manager_email:
                logger.info(
                    f"Sending probation ending reminder to manager {data.manager_email}"
                )

                await send_reminder(
                    to_email=data.manager_email,
                    username="Manager",
                    subject=f"Probation Ending: {data.first_name} {data.last_name}",
                    reminder_title="Employee Probation Review Required",
                    reminder_message=(
                        f"The probation period for {data.first_name} {data.last_name} "
                        f"is ending in {data.days_remaining} days. "
                        f"Please complete the probation review before the end date."
                    ),
                    due_date=str(data.probation_end_date),
                    urgency="high" if data.days_remaining <= 7 else "medium",
                    details={
                        "Employee": f"{data.first_name} {data.last_name}",
                        "Email": data.email,
                        "Probation End Date": str(data.probation_end_date),
                        "Days Remaining": str(data.days_remaining),
                    },
                    action_url="https://hrms.example.com/reviews",
                    action_text="Complete Review",
                )

            # Also notify the employee
            await send_notification(
                to_email=data.email,
                username=f"{data.first_name} {data.last_name}",
                title="Probation Period Update",
                message=(
                    f"Your probation period is ending on {data.probation_end_date}. "
                    f"Your manager will be conducting a review soon."
                ),
                details={
                    "Probation End Date": str(data.probation_end_date),
                    "Days Remaining": str(data.days_remaining),
                },
            )

        except Exception as e:
            logger.error(f"Error handling probation ending event: {e}")

    async def handle_contract_expiring(self, event_data: dict[str, Any]) -> None:
        """Handle contract expiring event - notify relevant parties."""
        try:
            envelope = EventEnvelope(**event_data)
            data = ContractExpiringEvent(**envelope.data)

            if self._check_duplicate(envelope.event_id):
                return

            # Notify manager
            if data.manager_email:
                await send_reminder(
                    to_email=data.manager_email,
                    username="Manager",
                    subject=f"Contract Expiring: {data.first_name} {data.last_name}",
                    reminder_title="Employee Contract Renewal Required",
                    reminder_message=(
                        f"The contract for {data.first_name} {data.last_name} "
                        f"is expiring in {data.days_remaining} days. "
                        f"Please initiate the renewal process if applicable."
                    ),
                    due_date=str(data.contract_end_date),
                    urgency="high" if data.days_remaining <= 14 else "medium",
                    details={
                        "Employee": f"{data.first_name} {data.last_name}",
                        "Email": data.email,
                        "Contract End Date": str(data.contract_end_date),
                        "Days Remaining": str(data.days_remaining),
                    },
                    action_url="https://hrms.example.com/contracts",
                    action_text="Manage Contract",
                )

            # Notify the employee
            await send_notification(
                to_email=data.email,
                username=f"{data.first_name} {data.last_name}",
                title="Contract Expiration Notice",
                message=(
                    f"Your contract is expiring on {data.contract_end_date}. "
                    f"Please contact HR for information about renewal."
                ),
                details={
                    "Contract End Date": str(data.contract_end_date),
                    "Days Remaining": str(data.days_remaining),
                },
                action_url="https://hrms.example.com/hr-contact",
                action_text="Contact HR",
            )

        except Exception as e:
            logger.error(f"Error handling contract expiring event: {e}")

    async def handle_performance_review_due(self, event_data: dict[str, Any]) -> None:
        """Handle performance review due event."""
        try:
            envelope = EventEnvelope(**event_data)
            data = PerformanceReviewDueEvent(**envelope.data)

            if self._check_duplicate(envelope.event_id):
                return

            # Notify manager
            if data.manager_email:
                await send_reminder(
                    to_email=data.manager_email,
                    username="Manager",
                    subject=f"Performance Review Due: {data.first_name} {data.last_name}",
                    reminder_title="Annual Performance Review",
                    reminder_message=(
                        f"The annual performance review for {data.first_name} {data.last_name} "
                        f"is due on {data.review_due_date}. This marks their "
                        f"{data.years_since_joining} year anniversary with the company."
                    ),
                    due_date=str(data.review_due_date),
                    urgency="medium",
                    details={
                        "Employee": f"{data.first_name} {data.last_name}",
                        "Years with Company": str(data.years_since_joining),
                        "Review Due Date": str(data.review_due_date),
                    },
                    action_url="https://hrms.example.com/reviews",
                    action_text="Start Review",
                )

        except Exception as e:
            logger.error(f"Error handling performance review due event: {e}")

    async def handle_salary_increment_due(self, event_data: dict[str, Any]) -> None:
        """Handle salary increment due event - notify HR."""
        try:
            envelope = EventEnvelope(**event_data)
            data = SalaryIncrementDueEvent(**envelope.data)

            if self._check_duplicate(envelope.event_id):
                return

            logger.info(
                f"Processing salary increment due notification for {data.email}"
            )

            # This goes to HR typically, but we'll log it for now
            # In production, this would go to an HR distribution list
            logger.info(
                f"Salary increment due for {data.first_name} {data.last_name} "
                f"({data.years_of_service} years) on {data.increment_due_date}"
            )

        except Exception as e:
            logger.error(f"Error handling salary increment due event: {e}")

    # ==========================================
    # Leave Event Handlers
    # ==========================================

    async def handle_leave_requested(self, event_data: dict[str, Any]) -> None:
        """Handle leave requested event - notify manager."""
        try:
            envelope = EventEnvelope(**event_data)
            data = LeaveRequestedEvent(**envelope.data)

            if self._check_duplicate(envelope.event_id):
                return

            # Notify manager of pending leave request
            if data.manager_email:
                logger.info(
                    f"Sending leave request notification to manager {data.manager_email}"
                )

                await send_notification(
                    to_email=data.manager_email,
                    username="Manager",
                    title="Leave Request Pending Approval",
                    message=(
                        f"{data.employee_name} has requested {data.days_requested} days "
                        f"of {data.leave_type} leave. Please review and respond."
                    ),
                    notification_title="New Leave Request",
                    details={
                        "Employee": data.employee_name,
                        "Leave Type": data.leave_type,
                        "Start Date": str(data.start_date),
                        "End Date": str(data.end_date),
                        "Days Requested": str(data.days_requested),
                        "Reason": data.reason or "Not specified",
                    },
                    action_url="https://hrms.example.com/leave-requests",
                    action_text="Review Request",
                )

        except Exception as e:
            logger.error(f"Error handling leave requested event: {e}")

    async def handle_leave_approved(self, event_data: dict[str, Any]) -> None:
        """Handle leave approved event - notify employee."""
        try:
            envelope = EventEnvelope(**event_data)
            data = LeaveApprovedEvent(**envelope.data)

            if self._check_duplicate(envelope.event_id):
                return

            logger.info(f"Sending leave approved notification to {data.employee_email}")

            await send_notification(
                to_email=data.employee_email,
                username=data.employee_name,
                title="Leave Request Approved",
                message=(
                    f"Your {data.leave_type} leave request has been approved! "
                    f"Enjoy your time off."
                ),
                notification_title="Leave Approved",
                details={
                    "Leave Type": data.leave_type,
                    "Start Date": str(data.start_date),
                    "End Date": str(data.end_date),
                    "Days Approved": str(data.days_approved),
                    "Approved By": data.approved_by_name or "Your Manager",
                    "Comments": data.comments or "None",
                },
                action_url="https://hrms.example.com/my-leaves",
                action_text="View Leave Details",
            )

            self._publish_notification_sent(
                notification_type=NotificationType.LEAVE_APPROVED,
                recipient_email=data.employee_email,
                recipient_name=data.employee_name,
                subject="Leave Request Approved",
                related_event_id=envelope.event_id,
                related_event_type=envelope.event_type,
            )

        except Exception as e:
            logger.error(f"Error handling leave approved event: {e}")

    async def handle_leave_rejected(self, event_data: dict[str, Any]) -> None:
        """Handle leave rejected event - notify employee."""
        try:
            envelope = EventEnvelope(**event_data)
            data = LeaveRejectedEvent(**envelope.data)

            if self._check_duplicate(envelope.event_id):
                return

            logger.info(f"Sending leave rejected notification to {data.employee_email}")

            await send_notification(
                to_email=data.employee_email,
                username=data.employee_name,
                title="Leave Request Not Approved",
                message=(
                    f"Unfortunately, your {data.leave_type} leave request was not approved. "
                    f"Please contact your manager if you have questions."
                ),
                notification_title="Leave Request Update",
                details={
                    "Leave Type": data.leave_type,
                    "Start Date": str(data.start_date),
                    "End Date": str(data.end_date),
                    "Days Requested": str(data.days_requested),
                    "Reason for Rejection": data.rejection_reason,
                    "Rejected By": data.rejected_by_name or "Your Manager",
                },
                action_url="https://hrms.example.com/my-leaves",
                action_text="View Details",
            )

            self._publish_notification_sent(
                notification_type=NotificationType.LEAVE_REJECTED,
                recipient_email=data.employee_email,
                recipient_name=data.employee_name,
                subject="Leave Request Not Approved",
                related_event_id=envelope.event_id,
                related_event_type=envelope.event_type,
            )

        except Exception as e:
            logger.error(f"Error handling leave rejected event: {e}")

    # ==========================================
    # Attendance Event Handlers
    # ==========================================

    async def handle_late_arrival(self, event_data: dict[str, Any]) -> None:
        """Handle late arrival event - notify manager."""
        try:
            envelope = EventEnvelope(**event_data)
            data = LateArrivalEvent(**envelope.data)

            if self._check_duplicate(envelope.event_id):
                return

            # Notify manager of late arrival
            if data.manager_email:
                logger.info(
                    f"Sending late arrival notification to manager {data.manager_email}"
                )

                await send_notification(
                    to_email=data.manager_email,
                    username="Manager",
                    title="Late Arrival Notification",
                    message=(
                        f"{data.employee_name} arrived {data.minutes_late} minutes late today."
                    ),
                    notification_title="Attendance Alert",
                    details={
                        "Employee": data.employee_name,
                        "Check-in Time": str(data.check_in_time),
                        "Expected Time": str(data.expected_time),
                        "Minutes Late": str(data.minutes_late),
                    },
                )

        except Exception as e:
            logger.error(f"Error handling late arrival event: {e}")

    async def handle_absent_employee(self, event_data: dict[str, Any]) -> None:
        """Handle absent employee event - notify manager."""
        try:
            envelope = EventEnvelope(**event_data)
            data = AbsentEmployeeEvent(**envelope.data)

            if self._check_duplicate(envelope.event_id):
                return

            # Notify manager of absence
            if data.manager_email:
                urgency = "high" if data.consecutive_absences > 2 else "medium"

                await send_notification(
                    to_email=data.manager_email,
                    username="Manager",
                    title="Employee Absence Alert",
                    message=(
                        f"{data.employee_name} was absent on {data.absent_date}. "
                        f"This is consecutive absence #{data.consecutive_absences}."
                    ),
                    notification_title="Absence Notification",
                    details={
                        "Employee": data.employee_name,
                        "Email": data.employee_email,
                        "Absent Date": str(data.absent_date),
                        "Consecutive Absences": str(data.consecutive_absences),
                    },
                )

        except Exception as e:
            logger.error(f"Error handling absent employee event: {e}")

    async def handle_overtime_alert(self, event_data: dict[str, Any]) -> None:
        """Handle overtime alert event."""
        try:
            envelope = EventEnvelope(**event_data)
            data = OvertimeAlertEvent(**envelope.data)

            if self._check_duplicate(envelope.event_id):
                return

            # Notify manager of overtime
            if data.manager_email:
                await send_notification(
                    to_email=data.manager_email,
                    username="Manager",
                    title="Overtime Alert",
                    message=(
                        f"{data.employee_name} worked {data.overtime_hours:.1f} hours "
                        f"of overtime today."
                    ),
                    notification_title="Overtime Notification",
                    details={
                        "Employee": data.employee_name,
                        "Check-out Time": str(data.check_out_time),
                        "Overtime Hours": f"{data.overtime_hours:.1f}",
                    },
                )

        except Exception as e:
            logger.error(f"Error handling overtime alert event: {e}")


# Topic to handler mapping
def get_topic_handlers() -> dict[str, callable]:
    """Get mapping of topics to their handlers."""
    handlers = NotificationEventHandlers()

    def wrap_async_handler(handler):
        """Wrap async handler for sync consumption."""

        def wrapper(event_data: dict[str, Any], topic: str):
            logger.info(f"Processing event from topic: {topic}")
            run_async(handler(event_data))

        return wrapper

    return {
        # Onboarding topics - direct notification triggers
        KafkaTopics.NOTIFICATION_INVITATION_EMAIL: wrap_async_handler(
            handlers.handle_invitation_email
        ),
        KafkaTopics.NOTIFICATION_WELCOME_EMAIL: wrap_async_handler(
            handlers.handle_onboarding_completed
        ),
        KafkaTopics.USER_ONBOARDING_COMPLETED: wrap_async_handler(
            handlers.handle_onboarding_completed
        ),
        KafkaTopics.USER_ONBOARDING_FAILED: wrap_async_handler(
            handlers.handle_onboarding_failed
        ),
        # Employee lifecycle topics
        KafkaTopics.EMPLOYEE_CREATED: wrap_async_handler(
            handlers.handle_employee_created
        ),
        KafkaTopics.EMPLOYEE_PROMOTED: wrap_async_handler(
            handlers.handle_employee_promoted
        ),
        KafkaTopics.EMPLOYEE_TERMINATED: wrap_async_handler(
            handlers.handle_employee_terminated
        ),
        KafkaTopics.EMPLOYEE_SALARY_INCREMENT: wrap_async_handler(
            handlers.handle_salary_increment
        ),
        # Special events (celebrations)
        KafkaTopics.EMPLOYEE_BIRTHDAY: wrap_async_handler(handlers.handle_birthday),
        KafkaTopics.EMPLOYEE_WORK_ANNIVERSARY: wrap_async_handler(
            handlers.handle_work_anniversary
        ),
        # HR events
        KafkaTopics.HR_PROBATION_ENDING: wrap_async_handler(
            handlers.handle_probation_ending
        ),
        KafkaTopics.HR_CONTRACT_EXPIRING: wrap_async_handler(
            handlers.handle_contract_expiring
        ),
        KafkaTopics.HR_PERFORMANCE_REVIEW_DUE: wrap_async_handler(
            handlers.handle_performance_review_due
        ),
        KafkaTopics.HR_SALARY_INCREMENT_DUE: wrap_async_handler(
            handlers.handle_salary_increment_due
        ),
        # Leave topics
        KafkaTopics.LEAVE_REQUESTED: wrap_async_handler(
            handlers.handle_leave_requested
        ),
        KafkaTopics.LEAVE_APPROVED: wrap_async_handler(handlers.handle_leave_approved),
        KafkaTopics.LEAVE_REJECTED: wrap_async_handler(handlers.handle_leave_rejected),
        KafkaTopics.NOTIFICATION_LEAVE_PENDING: wrap_async_handler(
            handlers.handle_leave_requested
        ),
        KafkaTopics.NOTIFICATION_LEAVE_APPROVED: wrap_async_handler(
            handlers.handle_leave_approved
        ),
        KafkaTopics.NOTIFICATION_LEAVE_REJECTED: wrap_async_handler(
            handlers.handle_leave_rejected
        ),
        # Attendance topics
        KafkaTopics.ATTENDANCE_LATE: wrap_async_handler(handlers.handle_late_arrival),
        KafkaTopics.ATTENDANCE_ABSENT: wrap_async_handler(
            handlers.handle_absent_employee
        ),
        KafkaTopics.NOTIFICATION_LATE_ARRIVAL: wrap_async_handler(
            handlers.handle_late_arrival
        ),
        KafkaTopics.NOTIFICATION_ABSENT_EMPLOYEE: wrap_async_handler(
            handlers.handle_absent_employee
        ),
        KafkaTopics.NOTIFICATION_OVERTIME_ALERT: wrap_async_handler(
            handlers.handle_overtime_alert
        ),
    }


def register_all_handlers(consumer) -> None:
    """Register all handlers with the consumer."""
    topic_handlers = get_topic_handlers()
    for topic, handler in topic_handlers.items():
        consumer.register_handler(topic, handler)
    logger.info(f"Registered {len(topic_handlers)} event handlers")


def start_consumer() -> None:
    """Initialize and start the Kafka consumer with all handlers."""
    from app.core.topics import KafkaTopics

    consumer = get_consumer(topics=KafkaTopics.all_subscribed_topics())
    register_all_handlers(consumer)
    consumer.start()
    logger.info("Notification service Kafka consumer started")


def stop_consumer() -> None:
    """Stop the Kafka consumer."""
    consumer = get_consumer()
    consumer.stop()
    logger.info("Notification service Kafka consumer stopped")
