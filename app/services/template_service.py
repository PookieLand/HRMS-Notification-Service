"""
Email Template Service with Jinja2 Rendering
Provides dynamic template rendering for various notification types.
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.logging import get_logger

logger = get_logger(__name__)


class EmailType(str, Enum):
    """Supported email template types"""

    WELCOME = "welcome"
    NOTIFICATION = "notification"
    REMINDER = "reminder"
    CONGRATULATIONS = "congratulations"
    INVITATION = "invitation"
    CELEBRATION = "celebration"
    LEAVE = "leave"


# Template file mapping
TEMPLATE_MAP = {
    EmailType.WELCOME: "system_welcome.html",
    EmailType.NOTIFICATION: "generic_notifications.html",
    EmailType.REMINDER: "generic_reminder.html",
    EmailType.CONGRATULATIONS: "generic_congratulations.html",
    EmailType.INVITATION: "onboarding_invitation.html",
    EmailType.CELEBRATION: "celebration.html",
    EmailType.LEAVE: "leave_notification.html",
}


class TemplateService:
    """Service for rendering email templates with Jinja2"""

    def __init__(self, template_dir: Optional[str] = None):
        """
        Initialize template service.

        Args:
            template_dir: Path to templates directory. Defaults to app/templates.
        """
        if template_dir is None:
            # Get the templates directory relative to this file
            base_path = Path(__file__).parent.parent
            template_dir = str(base_path / "templates")

        self.template_dir = Path(template_dir)

        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

        # Add custom filters
        self.env.filters["format_date"] = self._format_date
        self.env.filters["format_currency"] = self._format_currency

        logger.info(f"Template service initialized with directory: {self.template_dir}")

    def _format_date(self, value: Any, format: str = "%B %d, %Y") -> str:
        """Format date for display in templates"""
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError:
                return value
        if isinstance(value, datetime):
            return value.strftime(format)
        return str(value)

    def _format_currency(self, value: Any, currency: str = "$") -> str:
        """Format currency for display in templates"""
        try:
            return f"{currency}{float(value):,.2f}"
        except (ValueError, TypeError):
            return str(value)

    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render a template with the given context.

        Args:
            template_name: Name of the template file
            context: Dictionary of variables to pass to template

        Returns:
            Rendered HTML string
        """
        try:
            # Add default context values
            default_context = {
                "year": datetime.now().year,
                "company_name": "HRMS Cloud Platform",
            }
            # Merge defaults with provided context (provided values take precedence)
            final_context = {**default_context, **context}

            template = self.env.get_template(template_name)
            rendered = template.render(**final_context)

            logger.debug(f"Template '{template_name}' rendered successfully")
            return rendered

        except Exception as e:
            logger.error(f"Template rendering error for '{template_name}': {e}")
            raise TemplateRenderError(f"Failed to render template: {e}")

    def render_email_type(self, email_type: EmailType, context: Dict[str, Any]) -> str:
        """
        Render an email template by type.

        Args:
            email_type: The type of email to render
            context: Dictionary of variables to pass to template

        Returns:
            Rendered HTML string
        """
        template_name = TEMPLATE_MAP.get(email_type)
        if not template_name:
            raise TemplateNotFoundError(
                f"No template found for email type: {email_type}"
            )

        return self.render(template_name, context)

    def render_invitation(self, context: Dict[str, Any]) -> str:
        """
        Render an onboarding invitation email.

        Args:
            context: Dictionary containing:
                - username: Recipient name
                - role: Job role
                - job_title: Job title
                - department: Department name
                - start_date: Start date
                - action_url: Onboarding URL
                - message: Custom message (optional)

        Returns:
            Rendered HTML string
        """
        return self.render_email_type(EmailType.INVITATION, context)

    def render_celebration(
        self,
        celebration_type: str,
        context: Dict[str, Any],
    ) -> str:
        """
        Render a celebration email (birthday/anniversary).

        Args:
            celebration_type: 'birthday' or 'anniversary'
            context: Dictionary containing recipient details

        Returns:
            Rendered HTML string
        """
        context["celebration_type"] = celebration_type
        return self.render_email_type(EmailType.CELEBRATION, context)

    def render_leave_notification(
        self,
        status: str,
        context: Dict[str, Any],
    ) -> str:
        """
        Render a leave notification email.

        Args:
            status: 'approved', 'rejected', or 'pending'
            context: Dictionary containing leave details

        Returns:
            Rendered HTML string
        """
        context["status"] = status
        return self.render_email_type(EmailType.LEAVE, context)

    def get_available_templates(self) -> list[str]:
        """Get list of available template files"""
        try:
            return [f.name for f in self.template_dir.glob("*.html")]
        except Exception as e:
            logger.error(f"Error listing templates: {e}")
            return []

    def get_supported_email_types(self) -> list[str]:
        """Get list of supported email types"""
        return [email_type.value for email_type in EmailType]


class TemplateRenderError(Exception):
    """Raised when template rendering fails"""

    pass


class TemplateNotFoundError(Exception):
    """Raised when a template is not found"""

    pass


# Global template service instance
_template_service: Optional[TemplateService] = None


def get_template_service() -> TemplateService:
    """
    Get or create the global template service instance.

    Returns:
        TemplateService instance
    """
    global _template_service
    if _template_service is None:
        _template_service = TemplateService()
    return _template_service


def render_email(
    email_type: EmailType,
    username: Optional[str] = None,
    message: Optional[str] = None,
    **kwargs: Any,
) -> str:
    """
    Convenience function to render an email template.

    Args:
        email_type: Type of email to render
        username: Recipient's name/username
        message: Main message content
        **kwargs: Additional template variables

    Returns:
        Rendered HTML string
    """
    service = get_template_service()

    context = {"username": username, "message": message, **kwargs}

    # Remove None values from context
    context = {k: v for k, v in context.items() if v is not None}

    return service.render_email_type(email_type, context)


def render_invitation_email(
    username: str,
    email: str,
    role: str,
    job_title: Optional[str] = None,
    department: Optional[str] = None,
    start_date: Optional[str] = None,
    action_url: Optional[str] = None,
    **kwargs: Any,
) -> str:
    """
    Convenience function to render an invitation email.

    Args:
        username: Recipient's name
        email: Recipient's email
        role: Job role
        job_title: Job title (optional)
        department: Department name (optional)
        start_date: Start date (optional)
        action_url: Onboarding URL (optional)
        **kwargs: Additional template variables

    Returns:
        Rendered HTML string
    """
    service = get_template_service()

    context = {
        "username": username,
        "email": email,
        "role": role,
        "job_title": job_title or role,
        "department": department,
        "start_date": start_date,
        "action_url": action_url,
        **kwargs,
    }

    context = {k: v for k, v in context.items() if v is not None}

    return service.render_invitation(context)


def render_celebration_email(
    celebration_type: str,
    recipient_name: str,
    message: Optional[str] = None,
    years_of_service: Optional[int] = None,
    details: Optional[Dict[str, str]] = None,
    **kwargs: Any,
) -> str:
    """
    Convenience function to render a celebration email.

    Args:
        celebration_type: 'birthday' or 'anniversary'
        recipient_name: Recipient's name
        message: Custom message (optional)
        years_of_service: Years of service for anniversary (optional)
        details: Additional details to display (optional)
        **kwargs: Additional template variables

    Returns:
        Rendered HTML string
    """
    service = get_template_service()

    context = {
        "recipient_name": recipient_name,
        "message": message,
        "years_of_service": years_of_service,
        "details": details,
        **kwargs,
    }

    context = {k: v for k, v in context.items() if v is not None}

    return service.render_celebration(celebration_type, context)


def render_leave_email(
    status: str,
    username: str,
    title: str,
    message: str,
    details: Optional[Dict[str, str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    rejection_reason: Optional[str] = None,
    approved_by: Optional[str] = None,
    rejected_by: Optional[str] = None,
    action_url: Optional[str] = None,
    action_text: Optional[str] = None,
    **kwargs: Any,
) -> str:
    """
    Convenience function to render a leave notification email.

    Args:
        status: 'approved', 'rejected', or 'pending'
        username: Recipient's name
        title: Email title
        message: Main message
        details: Leave details dictionary (optional)
        start_date: Leave start date (optional)
        end_date: Leave end date (optional)
        rejection_reason: Reason for rejection (optional)
        approved_by: Name of approver (optional)
        rejected_by: Name of reviewer who rejected (optional)
        action_url: URL for action button (optional)
        action_text: Text for action button (optional)
        **kwargs: Additional template variables

    Returns:
        Rendered HTML string
    """
    service = get_template_service()

    context = {
        "username": username,
        "title": title,
        "message": message,
        "details": details,
        "start_date": start_date,
        "end_date": end_date,
        "rejection_reason": rejection_reason,
        "approved_by": approved_by,
        "rejected_by": rejected_by,
        "action_url": action_url,
        "action_text": action_text,
        **kwargs,
    }

    context = {k: v for k, v in context.items() if v is not None}

    return service.render_leave_notification(status, context)
