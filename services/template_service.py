"""
Template service for rendering email templates using Jinja2.
"""
import logging
from typing import Dict, Any
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from config import settings

logger = logging.getLogger(__name__)


class TemplateService:
    """Service for rendering email templates."""

    def __init__(self):
        """Initialize Jinja2 environment."""
        self.env = Environment(
            loader=FileSystemLoader(settings.TEMPLATES_DIR),
            autoescape=True
        )

    def render_template(
        self,
        template_name: str,
        context: Dict[str, Any]
    ) -> tuple[str, str]:
        """
        Render an email template with the given context.

        Args:
            template_name: Name of the template (without .html extension)
            context: Template context variables

        Returns:
            Tuple of (subject: str, html_content: str)

        Raises:
            TemplateNotFound: If template doesn't exist
            Exception: If rendering fails
        """
        try:
            # Load template
            template_file = f"{template_name}.html"
            template = self.env.get_template(template_file)

            # Render template
            html_content = template.render(**context)

            # Get subject from context or use default
            subject = context.get("subject", self._get_default_subject(template_name))

            logger.info(f"Template '{template_name}' rendered successfully")
            return subject, html_content

        except TemplateNotFound:
            logger.error(f"Template not found: {template_name}")
            raise
        except Exception as e:
            logger.exception(f"Error rendering template '{template_name}': {str(e)}")
            raise

    def _get_default_subject(self, template_name: str) -> str:
        """
        Get default subject for template.

        Args:
            template_name: Name of the template

        Returns:
            Default subject line
        """
        subjects = {
            "order_confirmation": "Order Confirmation - ShopHub",
            "order_shipped": "Your order has shipped!",
            "password_reset": "Reset your ShopHub password",
            "low_stock_alert": "[Admin] Low Stock Alert",
        }
        return subjects.get(template_name, "Notification from ShopHub")


# Singleton instance
template_service = TemplateService()
