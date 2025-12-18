"""
Hybrid Email Service
Provides a unified interface for sending emails with automatic fallback.
Uses Amazon SES as primary provider and Gmail SMTP as fallback.
Designed for Kubernetes deployment with robust error handling.
"""

import asyncio
from email.message import EmailMessage
from enum import Enum
from typing import Any, Dict, List, Optional

import aiosmtplib

from app.core.config import settings
from app.core.logging import get_logger
from app.services.ses_provider import SESProvider, get_ses_provider
from app.services.template_service import EmailType, get_template_service

logger = get_logger(__name__)


class EmailProvider(str, Enum):
    """Available email providers."""

    SES = "ses"
    SMTP = "smtp"


class EmailDeliveryResult:
    """Result of an email delivery attempt."""

    def __init__(
        self,
        success: bool,
        provider: Optional[EmailProvider] = None,
        message_id: Optional[str] = None,
        error: Optional[str] = None,
        fallback_used: bool = False,
    ):
        self.success = success
        self.provider = provider
        self.message_id = message_id
        self.error = error
        self.fallback_used = fallback_used

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "provider": self.provider.value if self.provider else None,
            "message_id": self.message_id,
            "error": self.error,
            "fallback_used": self.fallback_used,
        }


class HybridEmailService:
    """
    Hybrid email service that manages multiple email providers.
    Provides automatic fallback from SES to SMTP when primary fails.
    """

    def __init__(self):
        """Initialize the hybrid email service."""
        self._ses_provider: Optional[SESProvider] = None
        self._template_service = None

    @property
    def ses_provider(self) -> SESProvider:
        """Lazy load SES provider."""
        if self._ses_provider is None:
            self._ses_provider = get_ses_provider()
        return self._ses_provider

    @property
    def template_service(self):
        """Lazy load template service."""
        if self._template_service is None:
            self._template_service = get_template_service()
        return self._template_service

    def _get_primary_provider(self) -> EmailProvider:
        """Determine the primary email provider based on configuration."""
        if settings.EMAIL_PROVIDER == "smtp":
            return EmailProvider.SMTP
        return EmailProvider.SES

    def _get_fallback_provider(self) -> Optional[EmailProvider]:
        """Get the fallback provider if available."""
        if not settings.ENABLE_FALLBACK:
            return None

        primary = self._get_primary_provider()
        if primary == EmailProvider.SES and settings.smtp_configured:
            return EmailProvider.SMTP
        elif primary == EmailProvider.SMTP and settings.ses_configured:
            return EmailProvider.SES
        return None

    async def _send_via_ses(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        body: str,
        html: bool = False,
        sender_name: Optional[str] = None,
    ) -> bool:
        """Send email using Amazon SES."""
        return await self.ses_provider.send_email(
            to_email=to_email,
            to_name=to_name,
            subject=subject,
            body=body,
            html=html,
            sender_name=sender_name,
        )

    async def _send_via_smtp(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        body: str,
        html: bool = False,
        sender_name: Optional[str] = None,
    ) -> bool:
        """Send email using Gmail SMTP."""
        try:
            message = EmailMessage()
            message["Subject"] = subject
            message["From"] = (
                f"{sender_name or settings.EMAIL_SERVICE_NAME} <{settings.SMTP_USER}>"
            )
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
                username=settings.SMTP_USER,
                password=settings.SMTP_APP_PASSWORD,
            )

            logger.info(f"SMTP email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"SMTP failed to send email to {to_email}: {e}")
            return False

    async def _send_with_provider(
        self,
        provider: EmailProvider,
        to_email: str,
        to_name: str,
        subject: str,
        body: str,
        html: bool = False,
        sender_name: Optional[str] = None,
    ) -> bool:
        """Send email using the specified provider."""
        if provider == EmailProvider.SES:
            return await self._send_via_ses(
                to_email, to_name, subject, body, html, sender_name
            )
        else:
            return await self._send_via_smtp(
                to_email, to_name, subject, body, html, sender_name
            )

    async def send_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        body: str,
        html: bool = False,
        sender_name: Optional[str] = None,
    ) -> EmailDeliveryResult:
        """
        Send an email with automatic fallback support.

        Args:
            to_email: Recipient email address
            to_name: Recipient name
            subject: Email subject
            body: Email body content
            html: Whether body is HTML
            sender_name: Optional sender display name

        Returns:
            EmailDeliveryResult with success status and provider info
        """
        primary = self._get_primary_provider()
        fallback = self._get_fallback_provider()

        # Try primary provider with retries
        for attempt in range(settings.FALLBACK_RETRY_COUNT):
            try:
                success = await self._send_with_provider(
                    provider=primary,
                    to_email=to_email,
                    to_name=to_name,
                    subject=subject,
                    body=body,
                    html=html,
                    sender_name=sender_name,
                )
                if success:
                    logger.info(
                        f"Email sent via {primary.value} to {to_email} "
                        f"(attempt {attempt + 1})"
                    )
                    return EmailDeliveryResult(
                        success=True,
                        provider=primary,
                        fallback_used=False,
                    )
            except Exception as e:
                logger.warning(
                    f"Primary provider {primary.value} attempt {attempt + 1} failed: {e}"
                )

            # Small delay between retries
            if attempt < settings.FALLBACK_RETRY_COUNT - 1:
                await asyncio.sleep(1)

        # Try fallback provider if available
        if fallback:
            logger.info(f"Attempting fallback to {fallback.value} for {to_email}")
            try:
                success = await self._send_with_provider(
                    provider=fallback,
                    to_email=to_email,
                    to_name=to_name,
                    subject=subject,
                    body=body,
                    html=html,
                    sender_name=sender_name,
                )
                if success:
                    logger.info(
                        f"Email sent via fallback {fallback.value} to {to_email}"
                    )
                    return EmailDeliveryResult(
                        success=True,
                        provider=fallback,
                        fallback_used=True,
                    )
            except Exception as e:
                logger.error(f"Fallback provider {fallback.value} also failed: {e}")

        # All providers failed
        error_msg = f"All email providers failed for {to_email}"
        logger.error(error_msg)
        return EmailDeliveryResult(
            success=False,
            error=error_msg,
        )

    async def send_templated_email(
        self,
        to_email: str,
        subject: str,
        email_type: EmailType,
        context: Dict[str, Any],
        sender_name: Optional[str] = None,
    ) -> EmailDeliveryResult:
        """
        Send an HTML email using a predefined template with fallback support.

        Args:
            to_email: Recipient email address
            subject: Email subject
            email_type: Type of email template to use
            context: Template context variables
            sender_name: Optional sender display name

        Returns:
            EmailDeliveryResult with success status and provider info
        """
        try:
            # Add recipient email to context for footer
            context["recipient_email"] = to_email

            # Render the template using existing Jinja2 templates
            html_content = self.template_service.render_email_type(email_type, context)

            # Send using hybrid system
            result = await self.send_email(
                to_email=to_email,
                to_name=context.get(
                    "username", context.get("recipient_name", to_email)
                ),
                subject=subject,
                body=html_content,
                html=True,
                sender_name=sender_name,
            )

            if result.success:
                logger.info(
                    f"Templated email ({email_type.value}) sent to {to_email} "
                    f"via {result.provider.value if result.provider else 'unknown'}"
                )
            else:
                logger.error(
                    f"Failed to send templated email ({email_type.value}) to {to_email}"
                )

            return result

        except Exception as e:
            logger.error(f"Template rendering error for {to_email}: {e}")
            return EmailDeliveryResult(
                success=False,
                error=f"Template rendering failed: {e}",
            )

    async def send_welcome_email(
        self,
        to_email: str,
        username: str,
        employee_id: Optional[str] = None,
        department: Optional[str] = None,
        role: Optional[str] = None,
        start_date: Optional[str] = None,
        action_url: Optional[str] = None,
        company_name: Optional[str] = None,
    ) -> EmailDeliveryResult:
        """Send a welcome email to a new user."""
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

        return await self.send_templated_email(
            to_email=to_email,
            subject=f"Welcome to {company_name or 'HRMS Cloud Platform'}!",
            email_type=EmailType.WELCOME,
            context=context,
        )

    async def send_notification(
        self,
        to_email: str,
        username: str,
        title: str,
        message: str,
        notification_title: Optional[str] = None,
        details: Optional[Dict[str, str]] = None,
        action_url: Optional[str] = None,
        action_text: Optional[str] = None,
    ) -> EmailDeliveryResult:
        """Send a general notification email."""
        context = {
            "username": username,
            "title": title,
            "message": message,
            "notification_title": notification_title or title,
            "details": details,
            "action_url": action_url,
            "action_text": action_text or "View Details",
        }

        return await self.send_templated_email(
            to_email=to_email,
            subject=title,
            email_type=EmailType.NOTIFICATION,
            context=context,
        )

    async def send_reminder(
        self,
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
    ) -> EmailDeliveryResult:
        """Send a reminder email."""
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

        return await self.send_templated_email(
            to_email=to_email,
            subject=subject,
            email_type=EmailType.REMINDER,
            context=context,
        )

    async def send_congratulations(
        self,
        to_email: str,
        recipient_name: str,
        message: str,
        achievement: Optional[str] = None,
        details: Optional[Dict[str, str]] = None,
        action_url: Optional[str] = None,
        action_text: Optional[str] = None,
        closing_message: Optional[str] = None,
    ) -> EmailDeliveryResult:
        """Send a congratulations email."""
        context = {
            "recipient_name": recipient_name,
            "message": message,
            "achievement": achievement,
            "details": details,
            "action_url": action_url,
            "action_text": action_text or "View Details",
            "closing_message": closing_message,
        }

        return await self.send_templated_email(
            to_email=to_email,
            subject="Congratulations! 🎉",
            email_type=EmailType.CONGRATULATIONS,
            context=context,
        )

    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of all email providers.

        Returns:
            Dictionary with health status of each provider
        """
        health = {
            "primary_provider": self._get_primary_provider().value,
            "fallback_provider": None,
            "fallback_enabled": settings.ENABLE_FALLBACK,
            "providers": {},
        }

        fallback = self._get_fallback_provider()
        if fallback:
            health["fallback_provider"] = fallback.value

        # Check SES health
        if settings.ses_configured:
            try:
                quota = await self.ses_provider.get_send_quota()
                health["providers"]["ses"] = {
                    "status": "healthy" if quota else "degraded",
                    "configured": True,
                    "quota": quota,
                }
            except Exception as e:
                health["providers"]["ses"] = {
                    "status": "unhealthy",
                    "configured": True,
                    "error": str(e),
                }
        else:
            health["providers"]["ses"] = {
                "status": "not_configured",
                "configured": False,
            }

        # Check SMTP health
        if settings.smtp_configured:
            health["providers"]["smtp"] = {
                "status": "configured",
                "configured": True,
                "host": settings.SMTP_HOST,
                "port": settings.SMTP_PORT,
            }
        else:
            health["providers"]["smtp"] = {
                "status": "not_configured",
                "configured": False,
            }

        return health


# Global hybrid email service instance
_hybrid_email_service: Optional[HybridEmailService] = None


def get_hybrid_email_service() -> HybridEmailService:
    """
    Get or create the global hybrid email service instance.

    Returns:
        HybridEmailService instance
    """
    global _hybrid_email_service
    if _hybrid_email_service is None:
        _hybrid_email_service = HybridEmailService()
    return _hybrid_email_service


# Convenience functions for backward compatibility
async def send_email(
    to_email: str,
    to_name: str,
    subject: str,
    body: str,
    html: bool = False,
) -> bool:
    """Send an email using the hybrid service (backward compatible)."""
    service = get_hybrid_email_service()
    result = await service.send_email(to_email, to_name, subject, body, html)
    return result.success


async def send_templated_email(
    to_email: str,
    subject: str,
    email_type: EmailType,
    context: Dict[str, Any],
    sender_name: Optional[str] = None,
) -> bool:
    """Send a templated email using the hybrid service (backward compatible)."""
    service = get_hybrid_email_service()
    result = await service.send_templated_email(
        to_email, subject, email_type, context, sender_name
    )
    return result.success


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
    """Send a welcome email (backward compatible)."""
    service = get_hybrid_email_service()
    result = await service.send_welcome_email(
        to_email,
        username,
        employee_id,
        department,
        role,
        start_date,
        action_url,
        company_name,
    )
    return result.success


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
    """Send a notification email (backward compatible)."""
    service = get_hybrid_email_service()
    result = await service.send_notification(
        to_email,
        username,
        title,
        message,
        notification_title,
        details,
        action_url,
        action_text,
    )
    return result.success


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
    """Send a reminder email (backward compatible)."""
    service = get_hybrid_email_service()
    result = await service.send_reminder(
        to_email,
        username,
        subject,
        reminder_title,
        reminder_message,
        due_date,
        urgency,
        details,
        action_url,
        action_text,
    )
    return result.success


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
    """Send a congratulations email (backward compatible)."""
    service = get_hybrid_email_service()
    result = await service.send_congratulations(
        to_email,
        recipient_name,
        message,
        achievement,
        details,
        action_url,
        action_text,
        closing_message,
    )
    return result.success
