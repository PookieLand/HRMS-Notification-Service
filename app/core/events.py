"""
Event definitions for Notification Service.

Defines all event types and their data structures for Kafka consumption and publishing.
Events are categorized by source service and notification type.
"""

from datetime import date, datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, EmailStr, Field


class NotificationType(str, Enum):
    """Types of notifications the service can send."""

    # Onboarding
    INVITATION = "invitation"
    WELCOME = "welcome"
    PASSWORD_SET = "password_set"

    # Employee Lifecycle
    PROMOTION = "promotion"
    TERMINATION = "termination"
    TRANSFER = "transfer"
    PROBATION_COMPLETE = "probation_complete"
    CONTRACT_RENEWAL = "contract_renewal"
    SALARY_INCREMENT = "salary_increment"

    # Celebrations
    BIRTHDAY = "birthday"
    WORK_ANNIVERSARY = "work_anniversary"

    # HR Alerts
    HR_PROBATION_ENDING = "hr_probation_ending"
    HR_CONTRACT_EXPIRING = "hr_contract_expiring"
    HR_PERFORMANCE_REVIEW = "hr_performance_review"
    HR_SALARY_INCREMENT_DUE = "hr_salary_increment_due"
    HR_LEAVE_BALANCE_LOW = "hr_leave_balance_low"
    HR_EXCESSIVE_LEAVE = "hr_excessive_leave"

    # Leave
    LEAVE_REQUESTED = "leave_requested"
    LEAVE_APPROVED = "leave_approved"
    LEAVE_REJECTED = "leave_rejected"
    LEAVE_REMINDER = "leave_reminder"

    # Attendance
    LATE_ARRIVAL = "late_arrival"
    ABSENT = "absent"
    OVERTIME_ALERT = "overtime_alert"

    # General
    REMINDER = "reminder"
    NOTIFICATION = "notification"
    ANNOUNCEMENT = "announcement"


class EventMetadata(BaseModel):
    """Metadata attached to every event for tracing and correlation."""

    source_service: str = "notification-service"
    correlation_id: str = Field(default_factory=lambda: str(uuid4()))
    causation_id: Optional[str] = None
    actor_user_id: Optional[str] = None
    actor_role: Optional[str] = None
    trace_id: Optional[str] = None


class EventEnvelope(BaseModel):
    """
    Standard envelope for all events.
    Provides consistent structure for Kafka messages.
    """

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    version: str = "1.0"
    data: dict[str, Any]
    metadata: EventMetadata = Field(default_factory=EventMetadata)


# ==========================================
# Incoming Event Models (Consumed)
# ==========================================


class OnboardingInitiatedEvent(BaseModel):
    """Event received when onboarding is initiated."""

    onboarding_id: str
    email: EmailStr
    first_name: str
    last_name: str
    role: str
    job_title: Optional[str] = None
    department: Optional[str] = None
    invited_by_user_id: Optional[str] = None
    invited_by_email: Optional[str] = None
    invitation_url: Optional[str] = None


class OnboardingCompletedEvent(BaseModel):
    """Event received when onboarding is completed."""

    onboarding_id: str
    user_id: str
    employee_id: Optional[int] = None
    email: EmailStr
    first_name: str
    last_name: str
    role: str
    job_title: Optional[str] = None
    department: Optional[str] = None
    start_date: Optional[str] = None
    login_url: Optional[str] = None


class OnboardingFailedEvent(BaseModel):
    """Event received when onboarding fails."""

    onboarding_id: str
    email: EmailStr
    first_name: str
    last_name: str
    failure_reason: str
    failure_step: str


class EmployeeCreatedEvent(BaseModel):
    """Event received when an employee is created."""

    employee_id: int
    user_id: Optional[int] = None
    email: EmailStr
    first_name: str
    last_name: str
    role: str
    job_title: str
    department: Optional[str] = None
    manager_id: Optional[int] = None
    joining_date: Optional[date] = None


class EmployeePromotedEvent(BaseModel):
    """Event received when an employee is promoted."""

    employee_id: int
    user_id: Optional[int] = None
    email: EmailStr
    first_name: str
    last_name: str
    old_position: str
    new_position: str
    old_job_title: str
    new_job_title: str
    old_salary: Optional[float] = None
    new_salary: Optional[float] = None
    effective_date: date


class EmployeeTerminatedEvent(BaseModel):
    """Event received when an employee is terminated."""

    employee_id: int
    user_id: Optional[int] = None
    email: EmailStr
    first_name: str
    last_name: str
    termination_date: date
    reason: Optional[str] = None


class BirthdayEvent(BaseModel):
    """Event received for employee birthday."""

    employee_id: int
    user_id: Optional[int] = None
    email: EmailStr
    first_name: str
    last_name: str
    date_of_birth: date
    age: Optional[int] = None
    department: Optional[str] = None


class WorkAnniversaryEvent(BaseModel):
    """Event received for work anniversary."""

    employee_id: int
    user_id: Optional[int] = None
    email: EmailStr
    first_name: str
    last_name: str
    joining_date: date
    years_of_service: int
    department: Optional[str] = None


class ProbationEndingEvent(BaseModel):
    """Event received when probation is ending soon."""

    employee_id: int
    user_id: Optional[int] = None
    email: EmailStr
    first_name: str
    last_name: str
    probation_end_date: date
    days_remaining: int
    manager_id: Optional[int] = None
    manager_email: Optional[str] = None


class ContractExpiringEvent(BaseModel):
    """Event received when contract is expiring soon."""

    employee_id: int
    user_id: Optional[int] = None
    email: EmailStr
    first_name: str
    last_name: str
    contract_end_date: date
    days_remaining: int
    manager_id: Optional[int] = None
    manager_email: Optional[str] = None


class PerformanceReviewDueEvent(BaseModel):
    """Event received when performance review is due."""

    employee_id: int
    user_id: Optional[int] = None
    email: EmailStr
    first_name: str
    last_name: str
    review_due_date: date
    years_since_joining: int
    manager_id: Optional[int] = None
    manager_email: Optional[str] = None


class SalaryIncrementDueEvent(BaseModel):
    """Event received when salary increment is due."""

    employee_id: int
    user_id: Optional[int] = None
    email: EmailStr
    first_name: str
    last_name: str
    increment_due_date: date
    years_of_service: int
    current_salary: float
    salary_currency: str
    manager_id: Optional[int] = None


class SalaryIncrementEvent(BaseModel):
    """Event received when salary is incremented."""

    employee_id: int
    user_id: Optional[int] = None
    email: EmailStr
    first_name: str
    last_name: str
    old_salary: float
    new_salary: float
    increment_percentage: float
    salary_currency: str
    effective_date: date
    years_of_service: int


class LeaveRequestedEvent(BaseModel):
    """Event received when leave is requested."""

    leave_id: int
    employee_id: int
    employee_email: EmailStr
    employee_name: str
    manager_id: Optional[int] = None
    manager_email: Optional[str] = None
    leave_type: str
    start_date: date
    end_date: date
    days_requested: int
    reason: Optional[str] = None


class LeaveApprovedEvent(BaseModel):
    """Event received when leave is approved."""

    leave_id: int
    employee_id: int
    employee_email: EmailStr
    employee_name: str
    approved_by_id: int
    approved_by_email: Optional[str] = None
    approved_by_name: Optional[str] = None
    leave_type: str
    start_date: date
    end_date: date
    days_approved: int
    comments: Optional[str] = None


class LeaveRejectedEvent(BaseModel):
    """Event received when leave is rejected."""

    leave_id: int
    employee_id: int
    employee_email: EmailStr
    employee_name: str
    rejected_by_id: int
    rejected_by_email: Optional[str] = None
    rejected_by_name: Optional[str] = None
    leave_type: str
    start_date: date
    end_date: date
    days_requested: int
    rejection_reason: str


class LateArrivalEvent(BaseModel):
    """Event received for late arrival notification."""

    attendance_id: int
    employee_id: int
    employee_email: EmailStr
    employee_name: str
    check_in_time: datetime
    expected_time: datetime
    minutes_late: int
    manager_id: Optional[int] = None
    manager_email: Optional[str] = None


class AbsentEmployeeEvent(BaseModel):
    """Event received for absent employee notification."""

    employee_id: int
    employee_email: EmailStr
    employee_name: str
    absent_date: date
    manager_id: Optional[int] = None
    manager_email: Optional[str] = None
    consecutive_absences: int = 1


class OvertimeAlertEvent(BaseModel):
    """Event received for overtime alert."""

    attendance_id: int
    employee_id: int
    employee_email: EmailStr
    employee_name: str
    check_out_time: datetime
    overtime_hours: float
    manager_id: Optional[int] = None
    manager_email: Optional[str] = None


# ==========================================
# Outgoing Event Models (Published)
# ==========================================


class NotificationSentEvent(BaseModel):
    """Event published when notification is successfully sent."""

    notification_id: str = Field(default_factory=lambda: str(uuid4()))
    notification_type: NotificationType
    recipient_email: EmailStr
    recipient_name: str
    subject: str
    channel: str  # 'email', 'sms', 'push'
    sent_at: datetime = Field(default_factory=datetime.utcnow)
    related_event_id: Optional[str] = None
    related_event_type: Optional[str] = None


class NotificationFailedEvent(BaseModel):
    """Event published when notification fails to send."""

    notification_id: str = Field(default_factory=lambda: str(uuid4()))
    notification_type: NotificationType
    recipient_email: EmailStr
    recipient_name: str
    subject: str
    channel: str
    failed_at: datetime = Field(default_factory=datetime.utcnow)
    error_message: str
    retry_count: int = 0
    related_event_id: Optional[str] = None
    related_event_type: Optional[str] = None


class AuditNotificationEvent(BaseModel):
    """Event published for audit logging of notification actions."""

    action: str
    notification_type: NotificationType
    recipient_email: EmailStr
    recipient_name: str
    subject: str
    channel: str
    status: str  # 'sent', 'failed', 'queued'
    actor_user_id: Optional[str] = None
    actor_role: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Optional[dict[str, Any]] = None


# ==========================================
# Helper Functions
# ==========================================


def create_event(
    event_type: str,
    data: BaseModel,
    correlation_id: Optional[str] = None,
    causation_id: Optional[str] = None,
    actor_user_id: Optional[str] = None,
    actor_role: Optional[str] = None,
) -> EventEnvelope:
    """
    Helper function to create an event envelope with proper metadata.

    Args:
        event_type: Type/name of the event
        data: Event data as a Pydantic model
        correlation_id: Optional correlation ID for tracing
        causation_id: Optional ID of the event that caused this one
        actor_user_id: ID of the user performing the action
        actor_role: Role of the user performing the action

    Returns:
        EventEnvelope ready for publishing
    """
    metadata = EventMetadata(
        correlation_id=correlation_id or str(uuid4()),
        causation_id=causation_id,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
    )

    return EventEnvelope(
        event_type=event_type,
        data=data.model_dump(mode="json"),
        metadata=metadata,
    )


def parse_event(raw_data: dict[str, Any]) -> EventEnvelope:
    """
    Parse raw event data into an EventEnvelope.

    Args:
        raw_data: Raw dictionary from Kafka message

    Returns:
        Parsed EventEnvelope
    """
    return EventEnvelope(**raw_data)


def get_event_model_for_topic(topic: str) -> type[BaseModel] | None:
    """
    Get the appropriate event model class for a given topic.

    Args:
        topic: Kafka topic name

    Returns:
        Pydantic model class for the event, or None if unknown
    """
    topic_to_model = {
        "user-onboarding-initiated": OnboardingInitiatedEvent,
        "user-onboarding-completed": OnboardingCompletedEvent,
        "user-onboarding-failed": OnboardingFailedEvent,
        "employee-created": EmployeeCreatedEvent,
        "employee-promoted": EmployeePromotedEvent,
        "employee-terminated": EmployeeTerminatedEvent,
        "employee-special-birthday": BirthdayEvent,
        "employee-special-work-anniversary": WorkAnniversaryEvent,
        "hr-probation-ending": ProbationEndingEvent,
        "hr-contract-expiring": ContractExpiringEvent,
        "hr-performance-review-due": PerformanceReviewDueEvent,
        "hr-salary-increment-due": SalaryIncrementDueEvent,
        "employee-salary-increment": SalaryIncrementEvent,
        "leave-requested": LeaveRequestedEvent,
        "leave-approved": LeaveApprovedEvent,
        "leave-rejected": LeaveRejectedEvent,
        "notification-leave-pending": LeaveRequestedEvent,
        "notification-leave-approved": LeaveApprovedEvent,
        "notification-leave-rejected": LeaveRejectedEvent,
        "attendance-late": LateArrivalEvent,
        "attendance-absent": AbsentEmployeeEvent,
        "notification-late-arrival": LateArrivalEvent,
        "notification-absent-employee": AbsentEmployeeEvent,
        "notification-overtime-alert": OvertimeAlertEvent,
    }
    return topic_to_model.get(topic)
