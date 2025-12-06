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


# Template file mapping
TEMPLATE_MAP = {
    EmailType.WELCOME: "system_welcome.html",
    EmailType.NOTIFICATION: "generic_notifications.html",
    EmailType.REMINDER: "generic_reminder.html",
    EmailType.CONGRATULATIONS: "generic_congratulations.html",
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

    def get_available_templates(self) -> list[str]:
        """Get list of available template files"""
        try:
            return [f.name for f in self.template_dir.glob("*.html")]
        except Exception as e:
            logger.error(f"Error listing templates: {e}")
            return []


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
