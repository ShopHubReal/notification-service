"""
RabbitMQ consumer for processing notification events.
"""
import json
import logging
import asyncio
from typing import Optional
import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic, BasicProperties
from sqlalchemy.orm import Session
from config import settings
from database import SessionLocal
from services.email_service import email_service
from services.template_service import template_service
from models.database import NotificationLog
from datetime import datetime

logger = logging.getLogger(__name__)


class NotificationConsumer:
    """RabbitMQ consumer for notification events."""

    def __init__(self):
        """Initialize consumer."""
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[BlockingChannel] = None

    def connect(self):
        """Establish connection to RabbitMQ."""
        try:
            parameters = pika.URLParameters(settings.RABBITMQ_URL)
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()

            # Declare exchanges
            self.channel.exchange_declare(
                exchange="orders",
                exchange_type="topic",
                durable=True
            )
            self.channel.exchange_declare(
                exchange="inventory",
                exchange_type="topic",
                durable=True
            )
            self.channel.exchange_declare(
                exchange="payments",
                exchange_type="topic",
                durable=True
            )

            # Declare queues and bind them
            self._setup_queues()

            logger.info("Connected to RabbitMQ successfully")

        except Exception as e:
            logger.exception(f"Failed to connect to RabbitMQ: {str(e)}")
            raise

    def _setup_queues(self):
        """Setup queues and bindings."""
        queues = [
            ("notifications.order.completed", "orders", "order.completed"),
            ("notifications.order.shipped", "orders", "order.shipped"),
            ("notifications.low_stock", "inventory", "inventory.low_stock"),
            ("notifications.payment.failed", "payments", "payment.failed"),
        ]

        for queue_name, exchange, routing_key in queues:
            self.channel.queue_declare(queue=queue_name, durable=True)
            self.channel.queue_bind(
                queue=queue_name,
                exchange=exchange,
                routing_key=routing_key
            )
            logger.info(f"Queue '{queue_name}' bound to exchange '{exchange}' with key '{routing_key}'")

    def start_consuming(self):
        """Start consuming messages from all queues."""
        if not self.channel:
            raise RuntimeError("Not connected to RabbitMQ")

        # Setup consumers for each queue
        self.channel.basic_consume(
            queue="notifications.order.completed",
            on_message_callback=self._on_order_completed,
            auto_ack=False
        )
        self.channel.basic_consume(
            queue="notifications.order.shipped",
            on_message_callback=self._on_order_shipped,
            auto_ack=False
        )
        self.channel.basic_consume(
            queue="notifications.low_stock",
            on_message_callback=self._on_low_stock,
            auto_ack=False
        )
        self.channel.basic_consume(
            queue="notifications.payment.failed",
            on_message_callback=self._on_payment_failed,
            auto_ack=False
        )

        logger.info("Starting to consume messages...")
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            self.channel.stop_consuming()
            logger.info("Stopped consuming messages")

    def _on_order_completed(
        self,
        channel: BlockingChannel,
        method: Basic.Deliver,
        properties: BasicProperties,
        body: bytes
    ):
        """Handle order.completed event."""
        try:
            data = json.loads(body)
            logger.info(f"Received order.completed event: {data}")

            # Send order confirmation email
            asyncio.run(self._send_order_confirmation(data))

            channel.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            logger.exception(f"Error processing order.completed: {str(e)}")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def _on_order_shipped(
        self,
        channel: BlockingChannel,
        method: Basic.Deliver,
        properties: BasicProperties,
        body: bytes
    ):
        """Handle order.shipped event."""
        try:
            data = json.loads(body)
            logger.info(f"Received order.shipped event: {data}")

            # Send order shipped email
            asyncio.run(self._send_order_shipped(data))

            channel.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            logger.exception(f"Error processing order.shipped: {str(e)}")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def _on_low_stock(
        self,
        channel: BlockingChannel,
        method: Basic.Deliver,
        properties: BasicProperties,
        body: bytes
    ):
        """Handle inventory.low_stock event."""
        try:
            data = json.loads(body)
            logger.info(f"Received low_stock event: {data}")

            # Send low stock alert to admin
            asyncio.run(self._send_low_stock_alert(data))

            channel.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            logger.exception(f"Error processing low_stock: {str(e)}")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def _on_payment_failed(
        self,
        channel: BlockingChannel,
        method: Basic.Deliver,
        properties: BasicProperties,
        body: bytes
    ):
        """Handle payment.failed event."""
        try:
            data = json.loads(body)
            logger.info(f"Received payment.failed event: {data}")

            # Send payment failed email
            asyncio.run(self._send_payment_failed(data))

            channel.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            logger.exception(f"Error processing payment.failed: {str(e)}")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    async def _send_order_confirmation(self, data: dict):
        """Send order confirmation email."""
        db = SessionLocal()
        try:
            context = {
                "order_id": data.get("order_id"),
                "user_id": data.get("user_id"),
                "items": data.get("items", []),
                "total": data.get("total"),
                "subject": f"Order Confirmation - Order #{data.get('order_id')}"
            }

            subject, html_content = template_service.render_template(
                "order_confirmation",
                context
            )

            success, error = await email_service.send_email(
                to_email=data.get("user_email"),
                subject=subject,
                html_content=html_content
            )

            # Log notification
            notification = NotificationLog(
                user_id=data.get("user_id"),
                type="email",
                channel="sendgrid",
                recipient=data.get("user_email"),
                subject=subject,
                template="order_confirmation",
                status="sent" if success else "failed",
                error_message=error,
                sent_at=datetime.utcnow() if success else None
            )
            db.add(notification)
            db.commit()

        except Exception as e:
            logger.exception(f"Error sending order confirmation: {str(e)}")
        finally:
            db.close()

    async def _send_order_shipped(self, data: dict):
        """Send order shipped email."""
        db = SessionLocal()
        try:
            context = {
                "order_id": data.get("order_id"),
                "tracking_number": data.get("tracking_number"),
                "subject": "Your order has shipped!"
            }

            subject, html_content = template_service.render_template(
                "order_shipped",
                context
            )

            success, error = await email_service.send_email(
                to_email=data.get("user_email"),
                subject=subject,
                html_content=html_content
            )

            # Log notification
            notification = NotificationLog(
                user_id=data.get("user_id"),
                type="email",
                channel="sendgrid",
                recipient=data.get("user_email"),
                subject=subject,
                template="order_shipped",
                status="sent" if success else "failed",
                error_message=error,
                sent_at=datetime.utcnow() if success else None
            )
            db.add(notification)
            db.commit()

        except Exception as e:
            logger.exception(f"Error sending order shipped notification: {str(e)}")
        finally:
            db.close()

    async def _send_low_stock_alert(self, data: dict):
        """Send low stock alert to admin."""
        db = SessionLocal()
        try:
            context = {
                "product_id": data.get("product_id"),
                "product_name": data.get("product_name", "Unknown Product"),
                "current_quantity": data.get("current_quantity"),
                "subject": "[Admin] Low Stock Alert"
            }

            subject, html_content = template_service.render_template(
                "low_stock_alert",
                context
            )

            # Send to admin email (configured in settings)
            admin_email = data.get("admin_email", "admin@shophub.com")

            success, error = await email_service.send_email(
                to_email=admin_email,
                subject=subject,
                html_content=html_content
            )

            # Log notification
            notification = NotificationLog(
                type="email",
                channel="sendgrid",
                recipient=admin_email,
                subject=subject,
                template="low_stock_alert",
                status="sent" if success else "failed",
                error_message=error,
                sent_at=datetime.utcnow() if success else None
            )
            db.add(notification)
            db.commit()

        except Exception as e:
            logger.exception(f"Error sending low stock alert: {str(e)}")
        finally:
            db.close()

    async def _send_payment_failed(self, data: dict):
        """Send payment failed notification."""
        db = SessionLocal()
        try:
            context = {
                "order_id": data.get("order_id"),
                "reason": data.get("reason", "Unknown reason"),
                "subject": "Payment Failed - Action Required"
            }

            subject, html_content = template_service.render_template(
                "password_reset",  # Reusing password_reset template as generic
                context
            )

            success, error = await email_service.send_email(
                to_email=data.get("user_email"),
                subject=subject,
                html_content=html_content
            )

            # Log notification
            notification = NotificationLog(
                user_id=data.get("user_id"),
                type="email",
                channel="sendgrid",
                recipient=data.get("user_email"),
                subject=subject,
                template="password_reset",
                status="sent" if success else "failed",
                error_message=error,
                sent_at=datetime.utcnow() if success else None
            )
            db.add(notification)
            db.commit()

        except Exception as e:
            logger.exception(f"Error sending payment failed notification: {str(e)}")
        finally:
            db.close()

    def close(self):
        """Close connection to RabbitMQ."""
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            logger.info("Closed RabbitMQ connection")


def run_consumer():
    """Run the consumer (entry point for background process)."""
    consumer = NotificationConsumer()
    try:
        consumer.connect()
        consumer.start_consuming()
    except KeyboardInterrupt:
        logger.info("Consumer interrupted by user")
    finally:
        consumer.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    run_consumer()
