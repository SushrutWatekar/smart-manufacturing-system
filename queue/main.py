from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from datetime import date
import json
import pika
import os
import time
import requests
import threading

app = Flask(__name__)

rabbitmq_user = os.getenv("RABBITMQ_DEFAULT_USER")
rabbitmq_pass = os.getenv("RABBITMQ_DEFAULT_PASS")
rabbitmq_port = os.getenv("RABBITMQ_DEFAULT_PORT")


# URLS's of different services
INVENTORY_SERVICE_URL = os.getenv("INVENTORY_SERVICE_URL", "http://inventorymanagement:8000")
ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://ordermanagement:8001")
PRODUCTION_SERVICE_URL = os.getenv("PRODUCTION_SERVICE_URL", "http://productionscheduling:8002")


# RabbitMQ connection
credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_pass)
parameters = pika.ConnectionParameters("rabbitmq", rabbitmq_port, "/", credentials=credentials)
connection = None
for i in range(10):  # Retry 10 times
    try:
        connection = pika.BlockingConnection(parameters)
        print("Connection successful", flush=True)
        break
    except pika.exceptions.AMQPConnectionError:
        print("Connection failed, retrying...")
        time.sleep(10)

if connection is None:
    print("Failed to connect to RabbitMQ after retries.", flush=True)
channel = connection.channel()
channel.queue_declare(queue="production_queue")


def process_production_request(data):
    try:
        with app.app_context():
            # data = json.loads(body)
            product_id = data.get("product_id")
            quantity = data.get("quantity")
            order_id = data.get("order_id")
            requests.post(f"{PRODUCTION_SERVICE_URL}/schedule/production", json={"product_id": product_id, "quantity": +quantity, "order_id": order_id})
            print(data, flush=True)
    except Exception as e:
        print(f"Error processing message: {e}", flush=True)
        # ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def threaded_callback(ch, method, properties, body):
    try:
        data = json.loads(body)
        thread = threading.Thread(target=process_production_request, args=(data,))
        thread.start()
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"Error starting thread for message: {e}", flush=True)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

# Subscribe to RabbitMQ queue
channel.basic_qos(prefetch_count=5)  # Fetch up to 5 messages simultaneously
channel.basic_consume(queue="production_queue", on_message_callback=threaded_callback)
# channel.basic_consume(queue='return_book', on_message_callback=process_return_request)


print("ProductionQueue is waiting for messages...", flush=True)
try:
    channel.start_consuming()
except Exception as e:
    print(f"Error processing Consumer: {e}", flush=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8004, debug=True)
