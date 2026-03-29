# Production Scheduling Service

The Production Scheduling Service is a Flask-based microservice designed to manage and schedule production tasks for a manufacturing system. It integrates with inventory and order management services to ensure seamless production scheduling and fulfillment.

## Features

- Schedule production tasks for orders.
- Assign tasks to available machines automatically.
- Manage machine states (`idle`, `busy`, etc.).
- Update inventory after production completion.
- Notify the order management system when production is complete.
- Exposes a RESTful API with Swagger documentation.

---

## Table of Contents

- [Technologies Used](#technologies-used)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Variables](#environment-variables)
  - [Running the Service](#running-the-service)
- [API Documentation](#api-documentation)
- [Docker Support](#docker-support)


---

## Technologies Used

- **Python 3.11**
- **Flask** for API development
- **Flasgger** for Swagger UI and API documentation
- **SQLAlchemy** for database interactions
- **PostgreSQL** for persistent storage
- **Docker** for containerization

---

## Getting Started

### Prerequisites

- Python 3.11 installed on your system
- Docker and Docker Compose (optional for containerized deployment)
- PostgreSQL database

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/production-scheduling-service.git
   cd production-scheduling-service
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up the database:
   - Ensure a PostgreSQL database is running.
   - Create a database for the service (e.g., `productionscheduling`).

4. Configure the environment variables in a `.env` file (see below).

---

### Environment Variables

Create a `.env` file in the root directory with the following variables:

```dotenv
POSTGRES_USER=<your_postgres_username>
POSTGRES_PASSWORD=<your_postgres_password>
POSTGRES_HOST=<your_postgres_host>
POSTGRES_PORT=5432
POSTGRES_DB=<your_database_name>
INVENTORY_SERVICE_URL=http://inventorymanagement:8000
ORDER_SERVICE_URL=http://ordermanagement:8001
PRODUCTION_SERVICE_URL=http://productionscheduling:8002
```

---

### Running the Service

1. Run the Flask application:
   ```bash
   python main.py
   ```

2. Access the Swagger UI for API documentation:
   - Visit `http://localhost:8002/apidocs` in your browser.

---

## API Documentation

### Base URL

The base URL for the service is:
```
http://localhost:8002
```

### Endpoints

1. **Schedule Production**  
   `POST /schedule/production`

   - **Description:** Schedule production for a specific product and quantity.
   - **Request Body:**
     ```json
     {
       "product_id": "string",
       "quantity": "integer",
       "order_id": "integer"
     }
     ```
   - **Responses:**
     - `200`: Production started successfully.
     - `400`: Invalid request data.
     - `503`: No machines available.
     - `500`: Internal server error.

2. **Swagger UI**  
   Access detailed API documentation at:  
   [http://localhost:8002/apidocs](http://localhost:8002/apidocs)

---

## Docker Support

You can run the service inside a Docker container.

### Build the Docker Image

```bash
docker build -t production-scheduling-service .
```

### Run the Docker Container

```bash
docker run -p 8002:8002 --env-file .env production-scheduling-service
```

---

## Project Structure

```
.
├── main.py                 # Flask application entry point
├── Dockerfile              # Docker configuration
├── requirements.txt        # Python dependencies
└── README.md               # Documentation
```



