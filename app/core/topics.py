"""
Kafka Topic Definitions for Notification Service.

This service subscribes to topics from multiple services to send notifications.
Topic naming follows the pattern: <domain>-<event-type>
"""


class KafkaTopics:
    """
    Central registry of all Kafka topics consumed by the Notification Service.
    Topics are organized by source service for clarity.
    """

    # ==========================================
    # User Management Service Topics
    # ==========================================

    # Onboarding Events - Trigger invitation and welcome emails
    USER_ONBOARDING_INITIATED = "user-onboarding-initiated"
    USER_ONBOARDING_ASGARDEO_CREATED = "user-onboarding-asgardeo-created"
    USER_ONBOARDING_EMPLOYEE_CREATED = "user-onboarding-employee-created"
    USER_ONBOARDING_COMPLETED = "user-onboarding-completed"
    USER_ONBOARDING_FAILED = "user-onboarding-failed"

    # User Lifecycle Events
    USER_CREATED = "user-created"
    USER_SUSPENDED = "user-suspended"
    USER_ACTIVATED = "user-activated"

    # Direct Notification Triggers from User Service
    NOTIFICATION_WELCOME_EMAIL = "notification-welcome-email"
    NOTIFICATION_INVITATION_EMAIL = "notification-invitation-email"
    NOTIFICATION_PASSWORD_SET = "notification-password-set"

    # ==========================================
    # Employee Management Service Topics
    # ==========================================

    # Employee Lifecycle Events
    EMPLOYEE_CREATED = "employee-created"
    EMPLOYEE_PROMOTED = "employee-promoted"
    EMPLOYEE_TERMINATED = "employee-terminated"
    EMPLOYEE_TRANSFERRED = "employee-transferred"

    # Employment Status Events
    EMPLOYEE_PROBATION_STARTED = "employee-probation-started"
    EMPLOYEE_PROBATION_COMPLETED = "employee-probation-completed"
    EMPLOYEE_CONTRACT_STARTED = "employee-contract-started"
    EMPLOYEE_CONTRACT_RENEWED = "employee-contract-renewed"
    EMPLOYEE_CONTRACT_ENDED = "employee-contract-ended"

    # Special Events - Celebrations
    EMPLOYEE_BIRTHDAY = "employee-special-birthday"
    EMPLOYEE_WORK_ANNIVERSARY = "employee-special-work-anniversary"

    # HR Events - HR Team Notifications
    HR_PROBATION_ENDING = "hr-probation-ending"
    HR_CONTRACT_EXPIRING = "hr-contract-expiring"
    HR_PERFORMANCE_REVIEW_DUE = "hr-performance-review-due"
    HR_SALARY_INCREMENT_DUE = "hr-salary-increment-due"

    # Salary Events
    EMPLOYEE_SALARY_INCREMENT = "employee-salary-increment"

    # ==========================================
    # Leave Management Service Topics
    # ==========================================

    # Leave Request Events
    LEAVE_REQUESTED = "leave-requested"
    LEAVE_APPROVED = "leave-approved"
    LEAVE_REJECTED = "leave-rejected"
    LEAVE_CANCELLED = "leave-cancelled"

    # Leave Status Events
    LEAVE_STARTED = "leave-started"
    LEAVE_ENDED = "leave-ended"

    # Direct Notification Triggers from Leave Service
    NOTIFICATION_LEAVE_PENDING = "notification-leave-pending"
    NOTIFICATION_LEAVE_APPROVED = "notification-leave-approved"
    NOTIFICATION_LEAVE_REJECTED = "notification-leave-rejected"
    NOTIFICATION_LEAVE_REMINDER = "notification-leave-reminder"

    # HR Leave Events
    HR_LEAVE_BALANCE_LOW = "hr-leave-balance-low"
    HR_EXCESSIVE_LEAVE = "hr-excessive-leave"

    # ==========================================
    # Attendance Management Service Topics
    # ==========================================

    # Attendance Events
    ATTENDANCE_CHECKIN = "attendance-checkin"
    ATTENDANCE_CHECKOUT = "attendance-checkout"
    ATTENDANCE_LATE = "attendance-late"
    ATTENDANCE_ABSENT = "attendance-absent"
    ATTENDANCE_OVERTIME = "attendance-overtime"

    # Direct Notification Triggers from Attendance Service
    NOTIFICATION_LATE_ARRIVAL = "notification-late-arrival"
    NOTIFICATION_ABSENT_EMPLOYEE = "notification-absent-employee"
    NOTIFICATION_OVERTIME_ALERT = "notification-overtime-alert"

    # ==========================================
    # Notification Service Own Topics (Publishing)
    # ==========================================

    # Notification Status Events - For tracking and audit
    NOTIFICATION_SENT = "notification-sent"
    NOTIFICATION_FAILED = "notification-failed"
    NOTIFICATION_DELIVERED = "notification-delivered"

    # Audit Events
    AUDIT_NOTIFICATION_ACTION = "audit-notification-action"

    @classmethod
    def all_subscribed_topics(cls) -> list[str]:
        """Return list of all topics this service subscribes to."""
        return (
            cls.onboarding_topics()
            + cls.employee_lifecycle_topics()
            + cls.special_event_topics()
            + cls.hr_event_topics()
            + cls.leave_notification_topics()
            + cls.attendance_notification_topics()
        )

    @classmethod
    def onboarding_topics(cls) -> list[str]:
        """Return list of onboarding-related topics to subscribe to."""
        return [
            cls.USER_ONBOARDING_INITIATED,
            cls.USER_ONBOARDING_ASGARDEO_CREATED,
            cls.USER_ONBOARDING_COMPLETED,
            cls.USER_ONBOARDING_FAILED,
            cls.NOTIFICATION_WELCOME_EMAIL,
            cls.NOTIFICATION_INVITATION_EMAIL,
        ]

    @classmethod
    def employee_lifecycle_topics(cls) -> list[str]:
        """Return list of employee lifecycle topics to subscribe to."""
        return [
            cls.EMPLOYEE_CREATED,
            cls.EMPLOYEE_PROMOTED,
            cls.EMPLOYEE_TERMINATED,
            cls.EMPLOYEE_PROBATION_COMPLETED,
            cls.EMPLOYEE_CONTRACT_RENEWED,
            cls.EMPLOYEE_SALARY_INCREMENT,
        ]

    @classmethod
    def special_event_topics(cls) -> list[str]:
        """Return list of special event topics (celebrations)."""
        return [
            cls.EMPLOYEE_BIRTHDAY,
            cls.EMPLOYEE_WORK_ANNIVERSARY,
        ]

    @classmethod
    def hr_event_topics(cls) -> list[str]:
        """Return list of HR event topics for HR team notifications."""
        return [
            cls.HR_PROBATION_ENDING,
            cls.HR_CONTRACT_EXPIRING,
            cls.HR_PERFORMANCE_REVIEW_DUE,
            cls.HR_SALARY_INCREMENT_DUE,
            cls.HR_LEAVE_BALANCE_LOW,
            cls.HR_EXCESSIVE_LEAVE,
        ]

    @classmethod
    def leave_notification_topics(cls) -> list[str]:
        """Return list of leave-related notification topics."""
        return [
            cls.LEAVE_REQUESTED,
            cls.LEAVE_APPROVED,
            cls.LEAVE_REJECTED,
            cls.NOTIFICATION_LEAVE_PENDING,
            cls.NOTIFICATION_LEAVE_APPROVED,
            cls.NOTIFICATION_LEAVE_REJECTED,
            cls.NOTIFICATION_LEAVE_REMINDER,
        ]

    @classmethod
    def attendance_notification_topics(cls) -> list[str]:
        """Return list of attendance-related notification topics."""
        return [
            cls.ATTENDANCE_LATE,
            cls.ATTENDANCE_ABSENT,
            cls.NOTIFICATION_LATE_ARRIVAL,
            cls.NOTIFICATION_ABSENT_EMPLOYEE,
            cls.NOTIFICATION_OVERTIME_ALERT,
        ]

    @classmethod
    def publishing_topics(cls) -> list[str]:
        """Return list of topics this service publishes to."""
        return [
            cls.NOTIFICATION_SENT,
            cls.NOTIFICATION_FAILED,
            cls.NOTIFICATION_DELIVERED,
            cls.AUDIT_NOTIFICATION_ACTION,
        ]
