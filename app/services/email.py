"""
Email Service Module
Provides async email sending functionality with support for plain text and HTML templates.
"""

from email.message import EmailMessage
from typing import Any, Dict, Optional

import aiosmtplib

from app.core.config import settings
from app.core.logging import get_logger
from app.services.template_service import EmailType, get_template_service

logger = get_logger(__name__)


async def send_email(
    to_email: str,
    to_name: str,
    subject: str,
    body: str,
    html: bool = False,
) -> bool:
    """
    Send an email asynchronously.

    Args:
        to_email: Recipient email address
        to_name: Recipient name
        subject: Email subject
        body: Email body content
        html: Whether body is HTML or plain text

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = f"{settings.EMAIL_SERVICE_NAME} <{settings.SMTP_USER}>"
        message["To"] = f"{to_name} <{to_email}>"

        if html:
            message.set_content("Please view this email in an HTML-capable client.")
            message.add_alternative(body, subtype="html")
        else:
            message.set_content(body)

        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            use_tls=settings.SMTP_USE_TLS,
            username=settings.SMTP_USER,
            password=settings.SMTP_APP_PASSWORD,
        )

        logger.info(f"Email sent successfully to {to_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        return False


async def send_notification_email(
    to_email: str,
    to_name: str,
    subject: str,
    body: str,
) -> bool:
    """
    Send a notification email.

    Args:
        to_email: Recipient email address
        to_name: Recipient name
        subject: Email subject
        body: Email body content

    Returns:
        bool: True if successful, False otherwise
    """
    return await send_email(to_email, to_name, subject, body, html=False)


async def send_email_message(
    msg_from: str,
    msg_to: str,
    msg_subject: str,
    msg_body: str,
):
    """
    Send a basic email message (for testing).

    Args:
        msg_from: Sender display name
        msg_to: Recipient email address
        msg_subject: Email subject
        msg_body: Email body content
    """
    message = EmailMessage()
    message["From"] = f"{msg_from} <{settings.SMTP_USER}>"
    message["To"] = msg_to
    message["Subject"] = msg_subject
    message.set_content(msg_body)

    await aiosmtplib.send(
        message,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        use_tls=settings.SMTP_USE_TLS,
        username=settings.SMTP_USER,
        password=settings.SMTP_APP_PASSWORD,
    )
    logger.info(f"Basic email sent to {msg_to}")


async def send_templated_email(
    to_email: str,
    subject: str,
    email_type: EmailType,
    context: Dict[str, Any],
    sender_name: Optional[str] = None,
) -> bool:
    """
    Send an HTML email using a predefined template.

    Args:
        to_email: Recipient email address
        subject: Email subject
        email_type: Type of email template to use
        context: Template context variables (username, message, details, etc.)
        sender_name: Optional sender display name

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        template_service = get_template_service()

        # Add recipient email to context for footer
        context["recipient_email"] = to_email

        # Render the template
        html_content = template_service.render_email_type(email_type, context)

        # Create email message with mixed content (for inline images)
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = (
            f"{sender_name or settings.EMAIL_SERVICE_NAME} <{settings.SMTP_USER}>"
        )
        message["To"] = to_email

        # Set plain text fallback
        message.set_content(
            f"This email contains HTML content. Please view it in an HTML-capable email client.\n\nSubject: {subject}"
        )

        # Add HTML content as alternative
        message.add_alternative(html_content, subtype="html")

        # Send the email
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            use_tls=settings.SMTP_USE_TLS,
            username=settings.SMTP_USER,
            password=settings.SMTP_APP_PASSWORD,
        )

        logger.info(
            f"Templated email ({email_type.value}) sent successfully to {to_email}"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to send templated email to {to_email}: {str(e)}")
        return False


async def send_welcome_email(
    to_email: str,
    username: str,
    employee_id: Optional[str] = None,
    department: Optional[str] = None,
    role: Optional[str] = None,
    start_date: Optional[str] = None,
    action_url: Optional[str] = None,
    company_name: Optional[str] = None,
) -> bool:
    """
    Send a welcome email to a new user.

    Args:
        to_email: Recipient email address
        username: User's display name
        employee_id: Optional employee ID
        department: Optional department name
        role: Optional job role/title
        start_date: Optional start date
        action_url: Optional URL for getting started button
        company_name: Optional company name override

    Returns:
        bool: True if successful, False otherwise
    """
    context = {
        "username": username,
        "email": to_email,
        "employee_id": employee_id,
        "department": department,
        "role": role,
        "start_date": start_date,
        "action_url": action_url,
        "action_text": "Get Started",
    }
    if company_name:
        context["company_name"] = company_name

    return await send_templated_email(
        to_email=to_email,
        subject=f"Welcome to {company_name or 'HRMS Cloud Platform'}!",
        email_type=EmailType.WELCOME,
        context=context,
    )


async def send_notification(
    to_email: str,
    username: str,
    title: str,
    message: str,
    notification_title: Optional[str] = None,
    details: Optional[Dict[str, str]] = None,
    action_url: Optional[str] = None,
    action_text: Optional[str] = None,
) -> bool:
    """
    Send a general notification email.

    Args:
        to_email: Recipient email address
        username: User's display name
        title: Email title (shown in header)
        message: Main notification message
        notification_title: Title shown in the message box
        details: Optional key-value details to display
        action_url: Optional action button URL
        action_text: Optional action button text

    Returns:
        bool: True if successful, False otherwise
    """
    context = {
        "username": username,
        "title": title,
        "message": message,
        "notification_title": notification_title or title,
        "details": details,
        "action_url": action_url,
        "action_text": action_text or "View Details",
    }

    return await send_templated_email(
        to_email=to_email,
        subject=title,
        email_type=EmailType.NOTIFICATION,
        context=context,
    )


async def send_reminder(
    to_email: str,
    username: str,
    subject: str,
    reminder_title: str,
    reminder_message: str,
    due_date: Optional[str] = None,
    urgency: Optional[str] = None,
    details: Optional[Dict[str, str]] = None,
    action_url: Optional[str] = None,
    action_text: Optional[str] = None,
) -> bool:
    """
    Send a reminder email.

    Args:
        to_email: Recipient email address
        username: User's display name
        subject: Email subject
        reminder_title: Title of the reminder
        reminder_message: Main reminder message
        due_date: Optional due date string
        urgency: Optional urgency level (high, medium, low)
        details: Optional key-value details
        action_url: Optional action button URL
        action_text: Optional action button text

    Returns:
        bool: True if successful, False otherwise
    """
    context = {
        "username": username,
        "subject": subject,
        "reminder_title": reminder_title,
        "reminder_message": reminder_message,
        "due_date": due_date,
        "urgency": urgency,
        "details": details,
        "action_url": action_url,
        "action_text": action_text or "Take Action Now",
    }

    return await send_templated_email(
        to_email=to_email,
        subject=subject,
        email_type=EmailType.REMINDER,
        context=context,
    )


async def send_congratulations(
    to_email: str,
    recipient_name: str,
    message: str,
    achievement: Optional[str] = None,
    details: Optional[Dict[str, str]] = None,
    action_url: Optional[str] = None,
    action_text: Optional[str] = None,
    closing_message: Optional[str] = None,
) -> bool:
    """
    Send a congratulations email.

    Args:
        to_email: Recipient email address
        recipient_name: Recipient's display name
        message: Main congratulations message
        achievement: Optional achievement description
        details: Optional key-value details
        action_url: Optional action button URL
        action_text: Optional action button text
        closing_message: Optional custom closing message

    Returns:
        bool: True if successful, False otherwise
    """
    context = {
        "recipient_name": recipient_name,
        "message": message,
        "achievement": achievement,
        "details": details,
        "action_url": action_url,
        "action_text": action_text or "View Details",
        "closing_message": closing_message,
    }

    return await send_templated_email(
        to_email=to_email,
        subject="Congratulations! 🎉",
        email_type=EmailType.CONGRATULATIONS,
        context=context,
    )
