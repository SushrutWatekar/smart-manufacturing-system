from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import os
import logging
from datetime import datetime, timedelta
import requests
import time
from dotenv import load_dotenv
from flasgger import Swagger
# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Database configuration
db_user = os.environ.get('POSTGRES_USER')
db_password = os.environ.get('POSTGRES_PASSWORD')
db_host = os.environ.get('POSTGRES_HOST')
db_port = os.environ.get('POSTGRES_PORT')
db_name = os.environ.get('POSTGRES_DB')

# Configure the database URI
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

swagger = Swagger(app)


# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class OrderTracking(db.Model):

    __tablename__ = 'order_tracking'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.Integer, unique=True, nullable=False)
    status = db.Column(db.String(50), nullable=False, default='ORDER_PLACED')
    placed_time = db.Column(db.DateTime, nullable=False)
    estimated_completion_time = db.Column(db.DateTime, nullable=False)
    inventory_check_time = db.Column(db.Float, nullable=False)
    
    def to_dict(self):
        current_time = datetime.utcnow()
        time_since_order = (current_time - self.placed_time).total_seconds()
        time_until_completion = (self.estimated_completion_time - current_time).total_seconds()

        # Check inventory availability and get quantity at the time of request
        inventory_status = check_inventory_availability(self.order_id)
        inventory_available = inventory_status['available']
        order_quantity = inventory_status['quantity']
        actual_inventory_check_time = self.inventory_check_time

        return {
            "order_id": self.order_id,
            "status": self.status,
            "order_placed_at": self.format_datetime(self.placed_time),
            "estimated_completion_at": self.format_datetime(self.estimated_completion_time),
            "current_time": self.format_datetime(current_time),
            "time_metrics": self.calculate_time_metrics(time_since_order, time_until_completion, 
                                                      inventory_available, order_quantity, 
                                                      actual_inventory_check_time)
        }

    @staticmethod
    def format_datetime(value):
        """Helper method to format datetime into human-readable format."""
        return value.strftime("%d-%b-%Y %H:%M:%S UTC")

    def calculate_time_metrics(self, time_since_order, time_until_completion, 
                             inventory_available, order_quantity, actual_inventory_check_time):
        metrics = {
            "order_summary": {},
            "processing_breakdown": [],
            "time_status": {}
        }
        
        # Define base processing times
        order_processing_time = order_quantity / 2  
        fulfillment_time = round(order_quantity / 3 + order_processing_time, 2)  # Rounded to 2 decimals
       
        total_processing_time = (
            actual_inventory_check_time - 
            order_processing_time +  
            fulfillment_time
        )

        # Calculate completion status for each step based on time and inventory
        is_processing_complete = time_since_order >= (actual_inventory_check_time + order_processing_time)
        is_fulfillment_complete = time_since_order >= (
            actual_inventory_check_time + order_processing_time + fulfillment_time
        )
        
        # Order summary
        metrics["order_summary"] = {
            "total_processing_time": f"{round(total_processing_time, 2)} seconds",
            "inventory_status": "Available" if inventory_available else "Awaiting Production",
            "order_status": self.status,
            "order_quantity": order_quantity
        }

        # Detailed processing breakdown
        metrics["processing_breakdown"] = [
            {
                "step": "Inventory Check",
                "time": f"{round(actual_inventory_check_time, 2)} seconds",
                "status": "Completed"
            },
            {
                "step": "Order Processing",
                "time": f"{round(order_processing_time, 2)} seconds",
                "status": "Completed" if is_processing_complete else "Pending"
            }
        ]

        if not inventory_available:
            metrics["processing_breakdown"].append({
                "step": "Production Scheduling",
                "time": f"{round(order_processing_time, 2)} seconds",
                "status": "Required - Based on Quantity"
            })

        metrics["processing_breakdown"].append({
            "step": "Order Fulfillment",
            "time": f"{round(fulfillment_time, 2)} seconds",
            "status": "Completed" if is_fulfillment_complete else "Pending"
        })

        # Time status
        metrics["time_status"] = {
            "time_elapsed": f"{round(time_since_order, 2)} seconds",
            "estimated_time_remaining": f"{round(max(0, time_until_completion), 2)} seconds",
            "on_schedule": inventory_available or time_until_completion > 0
        }

        return metrics

def check_inventory_availability(order_id):
    """Check inventory availability with the Inventory Management service."""
    start_time = time.time()
    try:
        # Debugging: Start of the function
        logging.debug(f"Starting check_inventory_availability for order_id: {order_id}")
        
        # Get order details from order management service
        order_response = requests.get(f"http://ordermanagement:8001/order_service/{order_id}")
        logging.debug(f"Order management service response status: {order_response.status_code}")
        
        if order_response.status_code != 200:
            logging.warning(f"Failed to fetch order details for order_id: {order_id}. Defaulting quantity to 1.")
            end_time = time.time()
            return {
                "available": True,
                "quantity": 1,
                "check_time": round(end_time - start_time, 2)
            }

        # Parse order data
        order_data = order_response.json()
        logging.debug(f"Order data received: {order_data}")
        
        if 'data' not in order_data:
            logging.warning(f"'data' key missing in order data for order_id: {order_id}. Defaulting quantity to 1.")
            end_time = time.time()
            return {
                "available": True,
                "quantity": 1,
                "check_time": round(end_time - start_time, 2)
            }

        # Extract product_id and quantity
        product_id = order_data['data'].get('product_id')
        quantity = order_data['data'].get('quantity', 1)  # Default to 1 if quantity is missing
        logging.debug(f"Extracted product_id: {product_id}, quantity: {quantity}")

        # Check inventory
        inventory_payload = {"product_id": product_id, "quantity": quantity}
        logging.debug(f"Sending inventory check request with payload: {inventory_payload}")
        
        inventory_response = requests.post(
            f"http://inventorymanagement:8000/inventory/check",
            json=inventory_payload
        )
        
        logging.debug(f"Inventory service response status: {inventory_response.status_code}")

        end_time = time.time()
        check_time = round(end_time - start_time, 2)

        # Parse inventory response
        if inventory_response.status_code == 200:
            inventory_data = inventory_response.json()
            logging.debug(f"Inventory data received: {inventory_data}")
            
            if 'available_quantity' in inventory_data:
                return {
                    "available": inventory_data['available_quantity'] >= quantity,
                    "quantity": quantity,
                    "check_time": check_time
                }
        
        logging.warning(f"Inventory check failed or insufficient data for order_id: {order_id}.")
        return {
            "available": inventory_response.status_code == 200,
            "quantity": quantity,
            "check_time": check_time
        }

    except Exception as e:
        end_time = time.time()
        logging.error(f"Error checking inventory: {e}")
        return {
            "available": True,
            "quantity": 1,
            "check_time": round(end_time - start_time, 2)
        }


@app.route('/tracking/create', methods=['POST'])
def create_tracking():
    """
    Create tracking information for an order
    ---
    tags:
      - Tracking
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            order_id:
              type: integer
              description: The ID of the order to track.
          required:
            - order_id
    responses:
      201:
        description: Tracking created successfully
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
    try:
        data = request.get_json()
        if not data or 'order_id' not in data:
            return jsonify({"error": "Order ID is required"}), 400

        # Calculate processing times
        current_time = datetime.utcnow()
        
        # Check inventory availability and get quantity
        inventory_status = check_inventory_availability(data['order_id'])
        inventory_available = inventory_status['available']
        order_quantity = inventory_status['quantity']
        actual_inventory_check_time = inventory_status['check_time']
        
        # Calculate total processing time
        order_processing_time = order_quantity / 2
        fulfillment_time = order_quantity / 3 + order_processing_time
        total_processing_time = actual_inventory_check_time - order_processing_time + fulfillment_time
        
        estimated_completion = current_time + timedelta(seconds=total_processing_time)

        tracking = OrderTracking(
            order_id=data['order_id'],
            status='ORDER_PLACED',
            placed_time=current_time,
            estimated_completion_time=estimated_completion,
            inventory_check_time=actual_inventory_check_time
        )

        db.session.add(tracking)
        db.session.commit()
        return jsonify(tracking.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating tracking: {e}")
        return jsonify({"error": f"Failed to create tracking: {str(e)}"}), 500

@app.route('/tracking/<int:order_id>', methods=['GET'])
def get_tracking(order_id):
    """
    Get tracking information for an order
    ---
    tags:
      - Tracking
    parameters:
      - in: path
        name: order_id
        required: true
        type: integer
        description: The ID of the order to retrieve tracking information for.
    responses:
      200:
        description: Tracking information retrieved successfully
        schema:
          type: object
      404:
        description: Order tracking not found
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
        tracking = OrderTracking.query.filter_by(order_id=order_id).first()
        if not tracking:
            # Create a new tracking entry if it doesn't exist
            return create_tracking_for_existing_order(order_id)
        return jsonify(tracking.to_dict()), 200
    except Exception as e:
        logging.error(f"Error retrieving tracking: {e}")
        return jsonify({"error": f"Failed to retrieve tracking: {str(e)}"}), 500

def create_tracking_for_existing_order(order_id):
    """Create a new tracking entry for an existing order."""
    try:
        current_time = datetime.utcnow()
        inventory_status = check_inventory_availability(order_id)
        
        tracking = OrderTracking(
            order_id=order_id,
            status='ORDER_PLACED',
            placed_time=current_time,
            estimated_completion_time=current_time + timedelta(seconds=10),
            inventory_check_time=inventory_status['check_time']
        )
        
        db.session.add(tracking)
        db.session.commit()
        return jsonify(tracking.to_dict()), 200
    
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating tracking for existing order: {e}")
        return jsonify({"error": f"Failed to create tracking: {str(e)}"}), 500

@app.route('/tracking/update/<int:order_id>', methods=['PUT'])
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
        description: The ID of the order to update tracking for.
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
            datetime:
              type: string
              format: date-time
              description: The timestamp of the update in 'YYYY-MM-DD HH:MM:SS' format.
          required:
            - status
            - step
            - datetime
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
        data = request.get_json()
        if not data or 'status' not in data:
            return jsonify({"error": "Status is required"}), 400

        tracking = OrderTracking.query.filter_by(order_id=order_id).first()
        if not tracking:
            return jsonify({"error": "Order tracking not found"}), 404

        tracking.status = data['status']
        db.session.commit()
        return jsonify(tracking.to_dict()), 200

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating tracking: {e}")
        return jsonify({"error": f"Failed to update tracking: {str(e)}"}), 500

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
        order = Orders.query.get(order_id)
        if not order:
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

# Initialize the database schema
with app.app_context():
    # db.drop_all()
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8003)
