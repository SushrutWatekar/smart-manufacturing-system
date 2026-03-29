from flask import Flask, request, jsonify
import requests
from flask_sqlalchemy import SQLAlchemy
from datetime import date
import os
from threading import Lock
import time
import threading
from flasgger import Swagger
import logging

app = Flask(__name__)

# Initialize Swagger
swagger = Swagger(app)

# URLS's of different services
INVENTORY_SERVICE_URL = os.getenv("INVENTORY_SERVICE_URL", "http://inventorymanagement:8000")
ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://ordermanagement:8001")
PRODUCTION_SERVICE_URL = os.getenv("PRODUCTION_SERVICE_URL", "http://productionscheduling:8002")

# Database configuration
db_user = os.getenv("POSTGRES_USER")
db_password = os.getenv("POSTGRES_PASSWORD")
db_host = os.getenv("POSTGRES_HOST")
db_port = os.getenv("POSTGRES_PORT")
db_name = os.getenv("POSTGRES_DB")

app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


class Production(db.Model):
    __tablename__ = "machines"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    machine_id = db.Column(db.Integer)
    active = db.Column(db.Boolean, nullable=False, default=True)
    status = db.Column(db.String, nullable=False, default="idle")

    # Method to convert the order object to a dictionary
    def to_dict(self):
        return {
            "machine_id": self.machine_id,
            "active": self.active,
            "status": self.status,
        }


with app.app_context():
    db.create_all()
    if Production.query.count() == 0:
        sample_machines = [Production(machine_id=1, status="idle", active=True), Production(machine_id=2, status="idle", active=True), Production(machine_id=3, status="idle", active=True)]
        db.session.bulk_save_objects(sample_machines)
        db.session.commit()


def find_free_machine():
    # Find the first idle and active machine
    machine = Production.query.filter_by(status="idle", active=True).first()
    print(machine, flush=True)
    if machine:
        # Lock the machine by updating its status to busy
        machine.status = "busy"
        db.session.commit()
        print(machine, flush=True)
        return machine
    return None  # No free machine available


@app.route("/schedule/production", methods=["POST"])
def produce():
    """
    Schedule production for a product
    ---
    tags:
      - Production
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            product_id:
              type: string
              description: The ID of the product to produce.
            quantity:
              type: integer
              description: The quantity of the product to produce.
            order_id:
              type: integer
              description: The ID of the order for which production is scheduled.
          required:
            - product_id
            - quantity
            - order_id
    responses:
      200:
        description: Production started successfully
        schema:
          type: object
          properties:
            status:
              type: string
      400:
        description: Invalid data
        schema:
          type: object
          properties:
            error:
              type: string
      503:
        description: No machines available
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
    data = request.json
    product_id = data.get("product_id")
    quantity = data.get("quantity")
    order_id = data.get("order_id")

    if not product_id or not quantity or not order_id:
        return jsonify({"error": "Invalid request. 'product_id', 'quantity' and 'order_id' are required."}), 400

    # Find a free machine
    machine = find_free_machine()
    print(machine, flush=True)
    if not machine:
        return jsonify({"error": "No machines are currently available. Please try again later."}), 503

    # Start production in a new thread
    # threading.Thread(target=produce_stock, args=(machine, product_id, quantity)).start()
    try:
        print(f"Machine {machine.machine_id} started producing {quantity} of {product_id}.")
        time.sleep(quantity / 2)  # Simulate production time (1 second per quantity)
        logging.debug("Updating inventory to deduct the ordered quantity.")
        response = requests.post(f"{INVENTORY_SERVICE_URL}/inventory/update", json={"product_id": product_id, "quantity": +quantity})

        if response.status_code == 200:
            requests.post(f"{ORDER_SERVICE_URL}/order_service/complete", json={"order_id": order_id})
        print(f"Machine {machine.machine_id} finished producing {quantity} of {product_id}.")
    finally:
        # Free up the machine after production
        machine.status = "idle"
        db.session.commit()
        return jsonify({"status": f"Production started on {machine.machine_id} for {quantity} of {product_id}."}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8002, debug=True)
