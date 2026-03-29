import requests
import logging

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

ORDER_STATES = {
    "ORDER_PLACED": {
        "Name": "Order Placed",
        "Step": "Order Placement",
        "Status": "Placed"
    },
    "INVENTORY_CHECK_FAILED": {
        "Name": "Inventory Check Failed",
        "Step": "Inventory Check",
        "Status": "Failed"
    },
    "INVENTORY_CHECK_SUCCESSFUL": {
        "Name": "Inventory Check Successful",
        "Step": "Inventory Check",
        "Status": "Successful"
    },
    "ORDER_PROCESSING": {
        "Name": "Order Processing",
        "Step": "Order Processing",
        "Status": "In Progress"
    },
    "ORDER_PROCESSED": {
        "Name": "Order Processed",
        "Step": "Order Processing",
        "Status": "Processed"
    },
    "ORDER_FULFILLED": {
        "Name": "Order Fulfilled",
        "Step": "Order Fulfillment",
        "Status": "Fulfilled"
    },
    "ORDER_UNFULFILLED": {
        "Name": "Order Unfulfilled",
        "Step": "Order Fulfillment",
        "Status": "Unfulfilled"
    }
}
def update_order_state(state_key, order_details, datetime, creation = False):
    try:
        # Get state details
        state_info = ORDER_STATES.get(state_key, {
            "Name": "Unknown State",
            "Step": "Unknown Step",
            "Status": "Unknown"
        })

        # Add the timestamp and state info to the order details
        order_details["date_recorded"] = str(datetime)
        order_details["order_state"] = state_info["Name"]

        # Log the order details
        logging.debug(f"Order details: {order_details}")

        # Handle "Order Placed" state separately
        if state_key == "ORDER_PLACED" or state_key == "ORDER_UNFULFILLED" or creation:
            logging.info(f"Creating new tracking for state: {state_info['Name']}")
            tracking_response = requests.post("http://ordertracking:8003/tracking/create", json=order_details)

            if tracking_response.status_code == 201:
                logging.info(f"Successfully created tracking for order {order_details['order_id']}")
            else:
                logging.error(f"Failed to create tracking. Status code: {tracking_response.status_code}")
                logging.error(f"Response: {tracking_response.text}")
        else:
            # For all other states, update tracking
            logging.info(f"Updating tracking for state: {state_info['Name']}")
            update_data = {
                "status": state_info["Status"],
                "step": state_info["Step"],
                "datetime": datetime.strftime("%Y-%m-%d %H:%M:%S")
            }
            tracking_response = requests.put(
                f"http://ordertracking:8003/tracking/update/{order_details['order_id']}",
                json=update_data
            )

            if tracking_response.status_code == 200:
                logging.info(f"Successfully updated tracking for order {order_details['order_id']}")
            else:
                logging.error(f"Failed to update tracking. Status code: {tracking_response.status_code}")
                logging.error(f"Response: {tracking_response.text}")
    except requests.RequestException as e:
        logging.error(f"Error calling tracking API: {e}")
    except KeyError as e:
        logging.error(f"Missing key in order details or state information: {e}")
        logging.exception(e)
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        logging.exception(e)