# Order Management Service

## Overview
The **Order Management Service** is a microservice designed to handle order creation, tracking, and fulfillment processes. It integrates with other services such as inventory management, product scheduling, and order tracking to provide seamless order processing within a distributed system.

## Features
- Create new orders and validate stock availability with the Inventory Management Service.
- Handle orders with insufficient stock by publishing replenishment requests to RabbitMQ.
- Track the lifecycle of an order through various states using a centralized tracking mechanism.
- Query order details by client ID or order ID.

## Technologies Used
- **Python** (Flask, SQLAlchemy, Flask-Swagger)
- **PostgreSQL** (Database)
- **RabbitMQ** (Message broker)
- **Docker** (Containerization)
- **Flasgger** (API documentation)

## Setup and Installation

### Prerequisites
1. Python 3.11 or higher
2. PostgreSQL database
3. RabbitMQ message broker
4. Docker (optional for containerized deployment)

### Environment Variables
Define the following environment variables:

| Variable                 | Description                                  |
|--------------------------|----------------------------------------------|
| `POSTGRES_USER`          | PostgreSQL username                         |
| `POSTGRES_PASSWORD`      | PostgreSQL password                         |
| `POSTGRES_HOST`          | Host address of PostgreSQL server           |
| `POSTGRES_PORT`          | PostgreSQL server port                      |
| `POSTGRES_DB`            | Name of the PostgreSQL database             |
| `RABBITMQ_DEFAULT_USER`  | RabbitMQ username                           |
| `RABBITMQ_DEFAULT_PASS`  | RabbitMQ password                           |
| `RABBITMQ_DEFAULT_PORT`  | RabbitMQ server port                        |

### Steps

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <repository-folder>
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up the database:
   - Update the environment variables to point to your PostgreSQL instance.
   - Ensure the database tables are created by running the app:
     ```bash
     python main.py
     ```

4. Start the RabbitMQ server and configure credentials.

5. Run the service:
   ```bash
   flask run --host=0.0.0.0 --port=8001
   ```

### Docker Deployment

1. Build the Docker image:
   ```bash
   docker build -t order-management-service .
   ```

2. Run the container:
   ```bash
   docker run -p 8001:8001 --env-file .env order-management-service
   ```

## API Endpoints

### Order Service

#### Create Order
- **Endpoint**: `/order_service/create`
- **Method**: `POST`
- **Description**: Creates a new order and checks inventory availability.

#### Complete Order
- **Endpoint**: `/order_service/complete`
- **Method**: `POST`
- **Description**: Marks an order as fulfilled.

#### Get Client Orders
- **Endpoint**: `/order_service/orders/<client_id>`
- **Method**: `GET`
- **Description**: Retrieves all orders placed by a specific client.

#### Get Order Details
- **Endpoint**: `/order_service/<order_id>`
- **Method**: `GET`
- **Description**: Retrieves details of a specific order.

### Tracking Service

#### Update Tracking
- **Endpoint**: `/tracking/update/<order_id>`
- **Method**: `PUT`
- **Description**: Updates the tracking status of an order.

## Directory Structure
```
/app
├── Dockerfile
├── requirements.txt
├── main.py
├── utils.py
├── frontend/
└── README.md
```

## Key Components

### main.py
Defines the API routes, integrates with inventory and tracking services, and handles database interactions.

### utils.py
Contains utility functions such as `update_order_state` to manage order states and tracking updates.

### Database Model
The `Orders` model represents orders in the database with attributes:
- `order_id` (Primary Key)
- `client_id`
- `product_id`
- `quantity`
- `fulfilled`

### RabbitMQ Integration
Uses RabbitMQ to publish replenishment requests when stock is insufficient. Messages are published to the `production_queue`.

## Development Notes
- Ensure all services (Inventory, RabbitMQ, PostgreSQL) are running and accessible.
- Use Swagger documentation at `http://<host>:8001/apidocs` to explore and test endpoints.
- Log files are generated in the `DEBUG` level for detailed tracking during development.


