from flask import Flask, jsonify, render_template_string, request
import socket
import os
import setproctitle
import requests
from collections import defaultdict
import time
from prometheus_client import start_http_server, Counter, Histogram

# Setzen des Prozessnamens
setproctitle.setproctitle("invoicing")

app = Flask(__name__)

# Get environment variable(s)
SUFFIX = os.getenv('URL_SUFFIX', '')

ORDER_SERVICE_URL = f"http://order{SUFFIX}:8080/order/api"
CUSTOMER_SERVICE_URL = f"http://customer{SUFFIX}:8080/customer/api"
CATALOG_SERVICE_URL = f"http://catalog{SUFFIX}:8080/catalog/api"

# REST-Aufruf, um alle Bestellungen abzurufen
def get_orders():
    response = requests.get(ORDER_SERVICE_URL)
    if response.status_code == 200:
        return response.json()
    return []

# REST-Aufruf, um alle Kundeninformationen abzurufen
def get_customers():
    response = requests.get(CUSTOMER_SERVICE_URL)
    if response.status_code == 200:
        return response.json()
    return []

# REST-Aufruf, um alle Produktinformationen abzurufen
def get_catalog():
    response = requests.get(CATALOG_SERVICE_URL)
    if response.status_code == 200:
        return response.json()
    return []

# Funktion, um die Daten für die Tabellen aufzubereiten
def process_data(orders, customers, catalog):
    customers_dict = {customer["id"]: customer for customer in customers}
    catalog_dict = {item["id"]: item for item in catalog}
    
    invoices = defaultdict(lambda: {"customer_name": "", "total_amount": 0.0, "entries": []})
    for order in orders:
        customer = customers_dict.get(order["customer_id"], {})
        product = catalog_dict.get(order["product_id"], {})
        
        if customer and product:
            total = order["quantity"] * product["price"]
            invoices[order["customer_id"]]["customer_name"] = customer["name"]
            invoices[order["customer_id"]]["total_amount"] += total
            invoices[order["customer_id"]]["entries"].append({
                "order_id": order["id"],
                "product_name": product["name"],
                "quantity": order["quantity"],
                "product_price": product["price"],
                "total": total
            })
    return invoices

# Prometheus Metrics
REQUEST_COUNT = Counter('invoicing_requests_total', 'Total number of requests to the invoicing service', ['method', 'endpoint', 'http_status'])
REQUEST_LATENCY = Histogram('invoicing_request_latency_seconds', 'Request latency in seconds', ['method', 'endpoint'])

@app.route('/invoicing/api', methods=['GET'])
def get_invoices():
    start_time = time.time()
    try:
        orders = get_orders()
        customers = get_customers()
        catalog = get_catalog()
        
        invoices = process_data(orders, customers, catalog)
        response_data = [{"customer_id": customer_id, "customer_name": details["customer_name"], "total_amount": details["total_amount"], "entries": details["entries"]} for customer_id, details in invoices.items()]
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
def get_invoices_html():
    start_time = time.time()
    try:
        orders = get_orders()
        customers = get_customers()
        catalog = get_catalog()
        
        invoices = process_data(orders, customers, catalog)
        response_data = [{"customer_id": customer_id, "customer_name": details["customer_name"], "total_amount": details["total_amount"], "entries": details["entries"]} for customer_id, details in invoices.items()]

        hostname = socket.gethostname()
        total_all = sum(details["total_amount"] for details in invoices.values())
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
                                <td>{{ order.order_id }}</td>
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

if __name__ == '__main__':
    # Start up the server to expose the metrics.
    start_http_server(8001)
    app.run(host='0.0.0.0', port=8080)
