from flask import Flask, request, jsonify, render_template_string
import socket
import os
import setproctitle

# Setzen des Prozessnamens
setproctitle.setproctitle("shipment")

app = Flask(__name__)

# Beispielhafte Bestellungen
orders = [
    {"id": 1, "product_name": "Land Rover Range Rover", "quantity": 1, "customer_id": 1, "customer_name": "John Doe"},
    {"id": 2, "product_name": "BMW 3er", "quantity": 2, "customer_id": 2, "customer_name": "Jane Smith"},
    {"id": 3, "product_name": "Audi Q5", "quantity": 1, "customer_id": 3, "customer_name": "Bob Johnson"},
    {"id": 4, "product_name": "Tesla Model 3", "quantity": 3, "customer_id": 1, "customer_name": "John Doe"},
    {"id": 5, "product_name": "Ford Mustang", "quantity": 1, "customer_id": 2, "customer_name": "Jane Smith"},
    {"id": 6, "product_name": "Volkswagen Golf", "quantity": 2, "customer_id": 3, "customer_name": "Bob Johnson"},
    {"id": 7, "product_name": "Mercedes-Benz C-Klasse", "quantity": 1, "customer_id": 1, "customer_name": "John Doe"}
]

# REST-API

@app.route('/shipment/api', methods=['GET'])
def get_shipments():
    return jsonify(orders)

@app.route('/shipment/api/<int:id>', methods=['GET'])
def get_shipment_by_id(id):
    order = next((o for o in orders if o['id'] == id), None)
    if order:
        return jsonify(order)
    else:
        return jsonify({"error": "Shipment not found"}), 404

@app.route('/shipment/api/new', methods=['POST'])
def add_shipment():
    if not request.json or not 'product_name' in request.json or not 'quantity' in request.json or not 'customer_id' in request.json or not 'customer_name' in request.json:
        return jsonify({"error": "Bad Request"}), 400
    
    new_id = max(order['id'] for order in orders) + 1 if orders else 1
    new_order = {
        "id": new_id,
        "product_name": request.json['product_name'],
        "quantity": request.json['quantity'],
        "customer_id": request.json['customer_id'],
        "customer_name": request.json['customer_name']
    }
    
    orders.append(new_order)
    return jsonify(new_order), 201

# HTML Ausgabe

@app.route('/shipment')
def shipment_page():
    hostname = socket.gethostname()

    enriched_orders = []
    total_quantities = {}
    for order in orders:
        if order['customer_id'] not in total_quantities:
            total_quantities[order['customer_id']] = {
                'customer_name': order['customer_name'],
                'total_quantity': 0
            }
        total_quantities[order['customer_id']]['total_quantity'] += order['quantity']
        enriched_orders.append(order)

    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
        <link href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css" rel="stylesheet">
        <title>Shipment Service on {{ hostname }}</title>
    </head>
    <body>
        <div class="container">
            <h1 class="mt-5">Shipment Service on {{ hostname }}</h1>
            <table class="table table-striped mt-3">
                <thead>
                    <tr>
                        <th>Order ID</th>
                        <th>Customer Name</th>
                        <th>Product Name</th>
                        <th>Quantity</th>
                    </tr>
                </thead>
                <tbody>
                    {% for order in orders %}
                    <tr>
                        <td>{{ order['id'] }}</td>
                        <td>{{ order['customer_name'] }}</td>
                        <td>{{ order['product_name'] }}</td>
                        <td>{{ order['quantity'] }}</td>
                    </tr>
                    {% endfor %}
                    <tr>
                        <td colspan="3"><strong>Total Quantity</strong></td>
                        <td><strong>
                            {% for customer_id, data in total_quantities.items() %}
                                {{ data['customer_name'] }}: {{ data['total_quantity'] }}<br>
                            {% endfor %}
                        </strong></td>
                    </tr>
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """
    return render_template_string(html, orders=enriched_orders, hostname=hostname, total_quantities=total_quantities)

@app.route('/metrics')
def metrics():
    from prometheus_client import generate_latest
    return generate_latest(), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
