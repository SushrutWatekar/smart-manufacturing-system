from flask import Flask, jsonify, request, render_template
from flask_sqlalchemy import SQLAlchemy
import os
import logging
from flasgger import Swagger
from datetime import datetime
from sqlalchemy import text
import psutil
import time

# Initialize Flask app
app = Flask(__name__, static_folder='frontend', template_folder='frontend')

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Initialize Swagger
swagger = Swagger(app)

# Database configuration using environment variables
db_user = os.getenv("POSTGRES_USER")
db_password = os.getenv("POSTGRES_PASSWORD")
db_host = os.getenv("POSTGRES_HOST")
db_port = os.getenv("POSTGRES_PORT")
db_name = os.getenv("POSTGRES_DB")

# Flask SQLAlchemy database setup
app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# Database model for inventory
class Inventory(db.Model):
    __tablename__ = "inventory"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.Integer, nullable=False, unique=True)
    quantity = db.Column(db.Integer, nullable=False, default=0)

# Ensure the inventory table is created in the database
with app.app_context():
  db.create_all()
  if Inventory.query.count() == 0:
      sample_products = [Inventory(product_id=1, quantity=100), Inventory(product_id=2, quantity=100), Inventory(product_id=3, quantity=100)]
      db.session.bulk_save_objects(sample_products)
      db.session.commit()

#health check-points
def check_database():
    """Check database connectivity and response time."""
    try:
        start_time = time.time()
        # Execute a simple query to check database connection
        with db.engine.connect() as connection:
            connection.execute(text('SELECT 1'))
        response_time = round((time.time() - start_time) * 1000, 2)  # Convert to milliseconds
        return True, response_time
    except Exception as e:
        logging.error(f"Database health check failed: {e}")
        return False, 0

def get_system_health():
    """Get basic system metrics."""
    return {
        "cpu_usage": round(psutil.cpu_percent(), 2),
        "memory_usage": round(psutil.virtual_memory().percent, 2),
        "disk_usage": round(psutil.disk_usage('/').percent, 2)
    }

# API endpoint to check inventory stock
@app.route("/inventory/check", methods=["POST"])
def check_inventory():
    """
    Check inventory availability
    ---
    tags:
      - Inventory
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            product_id:
              type: string
              description: The ID of the product to check.
            quantity:
              type: integer
              description: The quantity of the product to check.
          required:
            - product_id
            - quantity
    responses:
      200:
        description: Success
        schema:
          type: object
          properties:
            message:
              type: string
              description: Message indicating availability.
            available:
              type: boolean
              description: True if sufficient quantity is available, false otherwise.
      400:
        description: Invalid data
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message.
      404:
        description: Product not found
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message.
    """
    data = request.get_json()
    logging.debug("Received request to check inventory: %s", data)

    if not data or "product_id" not in data or "quantity" not in data:
        logging.warning("Invalid data received for inventory check.")
        return jsonify({"error": "Invalid data"}), 400

    product_id = data["product_id"]
    requested_quantity = data["quantity"]

    product = Inventory.query.filter_by(product_id=product_id).first()

    if not product:
        logging.warning("Product not found in inventory: product_id=%s", product_id)
        return jsonify({"error": "Product not found"}), 404

    if product.quantity >= requested_quantity:
        logging.info("Sufficient stock available: product_id=%s, available_quantity=%s", product_id, product.quantity)
        return jsonify({"message": "Sufficient quantity available", "available": True}), 200
    else:
        logging.info("Insufficient stock: product_id=%s, requested_quantity=%s, available_quantity=%s", product_id, requested_quantity, product.quantity)
        return jsonify({"message": "Insufficient quantity", "available": False}), 200

# API endpoint to update inventory stock
@app.route("/inventory/update", methods=["POST"])
def update_inventory():
    """
    Update inventory stock
    ---
    tags:
      - Inventory
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            product_id:
              type: string
              description: The ID of the product to update.
            quantity:
              type: integer
              description: The quantity to update. Positive for adding stock, negative for removing stock.
          required:
            - product_id
            - quantity
    responses:
      200:
        description: Success
        schema:
          type: object
          properties:
            message:
              type: string
              description: Success message.
            product_id:
              type: string
              description: The ID of the updated product.
            new_quantity:
              type: integer
              description: The new quantity of the product in inventory.
      400:
        description: Invalid data or insufficient stock
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message.
      404:
        description: Product not found
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message.
    """
    data = request.get_json()
    logging.debug("Received request to update inventory: %s", data)

    if not data or "product_id" not in data or "quantity" not in data:
        logging.warning("Invalid data received for inventory update.")
        return jsonify({"error": "Invalid data"}), 400

    product_id = data["product_id"]
    update_quantity = data["quantity"]

    product = Inventory.query.filter_by(product_id=product_id).first()

    if not product:
        logging.warning("Product not found in inventory for update: product_id=%s", product_id)
        return jsonify({"error": "Product not found"}), 404

    # Update the quantity
    product.quantity += update_quantity  # (quantity = -ve -> if order is placed)

    if product.quantity < 0:
        logging.error("Stock cannot be negative after update: product_id=%s, update_quantity=%s, current_quantity=%s", product_id, update_quantity, product.quantity)
        return jsonify({"error": "Insufficient stock after update"}), 400

    db.session.commit()
    logging.info("Inventory updated successfully: product_id=%s, new_quantity=%s", product_id, product.quantity)
    return jsonify({"message": "Inventory updated successfully", "product_id": product_id, "new_quantity": product.quantity}), 200

# API endpoint to add a new product to inventory
@app.route("/inventory/add", methods=["POST"])
def add_product():
    """
    Add a new product to the inventory
    ---
    tags:
      - Inventory
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            product_id:
              type: string
              description: The ID of the product to add.
            quantity:
              type: integer
              description: The quantity of the product to add.
          required:
            - product_id
            - quantity
    responses:
      200:
        description: Success
        schema:
          type: object
          properties:
            message:
              type: string
              description: Success message.
            product_id:
              type: string
              description: The ID of the added product.
            quantity:
              type: integer
              description: The quantity of the added product.
      400:
        description: Invalid data or product already exists
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message.
    """
    data = request.get_json()
    logging.debug("Received request to add product: %s", data)

    if not data or "product_id" not in data or "quantity" not in data:
        logging.warning("Invalid data received for adding product.")
        return jsonify({"error": "Invalid data"}), 400

    product_id = data["product_id"]
    quantity = data["quantity"]

    # Check if the product already exists
    existing_product = Inventory.query.filter_by(product_id=product_id).first()

    if existing_product:
        logging.warning("Product already exists in inventory: product_id=%s", product_id)
        return jsonify({"error": "Product already exists"}), 400

    # Add the new product
    new_product = Inventory(product_id=product_id, quantity=quantity)
    db.session.add(new_product)
    db.session.commit()

    logging.info("Product added successfully: product_id=%s, quantity=%s", product_id, quantity)
    return jsonify({"message": "Product added successfully", "product_id": product_id, "quantity": quantity}), 200

# API endpoint to delete a product from inventory
@app.route("/inventory/delete", methods=["POST"])
def delete_product():
    """
    Delete a product from the inventory
    ---
    tags:
      - Inventory
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            product_id:
              type: string
              description: The ID of the product to delete.
          required:
            - product_id
    responses:
      200:
        description: Success
        schema:
          type: object
          properties:
            message:
              type: string
              description: Success message.
            product_id:
              type: string
              description: The ID of the deleted product.
      400:
        description: Invalid data
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message.
      404:
        description: Product not found
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message.
    """
    data = request.get_json()
    logging.debug("Received request to delete product: %s", data)

    if not data or "product_id" not in data:
        logging.warning("Invalid data received for deleting product.")
        return jsonify({"error": "Invalid data"}), 400

    product_id = data["product_id"]

    product = Inventory.query.filter_by(product_id=product_id).first()

    if not product:
        logging.warning("Product not found in inventory for deletion: product_id=%s", product_id)
        return jsonify({"error": "Product not found"}), 404

    # Delete the product
    db.session.delete(product)
    db.session.commit()

    logging.info("Product deleted successfully: product_id=%s", product_id)
    return jsonify({"message": "Product deleted successfully", "product_id": product_id}), 200


# API endpoint to get all products from inventory
@app.route("/inventory/all", methods=["GET"])
def get_all_products():
    """
    Get all products in the inventory
    ---
    tags:
      - Inventory
    responses:
      200:
        description: Success
        schema:
          type: object
          properties:
            products:
              type: array
              items:
                type: object
                properties:
                  product_id:
                    type: string
                    description: The ID of the product.
                  quantity:
                    type: integer
                    description: The quantity of the product.
      404:
        description: No products found
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message.
    """
    # Query the database for all products in the inventory
    products = Inventory.query.all()

    # If no products found
    if not products:
        logging.warning("No products found in inventory.")
        return jsonify({"error": "No products found"}), 404

    # Prepare a list of products
    product_list = []
    for product in products:
        product_list.append({
            "product_id": product.product_id,
            "quantity": product.quantity
        })

    logging.info("Fetched all products successfully.")
    return jsonify({"products": product_list}), 200


@app.route("/health", methods=["GET"])
def health_check():
    """
    Basic health check endpoint
    ---
    tags:
      - Health
    responses:
      200:
        description: Service is healthy
      503:
        description: Service is unhealthy
    """
    try:
        # Check database connectivity
        db_healthy, db_response_time = check_database()
        
        health_status = {
            "status": "healthy" if db_healthy else "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": {
                "connected": db_healthy,
                "response_time_ms": db_response_time
            }
        }
        
        status_code = 200 if db_healthy else 503
        return jsonify(health_status), status_code
    except Exception as e:
        logging.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }), 503

@app.route("/health/detailed", methods=["GET"])
def detailed_health_check():
    """
    Detailed health check endpoint with system metrics
    ---
    tags:
      - Health
    responses:
      200:
        description: Detailed health information
      503:
        description: Service is unhealthy
    """
    try:
        # Check database
        db_healthy, db_response_time = check_database()
        
        # Get system metrics
        system_metrics = get_system_health()
        
        # Get application metrics
        app_metrics = {
            "inventory_count": Inventory.query.count(),
            "last_checked": datetime.utcnow().isoformat()
        }
        
        health_status = {
            "status": "healthy" if db_healthy else "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": {
                "connected": db_healthy,
                "response_time_ms": db_response_time
            },
            "system": system_metrics,
            "application": app_metrics
        }
        
        status_code = 200 if db_healthy else 503
        return jsonify(health_status), status_code
    except Exception as e:
        logging.error(f"Detailed health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }), 503

# Run the Flask application
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
