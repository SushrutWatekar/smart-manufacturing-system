import datetime
import logging
from flask import Flask, request, jsonify
import requests
from flask_sqlalchemy import SQLAlchemy
import os
import pika
import json
from utils import update_order_state, ORDER_STATES
from flasgger import Swagger

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

app = Flask(__name__, static_folder='frontend', template_folder='frontend')

# Inventory service URL for stock checks and updates
INVENTORY_SERVICE_URL = "http://inventorymanagement:8000"
PRODUCT_SCHEDULING_URL = "http://productscheduling:8002"

# Database configuration
db_user = os.getenv("POSTGRES_USER")
db_password = os.getenv("POSTGRES_PASSWORD")
db_host = os.getenv("POSTGRES_HOST")
db_port = os.getenv("POSTGRES_PORT")
db_name = os.getenv("POSTGRES_DB")

# RabbitMQ configuration
rabbitmq_user = os.getenv("RABBITMQ_DEFAULT_USER")
rabbitmq_pass = os.getenv("RABBITMQ_DEFAULT_PASS")
rabbitmq_host = "rabbitmq"
rabbitmq_port = os.getenv("RABBITMQ_DEFAULT_PORT")

# Initialize Swagger
swagger = Swagger(app)

# RabbitMQ connection parameters
credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_pass)
parameters = pika.ConnectionParameters(rabbitmq_host, rabbitmq_port, "/", credentials=credentials)

# Flask SQLAlchemy database setup
app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


# Database model for orders
class Orders(db.Model):
    __tablename__ = "orders"
    order_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    client_id = db.Column(db.Integer, nullable=False)
    product_id = db.Column(db.Integer, nullable=False)
    fullfiled = db.Column(db.Boolean, default=False)
    quantity = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {
            "order_id": self.order_id,
            "client_id": self.client_id,
            "product_id": self.product_id,
            "fullfiled": self.fullfiled,
            "quantity": self.quantity,
        }


# Ensure the orders table is created
with app.app_context():
  logging.debug("Creating database tables if they don't exist.")
  db.create_all()



@app.route("/order_service/create", methods=["POST"])
def create_order():
    """
    Create an order
    ---
    tags:
      - Order Service
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            client_id:
              type: string
              description: The ID of the client placing the order.
            product_id:
              type: string
              description: The ID of the product to order.
            quantity:
              type: integer
              description: The quantity of the product to order.
          required:
            - client_id
            - product_id
            - quantity
    responses:
      201:
        description: Order placed successfully
        schema:
          type: object
          properties:
            message:
              type: string
            data:
              type: object
      200:
        description: Order created but stock insufficient
        schema:
          type: object
          properties:
            message:
              type: string
            data:
              type: object
      400:
        description: Invalid data
        schema:
          type: object
          properties:
            error:
              type: string
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            error:
              type: string
    """
    logging.debug("Received request to create an order.")
    data = request.get_json()
    logging.debug(f"Request payload: {data}")

    if not data or "client_id" not in data or "quantity" not in data or "product_id" not in data:
        logging.warning("Invalid data in request payload.")
        return jsonify({"error": "Invalid data"}), 400

    product_id, quantity, client_id = data["product_id"], data["quantity"], data["client_id"]

    try:
        # Check inventory
        logging.debug("Checking inventory availability.")
        inventory_response = requests.post(
            f"{INVENTORY_SERVICE_URL}/inventory/check", json={"product_id": product_id, "quantity": quantity}
        )
        inventory_response.raise_for_status()
        inventory_data = inventory_response.json()

        if inventory_data.get("available"):
            logging.debug("Inventory available. Proceeding to create the order.")
            new_order = Orders(client_id=client_id, product_id=product_id, quantity=quantity, fullfiled=True)
            db.session.add(new_order)
            db.session.commit()

            update_order_state("ORDER_PLACED", new_order.to_dict(), datetime.datetime.utcnow(), True)

            logging.debug("Updating inventory to deduct the ordered quantity.")
            inventory_update_response = requests.post(
                f"{INVENTORY_SERVICE_URL}/inventory/update", json={"product_id": product_id, "quantity": -quantity}
            )
            if inventory_update_response.status_code != 200:
                logging.error("Failed to update inventory.")
                update_order_state("INVENTORY_CHECK_FAILED", new_order.to_dict(), datetime.datetime.utcnow(), False)
                return jsonify({"error": "Failed to update inventory"}), 500

            update_order_state("INVENTORY_CHECK_SUCCESSFUL", new_order.to_dict(), datetime.datetime.utcnow(), False)
            logging.info("Order created successfully.")
            return jsonify({"message": "Order placed successfully", "order_id": new_order.order_id, "client_id": client_id, "product_id": product_id, "quantity": quantity, "fullfiled": True}), 201
        else:
            logging.warning("Insufficient stock. Creating an unfulfilled order.")
            new_order = Orders(client_id=client_id, product_id=product_id, quantity=quantity, fullfiled=False)
            db.session.add(new_order)
            db.session.commit()

            publish_to_rabbitmq(product_id, quantity, new_order.order_id)
            update_order_state("ORDER_UNFULFILLED", new_order.to_dict(), datetime.datetime.utcnow(), True)
            return jsonify({"message": "Insufficient stock. Replenishment requested.", "order_id": new_order.order_id, "client_id": client_id, "product_id": product_id, "quantity": quantity, "fullfiled": False}), 200

    except requests.RequestException as e:
        logging.error(f"Error contacting Inventory Management service: {e}")
        return jsonify({"error": "Failed to check inventory"}), 500
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        logging.exception(e)
        return jsonify({"error": "An error occurred"}), 500



@app.route("/order_service/complete", methods=["POST"])
def complete_order():
    """
    Complete an order
    ---
    tags:
      - Order Service
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            order_id:
              type: integer
              description: The ID of the order to complete.
          required:
            - order_id
    responses:
      200:
        description: Order completed successfully
        schema:
          type: object
          properties:
            message:
              type: string
            data:
              type: object
      404:
        description: Order not found
        schema:
          type: object
          properties:
            error:
              type: string
      400:
        description: Invalid data
        schema:
          type: object
          properties:
            error:
              type: string
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            error:
              type: string
    """
    logging.debug("Received request to complete an order.")
    data = request.get_json()
    logging.debug(f"Request payload: {data}")

    if not data or "order_id" not in data:
        logging.warning("Order ID is required.")
        return jsonify({"error": "Invalid data"}), 400

    try:
        # Retrieve the order
        order = Orders.query.get(data["order_id"])
        if not order:
            logging.warning(f"Order ID {data['order_id']} not found.")
            return jsonify({"error": "Order not found"}), 404

        # Mark the order as fulfilled
        order.fullfiled = True
        db.session.commit()

        # Update the tracking step and state using update_order_state
        logging.debug(f"Updating tracking for order ID {order.order_id} to 'Order Fulfillment'.")
        update_order_state("ORDER_FULFILLED", order.to_dict(), datetime.datetime.utcnow(), False)

        return jsonify({"message": "Order completed successfully.", "data": order.to_dict()}), 200

    except Exception as e:
        logging.error(f"Error completing order: {e}")
        return jsonify({"error": "Failed to complete order"}), 500

@app.route("/tracking/update/<int:order_id>", methods=["PUT"])
def update_tracking(order_id):

    """
    Update order tracking
    ---
    tags:
      - Tracking
    parameters:
      - in: path
        name: order_id
        required: true
        type: integer
        description: sends data to order-tracking service
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            status:
              type: string
              description: The status of the tracking step.
            step:
              type: string
              description: The tracking step to update.
          required:
            - status
            - step
    responses:
      200:
        description: Tracking updated successfully
        schema:
          type: object
      400:
        description: Invalid data
        schema:
          type: object
          properties:
            error:
              type: string
      404:
        description: Tracking or step not found
        schema:
          type: object
          properties:
            error:
              type: string
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            error:
              type: string
    """
    try:
        # 1. Get the update data from request
        data = request.get_json()
        if not data or "status" not in data or "step" not in data:
            return jsonify({"error": "Status and Step are required"}), 400

        # 2. Forward the update to Order Tracking service
        update_data = {
            "status": data["status"],
            "step": data["step"],
            "datetime": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 3. Send to Order Tracking service
        tracking_response = requests.put(
            f"http://ordertracking:8003/tracking/update/{order_id}",
            json=update_data
        )

        # 4. Return the response from tracking service
        if tracking_response.status_code != 200:
            logging.error(f"Failed to update tracking. Status code: {tracking_response.status_code}")
            logging.error(f"Response: {tracking_response.text}")
            return jsonify({"error": "Failed to update tracking"}), tracking_response.status_code

        return jsonify(tracking_response.json()), 200

    except Exception as e:
        logging.error(f"Error updating tracking: {e}")
        return jsonify({"error": f"Failed to update tracking: {str(e)}"}), 500


def publish_to_rabbitmq(product_id, quantity, order_id):
    try:
        logging.debug("Publishing replenishment request to RabbitMQ.")
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        channel.queue_declare(queue="production_queue")
        channel.basic_publish(
            exchange="", routing_key="production_queue", body=json.dumps({"product_id": product_id, "quantity": quantity, "order_id": order_id})
        )
        connection.close()
        logging.info("Replenishment request published successfully.")
    except Exception as e:
        logging.error(f"Failed to publish to RabbitMQ: {e}")
        raise

@app.route("/order_service/orders/<int:client_id>", methods=["GET"])
def get_client_orders(client_id):
    """
    Orders based on client_id
    ---
    tags:
      - Tracking
    parameters:
      - in: path
        name: client_id
        required: true
        type: integer
        description: The ID of the client we are tracking
        schema:
          type: object
          properties:
            status:
              type: string
              description: The status of the tracking step.
            step:
              type: string
              description: The tracking step to update.
          required:
            - status
            - step
    responses:
      200:
        description: Tracking updated successfully
        schema:
          type: object
      400:
        description: Invalid data
        schema:
          type: object
          properties:
            error:
              type: string
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            error:
              type: string
    """
    try:
        orders = Orders.query.filter_by(client_id=client_id).all()
        if not orders:
            return jsonify([]), 200
        return jsonify([order.to_dict() for order in orders]), 200
    except Exception as e:
        logging.error(f"Error retrieving orders: {e}")
        return jsonify({"error": "Failed to retrieve orders"}), 500

@app.route("/order_service/<int:order_id>", methods=["GET"])
def get_order_details(order_id):
    """
    Get order details
    ---
    tags:
      - Order Service
    parameters:
      - in: path
        name: order_id
        required: true
        type: integer
        description: The ID of the order to retrieve
    responses:
      200:
        description: Order details retrieved successfully
      404:
        description: Order not found
      500:
        description: Internal server error
    """
    try:
        # Retrieve the order directly using the order_id from the path
        order = Orders.query.get(order_id)
        if not order:
            logging.warning(f"Order ID {order_id} not found.")
            return jsonify({"error": "Order not found"}), 404
            
        return jsonify({
            "data": {
                "order_id": order.order_id,
                "client_id": order.client_id,
                "product_id": order.product_id,
                "quantity": order.quantity,
                "fullfiled": order.fullfiled
            }
        }), 200
            
    except Exception as e:
        logging.error(f"Error fetching order details: {e}")
        return jsonify({"error": "Failed to fetch order details"}), 500


if __name__ == "__main__":
    logging.debug("Starting Flask application.")
    app.run(host="0.0.0.0", port=8001, debug=True)