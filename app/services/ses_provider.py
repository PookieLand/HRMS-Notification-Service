"""
Amazon SES Email Provider Service
Provides async email sending functionality using Amazon Simple Email Service.
Supports both raw emails and templated emails with HTML content.
"""

import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class SESProvider:
    """
    Amazon SES email provider for sending transactional emails.
    Designed to work in Kubernetes environments with IAM roles or explicit credentials.
    """

    def __init__(self):
        """Initialize SES client with configuration from settings."""
        self._client = None
        self._initialized = False

    def _get_client(self):
        """
        Lazy initialization of SES client.
        Supports both explicit credentials and IAM role-based authentication.
        """
        if self._client is None:
            try:
                # Check if explicit credentials are provided
                if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
                    self._client = boto3.client(
                        "ses",
                        region_name=settings.AWS_REGION,
                        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    )
                    logger.info("SES client initialized with explicit credentials")
                else:
                    # Use IAM role (for Kubernetes with IRSA or EC2 instance profile)
                    self._client = boto3.client(
                        "ses",
                        region_name=settings.AWS_REGION,
                    )
                    logger.info("SES client initialized with IAM role credentials")

                self._initialized = True
            except Exception as e:
                logger.error(f"Failed to initialize SES client: {e}")
                raise SESProviderError(f"SES initialization failed: {e}")

        return self._client

    @property
    def is_available(self) -> bool:
        """Check if SES provider is available and configured."""
        try:
            if not settings.SES_ENABLED:
                return False
            # Try to get the client to verify configuration
            self._get_client()
            return True
        except Exception:
            return False

    async def send_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        body: str,
        html: bool = False,
        sender_name: Optional[str] = None,
        reply_to: Optional[List[str]] = None,
    ) -> bool:
        """
        Send an email using Amazon SES.

        Args:
            to_email: Recipient email address
            to_name: Recipient name
            subject: Email subject
            body: Email body (plain text or HTML)
            html: Whether body is HTML content
            sender_name: Optional sender display name
            reply_to: Optional list of reply-to addresses

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            client = self._get_client()

            # Build sender address
            sender = sender_name or settings.EMAIL_SERVICE_NAME
            source = f"{sender} <{settings.SES_SENDER_EMAIL}>"

            # Build destination
            destination = {"ToAddresses": [f"{to_name} <{to_email}>"]}

            # Build message body
            if html:
                message_body = {
                    "Html": {"Data": body, "Charset": "UTF-8"},
                    "Text": {
                        "Data": "Please view this email in an HTML-capable client.",
                        "Charset": "UTF-8",
                    },
                }
            else:
                message_body = {"Text": {"Data": body, "Charset": "UTF-8"}}

            # Build message
            message = {
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": message_body,
            }

            # Send email parameters
            send_params = {
                "Source": source,
                "Destination": destination,
                "Message": message,
            }

            # Add optional parameters
            if reply_to:
                send_params["ReplyToAddresses"] = reply_to

            if settings.SES_CONFIGURATION_SET:
                send_params["ConfigurationSetName"] = settings.SES_CONFIGURATION_SET

            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: client.send_email(**send_params)
            )

            message_id = response.get("MessageId", "unknown")
            logger.info(
                f"SES email sent successfully to {to_email}, MessageId: {message_id}"
            )
            return True

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            logger.error(
                f"SES ClientError sending to {to_email}: {error_code} - {error_message}"
            )
            return False
        except BotoCoreError as e:
            logger.error(f"SES BotoCoreError sending to {to_email}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending SES email to {to_email}: {e}")
            return False

    async def send_raw_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        text_body: str,
        html_body: str,
        sender_name: Optional[str] = None,
    ) -> bool:
        """
        Send a raw email with both text and HTML parts using Amazon SES.
        Provides more control over email structure.

        Args:
            to_email: Recipient email address
            to_name: Recipient name
            subject: Email subject
            text_body: Plain text body
            html_body: HTML body
            sender_name: Optional sender display name

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            client = self._get_client()

            # Build sender address
            sender = sender_name or settings.EMAIL_SERVICE_NAME
            source = f"{sender} <{settings.SES_SENDER_EMAIL}>"

            # Create MIME message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = source
            msg["To"] = f"{to_name} <{to_email}>"

            # Attach parts
            part1 = MIMEText(text_body, "plain", "utf-8")
            part2 = MIMEText(html_body, "html", "utf-8")
            msg.attach(part1)
            msg.attach(part2)

            # Send raw email parameters
            send_params = {
                "Source": source,
                "Destinations": [to_email],
                "RawMessage": {"Data": msg.as_string()},
            }

            if settings.SES_CONFIGURATION_SET:
                send_params["ConfigurationSetName"] = settings.SES_CONFIGURATION_SET

            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: client.send_raw_email(**send_params)
            )

            message_id = response.get("MessageId", "unknown")
            logger.info(
                f"SES raw email sent successfully to {to_email}, MessageId: {message_id}"
            )
            return True

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            logger.error(
                f"SES ClientError sending raw email to {to_email}: {error_code} - {error_message}"
            )
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending SES raw email to {to_email}: {e}")
            return False

    async def send_templated_ses_email(
        self,
        to_email: str,
        template_name: str,
        template_data: Dict[str, Any],
        sender_name: Optional[str] = None,
    ) -> bool:
        """
        Send an email using an SES template (if you've created templates in SES console).
        Note: This uses SES-native templates, not the Jinja2 templates from this app.

        Args:
            to_email: Recipient email address
            template_name: Name of the SES template
            template_data: Dictionary of template variables
            sender_name: Optional sender display name

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            import json

            client = self._get_client()

            sender = sender_name or settings.EMAIL_SERVICE_NAME
            source = f"{sender} <{settings.SES_SENDER_EMAIL}>"

            send_params = {
                "Source": source,
                "Destination": {"ToAddresses": [to_email]},
                "Template": template_name,
                "TemplateData": json.dumps(template_data),
            }

            if settings.SES_CONFIGURATION_SET:
                send_params["ConfigurationSetName"] = settings.SES_CONFIGURATION_SET

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: client.send_templated_email(**send_params)
            )

            message_id = response.get("MessageId", "unknown")
            logger.info(
                f"SES templated email sent successfully to {to_email}, MessageId: {message_id}"
            )
            return True

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            logger.error(
                f"SES ClientError sending templated email to {to_email}: {error_code} - {error_message}"
            )
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error sending SES templated email to {to_email}: {e}"
            )
            return False

    async def verify_email_address(self, email: str) -> bool:
        """
        Send a verification email to an address (for sandbox mode).

        Args:
            email: Email address to verify

        Returns:
            bool: True if verification email sent successfully
        """
        try:
            client = self._get_client()

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, lambda: client.verify_email_identity(EmailAddress=email)
            )

            logger.info(f"Verification email sent to {email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send verification email to {email}: {e}")
            return False

    async def get_send_quota(self) -> Optional[Dict[str, Any]]:
        """
        Get current SES sending quota and statistics.

        Returns:
            Dictionary with quota information or None on error
        """
        try:
            client = self._get_client()

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, client.get_send_quota)

            return {
                "max_24_hour_send": response.get("Max24HourSend", 0),
                "max_send_rate": response.get("MaxSendRate", 0),
                "sent_last_24_hours": response.get("SentLast24Hours", 0),
            }

        except Exception as e:
            logger.error(f"Failed to get SES send quota: {e}")
            return None


class SESProviderError(Exception):
    """Custom exception for SES provider errors."""

    pass


# Global SES provider instance
_ses_provider: Optional[SESProvider] = None


def get_ses_provider() -> SESProvider:
    """
    Get or create the global SES provider instance.

    Returns:
        SESProvider instance
    """
    global _ses_provider
    if _ses_provider is None:
        _ses_provider = SESProvider()
    return _ses_provider
