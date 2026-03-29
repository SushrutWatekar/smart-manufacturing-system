const CLIENT_SERVICE_URL = "http://localhost:8010"

// Handle order creation
document.getElementById('create-order-form').addEventListener('submit', function(event) {
    event.preventDefault();

    // Get values from form
    const client_id = document.getElementById('order-client-id').value;
    const product_id = document.getElementById('order-product-id').value;
    let quantity = document.getElementById('order-quantity').value;

    // Convert quantity to an integer before sending it
    quantity = parseInt(quantity, 10);

    // Show loading message while waiting for the response
    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = `<p>Loading...</p>`;  // You can replace this with a spinner if preferred

    // Send POST request to create order
    fetch(`${CLIENT_SERVICE_URL}/order_service/create`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        mode: "cors",
        body: JSON.stringify({ client_id, product_id, quantity })
    })
        .then(response => response.json())  // Parse the response as JSON
        .then(data => {
            if (data && data?.order_response) {
                const {
                    order_id,
                    client_id,
                    quantity,
                    fullfiled = false
                } = data.order_response
                // Display success message in a formatted way
                const resultsDiv = document.getElementById('results');
                resultsDiv.innerHTML = `
                    <h3>Order Created Successfully</h3>
                    <p><strong>Order ID:</strong> ${order_id}</p>
                    <p><strong>Client ID:</strong> ${client_id}</p>
                    <p><strong>Product ID:</strong> ${product_id}</p>
                    <p><strong>Quantity:</strong> ${quantity}</p>
                    <p><strong>Fullfiled:</strong> ${fullfiled ? "True" : "False"}</p>
                `;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            resultsDiv.textContent = "Failed to create order. Please try again.";
        });
});


// Handle searching orders by client ID
document.getElementById('search-order-form').addEventListener('submit', function(event) {
    event.preventDefault();
    const client_id = document.getElementById('search-client-id').value;

    // Send GET request to search for orders by client ID
    fetch(`${CLIENT_SERVICE_URL}/client/${client_id}/orders`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        },
        mode: "cors",
    })
        .then(response => response.json())
        .then(data => {
            const resultsDiv = document.getElementById('results');
            if (data.length === 0) {
                resultsDiv.textContent = "No orders found for this client.";
            } else {
                // Create an HTML table for displaying orders
                let table = `
                    <h3>Orders for Client ID: ${client_id}</h3>
                    <table border="1">
                        <thead>
                            <tr>
                                <th>Order ID</th>
                                <th>Product ID</th>
                                <th>Quantity</th>
                                <th>Fullfiled</th>
                            </tr>
                        </thead>
                        <tbody>
                `;

                // Populate table rows
                data.forEach(order => {
                    table += `
                        <tr>
                            <td>${order.order_id}</td>
                            <td>${order.product_id}</td>
                            <td>${order.quantity}</td>
                            <td>${order.fullfiled}</td>
                        </tr>
                    `;
                });

                table += `
                        </tbody>
                    </table>
                `;

                // Update results div
                resultsDiv.innerHTML = table;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            document.getElementById('results').textContent = "Failed to load orders. Please try again.";
        });
});
