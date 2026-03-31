# Notification Service

FastAPI microservice for sending email and SMS notifications via SendGrid and Twilio.

## Features

- **Email Notifications** via SendGrid
  - Template-based emails with Jinja2
  - Order confirmations
  - Shipping notifications
  - Password reset emails
  - Low stock alerts

- **SMS Notifications** via Twilio
  - Direct SMS sending
  - Phone number validation

- **RabbitMQ Integration**
  - Async event-driven notifications
  - Consumes events from order, inventory, and payment services

- **Notification Logging**
  - PostgreSQL-based notification history
  - Track sent/failed notifications
  - User notification history

## Architecture

### Technology Stack

- **Framework**: FastAPI 0.109
- **Database**: PostgreSQL (notifications_db)
- **Email Provider**: SendGrid API
- **SMS Provider**: Twilio API
- **Template Engine**: Jinja2
- **Message Broker**: RabbitMQ (pika)
- **Python**: 3.11

### Service Port

- **8007** - HTTP API

## API Endpoints

### Email

```bash
POST /api/notifications/email
```

Send an email notification using a template.

**Request:**
```json
{
  "to": "user@example.com",
  "subject": "Order Confirmation",
  "template": "order_confirmation",
  "context": {
    "order_id": "123e4567-e89b-12d3-a456-426614174000",
    "items": [],
    "total": "99.99"
  },
  "user_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

### SMS

```bash
POST /api/notifications/sms
```

Send an SMS notification.

**Request:**
```json
{
  "to": "+12345678900",
  "message": "Your order has shipped!",
  "user_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

### Notification History

```bash
GET /api/notifications/user/{user_id}?limit=50&offset=0
```

Get notification history for a user.

```bash
GET /api/notifications/{notification_id}
```

Get specific notification details.

### Health Check

```bash
GET /health
```

## Database Schema

### notification_log

```sql
CREATE TABLE notification_log (
    id UUID PRIMARY KEY,
    user_id UUID,
    type VARCHAR(50) NOT NULL,        -- email, sms
    channel VARCHAR(50) NOT NULL,     -- sendgrid, twilio
    recipient VARCHAR(255) NOT NULL,
    subject VARCHAR(255),
    template VARCHAR(100),
    status VARCHAR(20) DEFAULT 'pending',  -- pending, sent, failed
    error_message TEXT,
    sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Email Templates

Templates are stored in the `templates/` directory:

- `order_confirmation.html` - Order confirmation email
- `order_shipped.html` - Shipping notification
- `password_reset.html` - Password reset request
- `low_stock_alert.html` - Admin alert for low inventory

### Template Context Variables

Each template expects specific context variables:

**order_confirmation.html:**
- `order_id` - Order ID
- `items` - List of order items
- `total` - Order total
- `subject` - Email subject

**order_shipped.html:**
- `order_id` - Order ID
- `tracking_number` - Shipment tracking number
- `subject` - Email subject

**password_reset.html:**
- `reset_token` - Password reset token
- `reset_code` - Alternative reset code
- `subject` - Email subject

**low_stock_alert.html:**
- `product_id` - Product ID
- `product_name` - Product name
- `current_quantity` - Current stock level
- `subject` - Email subject

## RabbitMQ Consumers

The service consumes events from multiple exchanges:

### Orders Exchange

- **Queue**: `notifications.order.completed`
  - **Routing Key**: `order.completed`
  - **Action**: Send order confirmation email

- **Queue**: `notifications.order.shipped`
  - **Routing Key**: `order.shipped`
  - **Action**: Send shipping notification

### Inventory Exchange

- **Queue**: `notifications.low_stock`
  - **Routing Key**: `inventory.low_stock`
  - **Action**: Send low stock alert to admin

### Payments Exchange

- **Queue**: `notifications.payment.failed`
  - **Routing Key**: `payment.failed`
  - **Action**: Send payment failure notification

## Configuration

Set these environment variables:

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/notifications_db

# SendGrid
SENDGRID_API_KEY=SG.xxxxx
SENDGRID_FROM_EMAIL=noreply@shophub.com
SENDGRID_FROM_NAME=ShopHub

# Twilio
TWILIO_ACCOUNT_SID=ACxxxxx
TWILIO_AUTH_TOKEN=xxxxx
TWILIO_FROM_PHONE=+12345678900

# RabbitMQ
RABBITMQ_URL=amqp://user:pass@host:5672/

# Service URLs
AUTH_SERVICE_URL=http://auth-service:8006

# Application
DEBUG=False
```

## Running the Service

### Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run database migrations (create tables)
python -c "from database import engine, Base; from models.database import NotificationLog; Base.metadata.create_all(bind=engine)"

# Start API server
python main.py

# Start RabbitMQ consumer (in separate terminal)
python services/consumer.py
```

### Docker

```bash
# Build image
docker build -t notification-service:latest .

# Run container
docker run -d \
  --name notification-service \
  -p 8007:8007 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/notifications_db \
  -e SENDGRID_API_KEY=SG.xxxxx \
  -e TWILIO_ACCOUNT_SID=ACxxxxx \
  -e TWILIO_AUTH_TOKEN=xxxxx \
  -e RABBITMQ_URL=amqp://user:pass@host:5672/ \
  notification-service:latest
```

### Docker Compose

```yaml
services:
  notification-service:
    build: .
    ports:
      - "8007:8007"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/notifications_db
      - SENDGRID_API_KEY=${SENDGRID_API_KEY}
      - TWILIO_ACCOUNT_SID=${TWILIO_ACCOUNT_SID}
      - TWILIO_AUTH_TOKEN=${TWILIO_AUTH_TOKEN}
      - RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
    depends_on:
      - postgres
      - rabbitmq
```

## Development Notes

### Adding New Templates

1. Create HTML template in `templates/` directory
2. Add template context to `template_service.py`
3. Update template list in this README

### Testing SendGrid/Twilio

For development, you can use:
- SendGrid sandbox mode (test emails without sending)
- Twilio trial account (limited SMS credits)

### Logging

The service logs to stdout with the following levels:
- `INFO` - Normal operations
- `ERROR` - Failed notifications
- `DEBUG` - Detailed debugging (when DEBUG=True)

## Production Considerations

1. **Rate Limiting**: Implement rate limiting for SendGrid/Twilio API calls
2. **Retry Logic**: Add exponential backoff for failed notifications
3. **Dead Letter Queue**: Configure DLQ in RabbitMQ for failed messages
4. **Monitoring**: Add metrics for notification success/failure rates
5. **Security**: Store API keys in secure secret management (AWS Secrets Manager, Vault)
6. **Email Validation**: Validate email addresses before sending
7. **Phone Validation**: Validate phone numbers (E.164 format) before SMS
8. **Templates**: Use responsive email templates for mobile
9. **Unsubscribe**: Implement unsubscribe functionality for marketing emails
10. **Compliance**: Ensure GDPR/CAN-SPAM compliance

## Dependencies

- **order-service**: Consumes order events
- **inventory-service**: Consumes inventory events
- **payment-service**: Consumes payment events

## API Documentation

When running, visit:
- Swagger UI: http://localhost:8007/docs
- ReDoc: http://localhost:8007/redoc

## License

Copyright © 2026 ShopHub. All rights reserved.
