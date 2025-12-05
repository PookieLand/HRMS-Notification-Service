# from email.mime.multipart import MIMEMultipart
# from email.mime.text import MIMEText
from email.message import EmailMessage

import aiosmtplib

from app.core.config import settings
from app.core.logging import get_logger

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
        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        message["To"] = f"{to_name} <{to_email}>"

        # Add body
        part = MIMEText(body, "html" if html else "plain")
        message.attach(part)

        # Send email
        async with aiosmtplib.SMTP(
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            use_tls=settings.SMTP_TLS,
        ) as smtp:
            await smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            await smtp.send_message(message)

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


# This is for test notification
async def send_email_message(
    msg_from: str,
    msg_to: str,
    msg_subject: str,
    msg_body: str,
):
    message = EmailMessage()
    message["From"] = msg_from
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
