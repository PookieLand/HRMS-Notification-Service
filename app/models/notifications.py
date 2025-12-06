from typing import Optional, Dict

from pydantic import BaseModel, EmailStr
from sqlmodel import Field

from app.services.template_service import EmailType


# For the /basic/notify endpoint
class BasicNotification(BaseModel):
    """Basic notification request model"""

    email_from: str = Field(..., description="Sender display name")
    recipient_email: EmailStr = Field(..., description="Recipient email address")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Email body content")


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
