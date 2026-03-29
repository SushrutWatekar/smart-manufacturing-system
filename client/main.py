from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import os
import requests
from flasgger import Swagger
from flask_cors import CORS

# Initialize Flask app
app = Flask(__name__)

# Database configuration using environment variables
db_user = os.getenv("POSTGRES_USER")
db_password = os.getenv("POSTGRES_PASSWORD")
db_host = os.getenv("POSTGRES_HOST")
db_port = os.getenv("POSTGRES_PORT")
db_name = os.getenv("POSTGRES_DB")

# Configure SQLAlchemy
app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# Initialize Swagger
swagger = Swagger(app)

# Allow CORS for all routes and origins
CORS(app)

# Service URLs
ORDER_SERVICE_URL = "http://ordermanagement:8001/order_service/create"
TRACKING_SERVICE_URL = "http://ordertracking:8003/tracking"


# Client Model
class Client(db.Model):
    __tablename__ = "clients"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)


# Initialize database and add sample data
with app.app_context():
    db.create_all()
    if Client.query.count() == 0:
        sample_clients = [Client(name="John", email="john@example.com"), Client(name="Jane", email="jane@example.com"), Client(name="Mike", email="mike@example.com")]
        db.session.bulk_save_objects(sample_clients)
        db.session.commit()


# API Endpoints
@app.route("/create_user", methods=["POST"])
def create_user():
    """
    Create a new user
    ---
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - name
            - email
          properties:
            name:
              type: string
            email:
              type: string
    responses:
      201:
        description: User created successfully
      400:
        description: Name and email are required
    """
    data = request.get_json()
    name = data.get("name")
    email = data.get("email")

    if not all([name, email]):
        return jsonify({"error": "Name and email are required"}), 400

    new_client = Client(name=name, email=email)
    db.session.add(new_client)
    db.session.commit()

    return jsonify({"message": "User created successfully", "client_id": new_client.id}), 201


@app.route("/clients", methods=["GET"])
def get_clients():
    """
    Retrieve all clients
    ---
    responses:
      200:
        description: A list of clients
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: integer
              name:
                type: string
              email:
                type: string
    """
    clients = Client.query.all()
    client_list = [{"id": client.id, "name": client.name, "email": client.email} for client in clients]
    return jsonify(client_list), 200


@app.route("/delete_client/<int:client_id>", methods=["DELETE"])
def delete_client(client_id):
    """
    Delete a client by ID
    ---
    parameters:
      - in: path
        name: client_id
        required: true
        type: integer
    responses:
      200:
        description: Client deleted successfully
      404:
        description: Client not found
    """
    client = Client.query.get(client_id)
    if not client:
        return jsonify({"error": "Client not found"}), 404

    db.session.delete(client)
    db.session.commit()
    return jsonify({"message": "Client deleted successfully"}), 200


@app.route("/update_client/<int:client_id>", methods=["PUT"])
def update_client(client_id):
    """
    Update client information by ID
    ---
    parameters:
      - in: path
        name: client_id
        required: true
        type: integer
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
            email:
              type: string
    responses:
      200:
        description: Client updated successfully
      404:
        description: Client not found
    """
    data = request.get_json()
    client = Client.query.get(client_id)

    if not client:
        return jsonify({"error": "Client not found"}), 404

    if "name" in data:
        client.name = data["name"]
    if "email" in data:
        client.email = data["email"]

    db.session.commit()
    return jsonify({"message": "Client updated successfully"}), 200


@app.route("/client/<int:client_id>", methods=["GET"])
def get_client(client_id):
    """
    Retrieve client data by ID
    ---
    parameters:
      - in: path
        name: client_id
        required: true
        type: integer
    responses:
      200:
        description: Client data retrieved successfully
        schema:
          type: object
          properties:
            id:
              type: integer
            name:
              type: string
            email:
              type: string
      404:
        description: Client not found
    """
    client = Client.query.get(client_id)
    if not client:
        return jsonify({"error": "Client not found"}), 404

    return jsonify({"id": client.id, "name": client.name, "email": client.email}), 200


@app.route("/search_clients", methods=["GET"])
def search_clients():
    """
    Search clients by name or email
    ---
    parameters:
      - in: query
        name: query
        required: true
        type: string
    responses:
      200:
        description: A list of matching clients
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: integer
              name:
                type: string
              email:
                type: string
      400:
        description: Query parameter is required
    """
    query = request.args.get("query")
    if not query:
        return jsonify({"error": "Query parameter is required"}), 400

    clients = Client.query.filter((Client.name.ilike(f"%{query}%")) | (Client.email.ilike(f"%{query}%"))).all()

    client_list = [{"id": client.id, "name": client.name, "email": client.email} for client in clients]

    return jsonify(client_list), 200


@app.route("/order_service/create", methods=["POST"])
def create_order():
    """
    Create an order and track its status
    ---
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - client_id
            - quantity
            - product_id
          properties:
            client_id:
              type: integer
            quantity:
              type: integer
            product_id:
              type: integer
    responses:
      201:
        description: Order placed successfully with tracking information
      400:
        description: Client ID, quantity, and product ID are required
      404:
        description: Client ID does not exist
      500:
        description: Error communicating with order service
    """
    data = request.get_json()
    client_id = data.get("client_id")
    quantity = data.get("quantity")
    product_id = data.get("product_id")

    # Validate required fields
    if not all([client_id, quantity, product_id]):
        return jsonify({"error": "Client ID, quantity, and product ID are required"}), 400

    # Verify client exists
    client = Client.query.get(client_id)
    if not client:
        return jsonify({"error": "Client ID does not exist"}), 404

    # Prepare order payload
    payload = {"client_id": client_id, "quantity": quantity, "product_id": product_id}

    try:
        # Place the order
        order_response = requests.post(ORDER_SERVICE_URL, json=payload)
        order_data = order_response.json()

        if order_response.status_code in [200, 201]:
            return jsonify({"message": "Order placed successfully", "order_response": order_data}), order_response.status_code
        else:
            return jsonify({"error": "Order placement failed", "details": order_data}), order_response.status_code

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


import socket


@app.route("/debug", methods=["GET"])
def debug_connection():
    """
    Debug endpoint to test service connectivity
    """
    try:
        order_management_ip = socket.gethostbyname("ordermanagement")
        tracking_ip = socket.gethostbyname("ordertracking")
        return jsonify({"order_management_ip": order_management_ip, "tracking_ip": tracking_ip}), 200
    except socket.gaierror as e:
        return jsonify({"error": str(e)}), 500


@app.route("/track_order/<int:order_id>", methods=["GET"])
def track_order(order_id):
    """
    Track an order's status and timing
    ---
    parameters:
      - in: path
        name: order_id
        required: true
        type: integer
    responses:
      200:
        description: Order tracking information retrieved successfully
      404:
        description: Order tracking not found
      500:
        description: Error communicating with tracking service
    """
    try:
        response = requests.get(f"{TRACKING_SERVICE_URL}/{order_id}")
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Failed to retrieve tracking information: {str(e)}"}), 500


#view all order form perticular client
@app.route("/client/<int:client_id>/orders", methods=["GET"])
def get_client_orders(client_id):
    """
    Retrieve all orders for a specific client by filtering orders from the order service.
    """
    try:
        # Assuming order_service has an endpoint to get all orders
        order_service_url = f"http://ordermanagement:8001/order_service/orders/{client_id}"
        response = requests.get(order_service_url)
        response.raise_for_status()
        orders = response.json()

        # Filter orders by client_id
        client_orders = [order for order in orders if order["client_id"] == client_id]

        return jsonify(client_orders), 200
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Failed to fetch orders"}), 500



# Run the Flask application
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8010, debug=True)
