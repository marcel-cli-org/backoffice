from flask import Flask, request, jsonify, render_template_string, Response
import socket
import os
import setproctitle
from prometheus_client import start_http_server, Counter, Histogram
import time
from collections import defaultdict

# Setzen des Prozessnamens
setproctitle.setproctitle("invoicing")

app = Flask(__name__)

# Simulierter Speicher für Bestellungen
orders = [
    {"customer_id": 1, "customer_name": "John Doe", "id": 1, "product_id": 1, "product_name": "Land Rover Range Rover", "product_price": 150000, "quantity": 1, "total": 150000},
    {"customer_id": 2, "customer_name": "Jane Smith", "id": 2, "product_id": 4, "product_name": "BMW 3er", "product_price": 60000, "quantity": 2, "total": 120000},
    {"customer_id": 3, "customer_name": "Bob Johnson", "id": 3, "product_id": 8, "product_name": "Audi Q5", "product_price": 70000, "quantity": 1, "total": 70000},
    {"customer_id": 1, "customer_name": "John Doe", "id": 4, "product_id": 16, "product_name": "Tesla Model 3", "product_price": 55000, "quantity": 3, "total": 165000},
    {"customer_id": 2, "customer_name": "Jane Smith", "id": 5, "product_id": 19, "product_name": "Ford Mustang", "product_price": 60000, "quantity": 1, "total": 60000},
    {"customer_id": 3, "customer_name": "Bob Johnson", "id": 6, "product_id": 22, "product_name": "Volkswagen Golf", "product_price": 45000, "quantity": 2, "total": 90000},
    {"customer_id": 1, "customer_name": "John Doe", "id": 7, "product_id": 10, "product_name": "Mercedes-Benz C-Klasse", "product_price": 70000, "quantity": 1, "total": 70000}
]

# Prometheus Metrics
REQUEST_COUNT = Counter('invoicing_requests_total', 'Total number of requests to the invoicing service', ['method', 'endpoint', 'http_status'])
REQUEST_LATENCY = Histogram('invoicing_request_latency_seconds', 'Request latency in seconds', ['method', 'endpoint'])

@app.route('/invoicing/api', methods=['GET'])
def get_invoicing():
    start_time = time.time()
    try:
        # Gruppieren und Summieren der Bestellungen pro Kunde
        invoicing_summary = defaultdict(lambda: {"customer_name": "", "total_amount": 0.0, "entries": []})
        for order in orders:
            invoicing_summary[order["customer_id"]]["customer_name"] = order["customer_name"]
            invoicing_summary[order["customer_id"]]["total_amount"] += order["total"]
            invoicing_summary[order["customer_id"]]["entries"].append(order)

        response_data = [{"customer_id": customer_id, "customer_name": details["customer_name"], "total_amount": details["total_amount"], "entries": details["entries"]} for customer_id, details in invoicing_summary.items()]

        response = jsonify({"status": "success", "data": response_data})
        status = 200
    except Exception as e:
        response = jsonify({"status": "error", "message": str(e)})
        status = 500
    finally:
        request_latency = time.time() - start_time
        REQUEST_COUNT.labels(method=request.method, endpoint=request.path, http_status=status).inc()
        REQUEST_LATENCY.labels(method=request.method, endpoint=request.path).observe(request_latency)
    
    return response, status

@app.route('/invoicing', methods=['GET'])
def get_invoicing_html():
    start_time = time.time()
    try:
        # Gruppieren und Summieren der Bestellungen pro Kunde
        invoicing_summary = defaultdict(lambda: {"customer_name": "", "total_amount": 0.0, "entries": []})
        for order in orders:
            invoicing_summary[order["customer_id"]]["customer_name"] = order["customer_name"]
            invoicing_summary[order["customer_id"]]["total_amount"] += order["total"]
            invoicing_summary[order["customer_id"]]["entries"].append(order)

        response_data = [{"customer_id": customer_id, "customer_name": details["customer_name"], "total_amount": details["total_amount"], "entries": details["entries"]} for customer_id, details in invoicing_summary.items()]

        hostname = socket.gethostname()
        total_all = sum(details["total_amount"] for details in invoicing_summary.values())
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
            <link href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css" rel="stylesheet">
            <title>Invoicing Service on {{ hostname }}</title>
        </head>
        <body>
            <div class="container">
                <h1 class="mt-5">Invoicing Service on {{ hostname }}</h1>
                <table class="table table-striped mt-3">
                    <thead>
                        <tr>
                            <th>Customer ID</th>
                            <th>Customer Name</th>
                            <th>Order ID</th>
                            <th>Product Name</th>
                            <th>Quantity</th>
                            <th>Product Price</th>
                            <th>Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for entry in data %}
                            {% for order in entry.entries %}
                            <tr>
                                <td>{{ entry.customer_id }}</td>
                                <td>{{ entry.customer_name }}</td>
                                <td>{{ order.id }}</td>
                                <td>{{ order.product_name }}</td>
                                <td>{{ order.quantity }}</td>
                                <td>${{ order.product_price }}</td>
                                <td>${{ order.total }}</td>
                            </tr>
                            {% endfor %}
                            <tr>
                                <td colspan="6"><strong>Total for {{ entry.customer_name }}</strong></td>
                                <td><strong>${{ entry.total_amount }}</strong></td>
                            </tr>
                        {% endfor %}
                        <tr>
                            <td colspan="6"><strong>Total</strong></td>
                            <td><strong>${{ total_all }}</strong></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </body>
        </html>
        """
        response = render_template_string(html, data=response_data, hostname=hostname, total_all=total_all)
        status = 200
    except Exception as e:
        response = jsonify({"status": "error", "message": str(e)})
        status = 500
    finally:
        request_latency = time.time() - start_time
        REQUEST_COUNT.labels(method=request.method, endpoint=request.path, http_status=status).inc()
        REQUEST_LATENCY.labels(method=request.method, endpoint=request.path).observe(request_latency)
    
    return response, status

@app.route('/metrics')
def metrics():
    from prometheus_client import generate_latest
    return generate_latest(), 200

@app.route('/invoicing/api/new', methods=['POST'])
def add_order():
    start_time = time.time()
    try:
        if not request.json or not 'customer_id' in request.json or not 'customer_name' in request.json or not 'amount' in request.json:
            return jsonify({"error": "Bad Request"}), 400
        
        new_id = max(order['id'] for order in orders) + 1 if orders else 1
        new_order = {
            "id": new_id,
            "customer_id": request.json['customer_id'],
            "customer_name": request.json['customer_name'],
            "amount": request.json['amount']
        }
        
        orders.append(new_order)
        response = jsonify(new_order)
        status = 201
    except Exception as e:
        response = jsonify({"status": "error", "message": str(e)})
        status = 500
    finally:
        request_latency = time.time() - start_time
        REQUEST_COUNT.labels(method=request.method, endpoint=request.path, http_status=status).inc()
        REQUEST_LATENCY.labels(method=request.method, endpoint=request.path).observe(request_latency)
    
    return response, status

if __name__ == '__main__':
    # Start up the server to expose the metrics.
    start_http_server(8000)
    app.run(host='0.0.0.0', port=8080)
