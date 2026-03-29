# Queue Service for Production Scheduling

This service listens to a RabbitMQ queue (`production_queue`) and processes incoming messages to trigger production scheduling via an external service. It is built using Flask and interacts with RabbitMQ for message queueing and HTTP requests to external services.

## Features
- Connects to RabbitMQ to listen for messages.
- Processes production requests asynchronously using threading.
- Sends production scheduling requests to a specified external service (via HTTP).
- Handles retries for RabbitMQ connection with exponential backoff.
- Configurable URLs for other services (Inventory, Order, Production).

## Environment Variables

This service depends on several environment variables to function correctly:

- `RABBITMQ_DEFAULT_USER`: RabbitMQ username.
- `RABBITMQ_DEFAULT_PASS`: RabbitMQ password.
- `RABBITMQ_DEFAULT_PORT`: RabbitMQ port.
- `INVENTORY_SERVICE_URL`: URL for the Inventory service (default: `http://inventorymanagement:8000`).
- `ORDER_SERVICE_URL`: URL for the Order service (default: `http://ordermanagement:8001`).
- `PRODUCTION_SERVICE_URL`: URL for the Production service (default: `http://productionscheduling:8002`).

## Installation

1. Clone this repository.
2. Create a virtual environment (optional):
   ```bash
   python3 -m venv venv
3. Install dependencies:
    ```bash
    pip install -r requirements.txt

### Docker Setup
This service is containerized using Docker. You can build and run the service with the following commands:
1. Build the Docker image:
    ```bash
    docker build -t queue-service .
2. Run the Docker container:
    ```bash
    docker run -p 8004:8004 --env-file .env queue-service

The .env file should contain your environment variables, including RabbitMQ credentials and service URLs.

## Dependencies
- **Flask**
- **Requests**
- **SQLAlchemy**
- **Flask-SQLAlchemy**
- **psycopg2-binary**
- **pika (RabbitMQ client)**


## Usage
Once the service is up and running, it will listen to the production_queue in RabbitMQ for incoming messages. Each message should contain the following JSON structure:

    {
    "product_id": "123",
    "quantity": 10,
    "order_id": "order_456"
    }

The service processes the message by making an HTTP request to the PRODUCTION_SERVICE_URL to schedule production for the given product and quantity.

Troubleshooting :
- RabbitMQ Connection Issues
If the service is unable to connect to RabbitMQ, it will retry 10 times with a 10-second delay between each attempt. Ensure that RabbitMQ is running and accessible via the specified credentials and port.

Logs
- Logs are printed to the console, including information about the service status and any errors that occur during message processing. If an error occurs, the message will not be acknowledged, and the system will attempt to process it again.
