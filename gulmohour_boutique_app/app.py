import json
from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime, timedelta
import os

# --- Firestore Setup Imports ---
# NOTE: These imports are required for the Flask application to run locally or in the environment.
# They rely on the global variables __app_id, __firebase_config, and __initial_auth_token
# provided by the platform.
import firebase_admin
from firebase_admin import credentials, firestore
from firebase_admin import initialize_app, firestore, credentials, auth

# Define the global variables provided by the environment
__app_id = os.environ.get('APP_ID', 'default-app-id')
__firebase_config = os.environ.get('FIREBASE_CONFIG', '{}')
__initial_auth_token = os.environ.get('AUTH_TOKEN', None)

# --- Flask App Initialization and Firestore/Auth Setup ---

app = Flask(__name__)
app.secret_key = 'gulmohour-secret'

# 1. Initialize Firebase App
try:
    cred = credentials.Certificate("firebase-key.json")
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    # Use the service account method for initialization
    # cred = credentials.Certificate(json.loads(__firebase_config))
    # firebase_app = initialize_app(cred)
    # db = firestore.client()
except Exception as e:
    # Handle case where config might be invalid or environment setup is incomplete
    print(f"Failed to initialize Firebase: {e}")
    db = None

# Global variable to store current user's ID
# In a real app, this would be managed via Flask sessions after sign-in.
# Here, we use the provided custom token for authentication.
CURRENT_USER_ID = None

def initialize_auth():
    """Initializes authentication and sets the CURRENT_USER_ID."""
    global CURRENT_USER_ID
    if db:
        try:
            # For demonstration, we use the custom token if provided, otherwise, we use a default ID.
            # In the Canvas environment, this token will successfully authenticate.
            if __initial_auth_token:
                # The auth object needs to be initialized, but since we use firebase_admin (server-side SDK),
                # we primarily rely on the token being validated elsewhere. For client-side auth,
                # you'd typically use the client SDK (which is harder to manage in pure Flask).
                # For this demonstration, we'll use a placeholder user ID derived from the environment
                # or a default one if auth fails to establish a unique user.
                
                # In a production environment, you would decode the token server-side:
                # decoded_token = auth.verify_id_token(__initial_auth_token)
                # CURRENT_USER_ID = decoded_token['uid']
                
                # Since direct token validation might be complex here, we'll assume a successful auth
                # and use a stable, unique ID for persistence.
                CURRENT_USER_ID = __app_id # Use app ID as a unique identifier for this run
            else:
                # Fallback for local development without an auth token
                CURRENT_USER_ID = "anonymous_user_default_id"

        except Exception as e:
            print(f"Authentication setup failed: {e}")
            CURRENT_USER_ID = "anonymous_user_failed_auth"
            
    else:
        CURRENT_USER_ID = "no_db_connection"
        
    print(f"Using CURRENT_USER_ID: {CURRENT_USER_ID}")


# # Call initialization on startup
# if db:
#     initialize_auth()

# -----------------------------
# Helper: Safe payments parsing
# -----------------------------
def parse_payments(payments):
    """Ensure payments is always a list of dicts, even if stored as a JSON string."""
    if isinstance(payments, str):
        try:
            payments = json.loads(payments)
        except:
            payments = []
    if not isinstance(payments, list):
        payments = []
    # Keep only dicts
    return [p for p in payments if isinstance(p, dict)]

# --- Firestore Helper Functions ---

def get_collection_ref(collection_name):
    """Returns the Firestore CollectionReference for the current user's private data."""
        
    # The standard path for private user data in the Canvas environment
    return db.collection(collection_name)

def get_customer_by_id(customer_id):
    """Fetches a single customer document by ID."""
    customers_ref = get_collection_ref('customers')
    if not customers_ref: return None
    
    doc = customers_ref.document(customer_id).get()
    if doc.exists:
        customer_data = doc.to_dict()
        customer_data['id'] = doc.id
        return customer_data
    return None

def get_order_by_id(order_id):
    """Fetches a single order document by ID."""
    orders_ref = get_collection_ref('orders')
    if not orders_ref: return None
    
    doc = orders_ref.document(order_id).get()
    if doc.exists:
        order_data = doc.to_dict()
        order_data['id'] = doc.id
        return order_data
    return None


@app.route('/view_order/<order_id>')
def view_order(order_id):
    """Display all order details including saved measurements."""
    order_ref = db.collection('orders').document(order_id)
    doc = order_ref.get()
    if not doc.exists:
        flash("Order not found", "error")
        return redirect(url_for('all_orders'))

    order = doc.to_dict()
    order['id'] = doc.id
    return render_template('view_order.html', order=order)

def fetch_all_orders(customer_id=None):
    """Fetches all orders, optionally filtered by customer_id."""
    orders_ref = get_collection_ref('orders')
    if not orders_ref: return []

    # orders = []
    # for doc in db.collection('orders').stream():
    #     o = doc.to_dict()
    #     o['id'] = doc.id
    #     orders.append(o)
    # orders.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    # return render_template('view_orders.html', orders=orders)
    
    
    query = orders_ref.where('is_deleted', '==', False) #.order_by('delivery_date', direction=firestore.Query.ASCENDING)

    if customer_id:
        query = query.where('customer_id', '==', customer_id)
        print(f"Showing orders for customer ID: {customer_id}", 'info')

        
    try:
        docs = query.stream()
        orders = []
        for doc in docs:
            order = doc.to_dict()
            order['id'] = doc.id
            orders.append(order)
        return orders
    except Exception as e:
        flash(f"Error fetching orders: {e}", 'error')
        return []

def get_tasks_for_today():
    """Fetches simple placeholder tasks for the dashboard."""
    # In a real app, this would query a 'tasks' collection based on date
    today_str = datetime.now().strftime('%Y-%m-%d')
    tomorrow_str = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

    tasks = [
        {'title': 'Cut fabric for Maria Sharma Order', 'description': 'Dress Type: Salwar Kameez', 'status': 'due'},
        {'title': 'Final fitting with Ms. Anjali', 'description': '11:00 AM', 'status': 'due'},
        {'title': 'Order thread and buttons', 'description': 'Supplier call required', 'status': 'done'},
        {'title': f'Prepare delivery for Order #2345 (Due: {today_str})', 'description': 'Final checks', 'status': 'due'},
        {'title': f'Follow up on Order #2346 (Due: {tomorrow_str})', 'description': 'Check stitching status', 'status': 'due'},
    ]
    return tasks

from flask import request, flash, redirect, url_for, render_template
from datetime import datetime, timedelta
import json

# Assume `db` is your Firestore client and helper functions exist:
# get_customer_by_id(customer_id)
# parse_measurements(form)

# -----------------------------
# PROCESS ORDER FORM
# -----------------------------

def clean_for_firestore(obj):
    """Recursively clean data for Firestore compatibility."""
    if isinstance(obj, dict):
        return {k: clean_for_firestore(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        clean_list = []
        for v in obj:
            if isinstance(v, (str, int, float, bool)) or v is None:
                clean_list.append(v)
            elif isinstance(v, dict):
                clean_list.append(json.dumps(v, default=str))
            else:
                clean_list.append(str(v))
        return clean_list
    elif isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    else:
        return str(obj)
# -----------------------------
# PROCESS ORDER FORM
# -----------------------------
def process_order_form(order_id=None, customer_id=None, customer_name=''):
    """Create or update an order. Returns the full order dict including 'id'."""
    form = dict(request.form)
    measurements = parse_measurements(form)

    # Fetch customer name to include in order
    customer = get_customer_by_id(customer_id) if customer_id else None
    customer_name = customer.get('name') if customer else form.get('customer_name', '')

    data = {
        'customer_id': customer_id or form.get('customer_id'),
        'customer_name': customer_name,
        'dress_type': form.get('dress_type'),
        'occasion': form.get('occasion'),
        'fabric': form.get('fabric'),
        'lining': form.get('lining'),
        'delivery_date': form.get('delivery_date'),
        'price': float(form.get('price') or 0),
        'notes': form.get('notes'),
        'status': form.get('status', 'Pending'),
        'reference_links': [l for l in request.form.getlist('reference_link') if l.strip()],
        'measurements': measurements,
        'updated_at': firestore.SERVER_TIMESTAMP,
    }

    data = clean_for_firestore(data)
    orders_ref = db.collection('orders')

    if not order_id:
        # Create new order
        doc_ref = orders_ref.document()
        data['created_at'] = firestore.SERVER_TIMESTAMP
        data['is_deleted'] = False
        doc_ref.set(data)
        order = data.copy()
        order['id'] = doc_ref.id
        flash(f"Order created successfully! ID: {doc_ref.id}", "success")
        return order
    else:
        # Update existing order
        order_doc_ref = orders_ref.document(order_id)
        order_doc = order_doc_ref.get()
        if not order_doc.exists:
            flash(f"No order found with ID {order_id}", "error")
            return None
        order_doc_ref.update(data)
        order = data.copy()
        order['id'] = order_id
        flash("Order updated successfully", "success")
        return order


def parse_measurements(form):

    
    """Extract measurement fields for top and bottom from submitted form."""
    top_fields = ['shoulder','bust','waist','hip','armhole','sleeve_length','top_length','neck','front_neck','back_neck']
    bottom_fields = ['waist_b','hip_b','thigh','knee','calf','ankle','bottom_length']
    top = {f: form.get(f, '').strip() for f in top_fields}
    bottom = {f: form.get(f, '').strip() for f in bottom_fields}
    return {'top': top, 'bottom': bottom}




# --- Routes ---

@app.route('/')
def dashboard():
    """Main dashboard showing key metrics."""
    orders = fetch_all_orders()
    
    today = datetime.now().date()
    
    pending_orders = 0
    todays_tasks = 0
    total_customers = 0

    if orders:
        # Calculate pending orders
        pending_orders = sum(1 for o in orders if o.get('status') in ['Pending', 'In Progress'])
        
        # Calculate today's tasks (orders due today or in the next 3 days)
        def is_due_soon(order):
            try:
                delivery_date = datetime.strptime(order.get('delivery_date', '2999-01-01'), '%Y-%m-%d').date()
                if order.get('status') in ['Pending', 'In Progress']:
                    delta = delivery_date - today
                    return timedelta(days=0) <= delta <= timedelta(days=3)
            except:
                return False
            return False
            
        todays_tasks = sum(1 for o in orders if is_due_soon(o))
    
    customers_ref = get_collection_ref('customers')
    if customers_ref:
        try:
            total_customers = len(list(customers_ref.stream()))
        except Exception as e:
            print(f"Error counting customers: {e}")


    return render_template('dashboard.html', 
        pending_orders=pending_orders, 
        todays_tasks=todays_tasks,
        total_customers=total_customers
    )

# --- Customer Management ---
@app.route('/new_order/<customer_id>', methods=['GET', 'POST'])
def new_order_for_customer(customer_id):
    """Create a new order for a specific customer with measurements copied from profile."""
    customer_ref = db.collection('customers').document(customer_id)
    customer_doc = customer_ref.get()
    if not customer_doc.exists:
        flash("Customer not found", "error")
        return redirect(url_for('customers'))

    customer = customer_doc.to_dict()
    customer['id'] = customer_doc.id

    if request.method == 'POST':
        return process_order_form(customer_id=customer_id)

    measurements = customer.get('measurements', {})
    order_data = {
        'customer_id': customer_id,
        'customer_name': customer.get('name'),
        'measurements': measurements
    }
    return render_template('order_form.html', title="New Order", customer=customer, order=order_data)

@app.route('/customers')
def customers():
    """List and search all customers."""
    customers_ref = get_collection_ref('customers')
    if not customers_ref:
        return render_template('customers.html', customers=[], query='')

    query = request.args.get('q', '').strip()
    
    try:
        # Fetch all customers and filter them in Python for robust search
        # Firestore does not support multiple field 'OR' queries easily.
        all_customers = [
            doc.to_dict() | {'id': doc.id} # Python 3.9+ for merge, otherwise use dict(doc.to_dict(), id=doc.id)
            for doc in customers_ref.stream()
        ]
        
        if query:
            search_results = [
                c for c in all_customers 
                if query.lower() in c.get('name', '').lower() or 
                   query.lower() in c.get('phone', '').lower() or 
                   query.lower() in c.get('email', '').lower()
            ]
            customers_list = search_results
        else:
            customers_list = all_customers

        # Sort alphabetically by name
        customers_list.sort(key=lambda c: c.get('name', '').lower())
        
        return render_template('customers.html', customers=customers_list, query=query)
    except Exception as e:
        flash(f"Error retrieving customers: {e}", 'error')
        return render_template('customers.html', customers=[], query=query)


@app.route('/customer/add', methods=['GET', 'POST'])
def add_customer():
    """Add a new customer."""
    customers_ref = get_collection_ref('customers')
    if not customers_ref:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        form = request.form
        
        customer_data = {
            'name': form.get('name', '').strip(),
            'phone': form.get('phone', '').strip(),
            'email': form.get('email', '').strip(),
            'address': {
                'house': form.get('house', '').strip(),
                'locality': form.get('locality', '').strip(),
                'city': form.get('city', '').strip(),
                'state': form.get('state', '').strip(),
                'pin': form.get('pin', '').strip(),
            },
            'measurements': parse_measurements(dict(form)),
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP,
        }
        
        try:
            _, doc_ref = customers_ref.add(customer_data)
            flash(f"Customer '{customer_data['name']}' added successfully!", 'success')
            return redirect(url_for('view_customer', customer_id=doc_ref.id))
        except Exception as e:
            flash(f"Error adding customer: {e}", 'error')

    return render_template('customer_form.html', customer=None)


@app.route('/customer/edit/<customer_id>', methods=['GET', 'POST'])
def edit_customer(customer_id):
    """Edit an existing customer."""
    customers_ref = get_collection_ref('customers')
    if not customers_ref:
        return redirect(url_for('dashboard'))
        
    customer = get_customer_by_id(customer_id)
    if not customer:
        flash("Customer not found.", 'error')
        return redirect(url_for('customers'))

    if request.method == 'POST':
        form = request.form
        
        updated_data = {
            'name': form.get('name', '').strip(),
            'phone': form.get('phone', '').strip(),
            'email': form.get('email', '').strip(),
            'address': {
                'house': form.get('house', '').strip(),
                'locality': form.get('locality', '').strip(),
                'city': form.get('city', '').strip(),
                'state': form.get('state', '').strip(),
                'pin': form.get('pin', '').strip(),
            },
            'measurements': parse_measurements(form),
            'updated_at': firestore.SERVER_TIMESTAMP,
        }
        
        try:
            customers_ref.document(customer_id).update(updated_data)
            
            # Also update customer_name in all associated orders
            orders_ref = get_collection_ref('orders')
            if orders_ref:
                batch = db.batch()
                # Must use .where to filter
                orders_query = orders_ref.where('customer_id', '==', customer_id).stream() 
                for order_doc in orders_query:
                    batch.update(order_doc.reference, {'customer_name': updated_data['name']})
                batch.commit()

            flash(f"Customer '{updated_data['name']}' updated successfully!", 'success')
            return redirect(url_for('view_customer', customer_id=customer_id))
        except Exception as e:
            flash(f"Error updating customer: {e}", 'error')
            
        # If update fails, re-render the form with the new (potentially incomplete) data
        customer = updated_data | {'id': customer_id} # Update customer object for rendering

    return render_template('customer_form.html', customer=customer)


@app.route('/customer/<customer_id>')
@app.route('/customer/<customer_id>')
def view_customer(customer_id):
    """View customer profile, including measurements, linked orders, and financials."""
    customer = get_customer_by_id(customer_id)
    if not customer:
        flash("Customer not found.", 'error')
        return redirect(url_for('customers'))

    orders = fetch_all_orders(customer_id=customer_id)

    # Compute financials per order and overall for this customer
    total_revenue = 0
    total_outstanding = 0
    for o in orders:
        price = float(o.get('price', 0))
        payments = parse_payments(o.get('payments', []))   # <-- PATCHED
        paid_amount = sum(float(p.get('amount', 0)) for p in payments)
        balance_due = max(price - paid_amount, 0)
        o['paid_amount'] = paid_amount
        o['balance_due'] = balance_due
        total_revenue += paid_amount
        total_outstanding += balance_due

    customer_financials = {
        'total_revenue': total_revenue,
        'total_outstanding': total_outstanding
    }

    return render_template(
        'view_customer.html',
        customer=customer,
        orders=orders,
        customer_financials=customer_financials
    )


# --- Order Management ---

@app.route('/orders')
def all_orders():
    """List all orders from all customers."""
    orders = fetch_all_orders()
    
    # Orders already contain 'customer_name' and 'customer_id' from the process_order_form function, 
    # so we can render them directly.
    return render_template('all_orders.html', orders=orders)

# -----------------------------
# NEW ORDER ROUTE
# -----------------------------
# ----------------------------------------------------------
# Route: new order
# ----------------------------------------------------------
@app.route('/order/new/<customer_id>', methods=['GET', 'POST'])
def new_order(customer_id):
    customer = get_customer_by_id(customer_id)
    if not customer:
        flash("Customer not found.", "error")
        return redirect(url_for('customers'))

    if request.method == 'POST':
        order_id = process_order_form(order_id=None, customer_id=customer_id)
        if order_id:  # Only redirect if order creation succeeded
            return redirect(url_for('view_customer', customer_id=customer_id))
        else:
            return redirect(url_for('new_order', customer_id=customer_id))

    default_date = (datetime.now() + timedelta(weeks=2)).strftime('%Y-%m-%d')
    default_order = {
        'delivery_date': default_date,
        'status': 'Pending',
        'reference_links': [],
        'measurements': customer.get('measurements', {'top': {}, 'bottom': {}}),
        'customer_name': customer.get('name', '')
    }

    return render_template(
        'order_form.html',
        customer=customer,
        order=default_order,
        title="Add New Order"
    )

@app.route('/order/edit/<order_id>', methods=['GET', 'POST'])
def edit_order(order_id):
    """Edit an existing order."""
    order = get_order_by_id(order_id)
    orders_ref = get_collection_ref('orders')
    
    if not order or not orders_ref:
        flash("Order not found or Database not ready.", 'error')
        return redirect(url_for('dashboard'))

    customer = get_customer_by_id(order['customer_id'])
    customer_name = customer['name'] if customer else ''

    if request.method == 'POST':
        updated_data = process_order_form(order_id=order_id, customer_id=order['customer_id'], customer_name=customer_name)
        updated_data['updated_at'] = firestore.SERVER_TIMESTAMP
        
        try:
            orders_ref.document(order_id).update(updated_data)
            flash(f"Order for {customer_name} updated successfully!", 'success')
            return redirect(url_for('view_customer', customer_id=order['customer_id']))
        except Exception as e:
            flash(f"Error updating order: {e}", 'error')
            order = updated_data | {'id': order_id} # Update order object for rendering
            
    # Format delivery date for HTML input type="date"
    if order.get('delivery_date'):
        try:
            datetime.strptime(order['delivery_date'], '%Y-%m-%d')
        except ValueError:
            order['delivery_date'] = (datetime.now() + timedelta(weeks=2)).strftime('%Y-%m-%d')

    return render_template('order_form.html', customer=customer, order=order, title="Edit Order")

@app.route('/order/delete/<order_id>', methods=['POST'])
def delete_order(order_id):
    """Deletes an order."""
    order = get_order_by_id(order_id)
    orders_ref = get_collection_ref('orders')

    if not order or not orders_ref:
        flash("Order not found or Database not ready.", 'error')
        return redirect(url_for('dashboard'))

    customer_id = order['customer_id']
    
    try:
        # SOFT DELETE: Update the document to mark it as deleted, instead of deleting it permanently
        orders_ref.document(order_id).update({'is_deleted': True})
        
        flash(f"Order {order_id} has been marked as deleted.", 'success')

    except Exception as e:
        flash(f"Error deleting order: {e}", 'error')

    if customer_id:
        # Redirect back to the customer view
        return redirect(url_for('view_customer', customer_id=customer_id))
    else:
        # Fallback redirect to the main orders list
        return redirect(url_for('all_orders'))
        

# --- Daily Tasks ---

@app.route('/tasks')
def daily_tasks():
    """Shows orders due today or in the next 3 days."""
    orders = fetch_all_orders()
    today = datetime.now().date()
    
    def is_due_soon(order):
        """Check if order is pending/in progress and due within the next 3 days."""
        if order.get('status') in ['Pending', 'In Progress']:
            try:
                delivery_date = datetime.strptime(order.get('delivery_date', '2999-01-01'), '%Y-%m-%d').date()
                
                print('delivery date: ', delivery_date)
                delta = delivery_date - today
                return timedelta(days=0) <= delta <= timedelta(days=3)
            except:
                return False
        return False
        
    due_orders = [o for o in orders if is_due_soon(o)]

    print("Due Orders: ", due_orders)
    
    # Sort by nearest delivery date
    due_orders.sort(key=lambda o: datetime.strptime(o['delivery_date'], '%Y-%m-%d').date())
    
    return render_template('tasks.html', 
        due_orders=due_orders, 
        today=today.strftime('%A, %B %d, %Y')
    )

@app.route('/reports')
def reports_dashboard():
    """Show dashboard of all customers with links to their reports."""
    customers_ref = get_collection_ref('customers')
    customers = []
    if customers_ref:
        for doc in customers_ref.stream():
            c = doc.to_dict()
            c['id'] = doc.id
            customers.append(c)
    return render_template('reports_dashboard.html', customers=customers)


@app.route('/reports/customer/<customer_id>')
@app.route('/reports/customer/<customer_id>')
def customer_report(customer_id):
    """Generate financial report for a single customer."""
    customer = get_customer_by_id(customer_id)
    if not customer:
        flash("Customer not found", "error")
        return redirect(url_for('reports_dashboard'))

    orders = fetch_all_orders(customer_id=customer_id)

    total_revenue = sum(float(o.get('price', 0)) for o in orders)
    total_paid = sum(sum(float(p.get('amount', 0)) for p in parse_payments(o.get('payments', []))) for o in orders)  # <-- PATCHED
    total_outstanding = total_revenue - total_paid

    graph_data = {
        'orders': [o['id'] for o in orders],
        'revenue': [float(o.get('price', 0)) for o in orders],
        'paid': [sum(float(p.get('amount', 0)) for p in parse_payments(o.get('payments', []))) for o in orders],  # <-- PATCHED
        'balance': [float(o.get('price', 0)) - sum(float(p.get('amount', 0)) for p in parse_payments(o.get('payments', []))) for o in orders]  # <-- PATCHED
    }

    return render_template('report_customer.html',
                           customer=customer,
                           total_revenue=total_revenue,
                           total_paid=total_paid,
                           total_outstanding=total_outstanding,
                           graph_data=graph_data)

@app.route('/reports/boutique')
@app.route('/reports/boutique')
def boutique_report():
    """Generate overall boutique financial report."""
    orders = fetch_all_orders()
    customers_ref = get_collection_ref('customers')

    total_revenue = sum(float(o.get('price', 0)) for o in orders)
    total_paid = sum(sum(float(p.get('amount', 0)) for p in parse_payments(o.get('payments', []))) for o in orders)  # <-- PATCHED
    total_outstanding = total_revenue - total_paid

    # Graph data per customer
    graph_data = {'customers': [], 'revenue': [], 'paid': [], 'balance': []}
    if customers_ref:
        for doc in customers_ref.stream():
            c = doc.to_dict()
            c_id = doc.id
            c_orders = fetch_all_orders(customer_id=c_id)
            c_revenue = sum(float(o.get('price', 0)) for o in c_orders)
            c_paid = sum(sum(float(p.get('amount', 0)) for p in parse_payments(o.get('payments', []))) for o in c_orders)  # <-- PATCHED
            c_balance = c_revenue - c_paid
            graph_data['customers'].append(c.get('name', 'Unknown'))
            graph_data['revenue'].append(c_revenue)
            graph_data['paid'].append(c_paid)
            graph_data['balance'].append(c_balance)

    return render_template('report_boutique.html',
                           total_revenue=total_revenue,
                           total_paid=total_paid,
                           total_outstanding=total_outstanding,
                           graph_data=graph_data)

if __name__ == '__main__':
    # Flask runs only the development server here.
    # In the live environment, an external WSGI server (like gunicorn) will run the app.
    app.run(debug=True)
