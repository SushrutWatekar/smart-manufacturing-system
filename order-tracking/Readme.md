# Order Tracking Microservice

## Overview

The Order Tracking Microservice enables tracking and monitoring of orders, from placement to fulfillment. It integrates with inventory and order management services to provide detailed insights into order processing and status updates.

## Features
- **Order Tracking**: Create and retrieve tracking information for orders.
- **Inventory Check**: Validate product availability and calculate processing times.
- **Order Status Updates**: Modify tracking status for in-progress orders.
- **API Endpoints**: Exposes RESTful APIs for seamless integration.

## Prerequisites

Ensure the following are installed on your system:
- Python 3.9 or later
- PostgreSQL database
- Docker (optional for containerized deployment)

## Setup Instructions

### Environment Variables
Create a `.env` file in the root directory and define the following variables:

```plaintext
POSTGRES_USER=<your_db_username>
POSTGRES_PASSWORD=<your_db_password>
POSTGRES_HOST=<db_host>
POSTGRES_PORT=<db_port>
POSTGRES_DB=<database_name>
```

### Installation

1. Clone the repository:
   ```bash
   git clone <repository_url>
   cd order-tracking
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Initialize the database:
   ```bash
   python -c "from main import db; db.create_all()"
   ```

### Running the Service

#### Locally
Start the Flask application:
```bash
python main.py
```

#### Using Docker

1. Build the Docker image:
   ```bash
   docker build -t order-tracking .
   ```

2. Run the Docker container:
   ```bash
   docker run -d -p 8004:8004 --env-file .env order-tracking
   ```

## API Endpoints

### Create Order Tracking
**POST** `/tracking/create`

- **Description**: Creates tracking information for an order.
- **Request Body**:
  ```json
  {
    "order_id": 123
  }
  ```
- **Response**:
  ```json
  {
    "order_id": 123,
    "status": "ORDER_PLACED",
    "order_placed_at": "01-Jan-2025 12:00:00 UTC",
    "estimated_completion_at": "01-Jan-2025 12:10:00 UTC",
    ...
  }
  ```

### Get Order Tracking
**GET** `/tracking/<order_id>`

- **Description**: Retrieves tracking details for a specific order.
- **Response**:
  ```json
  {
    "order_id": 123,
    "status": "ORDER_PROCESSING",
    ...
  }
  ```

### Update Order Tracking
**PUT** `/tracking/update/<order_id>`

- **Description**: Updates the tracking status of an order.
- **Request Body**:
  ```json
  {
    "status": "FULFILLED"
  }
  ```
- **Response**:
  ```json
  {
    "order_id": 123,
    "status": "FULFILLED",
    ...
  }
  ```

### Order Details
**GET** `/order_service/<order_id>`

- **Description**: Fetches order details such as product ID and quantity.
- **Response**:
  ```json
  {
    "data": {
      "order_id": 123,
      "product_id": 456,
      "quantity": 10
    }
  }
  ```

## Dockerfile
```dockerfile
# Use Python slim image for smaller size
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the main application file into the container
COPY main.py .

# Expose the application port
EXPOSE 8004

# Define the default command to run the application
CMD ["python", "main.py"]
```

## Requirements File
```plaintext
requests==2.26.0
flask==2.2.5
flask-sqlalchemy==3.0.5
werkzeug==2.2.3
psycopg2-binary==2.9.8
python-dotenv==1.0.0
```

## Logging and Debugging
- Logs are configured to output to the console with `DEBUG` level.
- Use `logging` to trace issues during API calls and database transactions.

## Testing
- Use tools like Postman or curl to interact with the endpoints during testing. Ensure the database is properly configured before running the application.
- Use Swagger documentation at `http://<host>:8004/apidocs` to explore and test endpoints.
