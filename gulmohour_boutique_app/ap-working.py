from flask import Flask, render_template, request, redirect, url_for, flash
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import re

app = Flask(__name__)
app.secret_key = 'gulmohour-secret'

# Initialize Firebase
cred = credentials.Certificate("firebase-key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# ---------- Helpers ----------
def normalize(s):
    return str(s).strip().lower()

def find_customer_by_query(search_query):
    """Search customer by name, phone, or email."""
    if not search_query:
        return None, None
    q = normalize(search_query)
    for doc in db.collection('customers').stream():
        data = doc.to_dict()
        name = normalize(data.get('name', ''))
        phone = normalize(data.get('phone', ''))
        email = normalize(data.get('email', ''))
        if q == phone or q == email or q in name:
            data['id'] = doc.id
            return doc.id, data
    return None, None


# ---------- DASHBOARD ----------
@app.route('/')
def dashboard():
    orders_ref = db.collection('orders')
    orders = [doc.to_dict() for doc in orders_ref.stream()]
    customers_ref = db.collection('customers')
    customers = [doc.to_dict() for doc in customers_ref.stream()]

    total_customers = len(customers)
    pending_orders = len([o for o in orders if o.get('status') != 'Delivered'])
    delivered_orders = len([o for o in orders if o.get('status') == 'Delivered'])
    measurements_recorded = len([c for c in customers if 'measurements' in c and c['measurements']])
    recent_customers = sorted(customers, key=lambda x: x.get('name', ''))[:5]
    recent_orders = orders[:5]

    # Placeholder for today's tasks
    todays_tasks = db.collection('tasks').where('date', '==', datetime.now().strftime('%Y-%m-%d')).stream()
    todays_tasks = len(list(todays_tasks))

    return render_template(
        'dashboard.html',
        total_customers=total_customers,
        pending_orders=pending_orders,
        delivered_orders=delivered_orders,
        measurements_recorded=measurements_recorded,
        recent_customers=recent_customers,
        recent_orders=recent_orders,
        todays_tasks=todays_tasks
    )


# ---------- CUSTOMERS ----------
@app.route('/customers', methods=['GET', 'POST'])
def customers():
    query = request.args.get('q', '').strip()
    customer = {}  # default empty customer object

    if query:
        doc_id, data = find_customer_by_query(query)
        if doc_id:
            # Customer found, redirect to profile page
            return redirect(url_for('view_customer', customer_id=doc_id))
        else:
            # Customer not found, show add form with warning
            flash(f"No customer found for '{query}'. Please add new.", "warning")
            return render_template(
                'add_customer.html',
                not_found_query=query,
                customer=customer
            )

    # If no search, show all customers
    customers_list = []
    for doc in db.collection('customers').stream():
        d = doc.to_dict()
        d['id'] = doc.id
        customers_list.append(d)

    # Sort customers by name
    customers_list.sort(key=lambda x: (x.get('name') or '').lower())

    return render_template(
        'customers.html',
        customers=customers_list,
        query=query,
        customer=customer  # always pass customer to template
    )


@app.route('/customer/<customer_id>')
def view_customer(customer_id):
    # Fetch customer
    customer_ref = db.collection('customers').document(customer_id)
    customer_doc = customer_ref.get()
    if not customer_doc.exists:
        flash('Customer not found', 'error')
        return redirect(url_for('customers'))

    customer = customer_doc.to_dict()
    customer['id'] = customer_id  # add ID for template
    if 'address' not in customer:
        customer['address'] = {}
    if 'measurements' not in customer:
        customer['measurements'] = {'top': {}, 'bottom': {}}

    # Fetch orders (can be empty)
    orders_ref = db.collection('orders').where('customer_id', '==', customer_id)
    orders = []
    for o_doc in orders_ref.stream():
        o = o_doc.to_dict()
        o['id'] = o_doc.id
        orders.append(o)
    orders.sort(key=lambda x: x.get('delivery_date') or '', reverse=True)

    return render_template('view_customer.html', customer=customer, orders=orders)

# ---------- ADD CUSTOMER ----------
@app.route('/customer/add', methods=['GET', 'POST'])
def add_customer():
    if request.method == 'POST':
        # Gather contact info
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()

        if not phone or not email:
            flash('Phone and Email are required.', 'error')
            return render_template('customer_form.html', customer=None)

        # Validation
        if not re.match(r"^\+?\d{10,13}$", phone):
            flash("Invalid phone number format.", "error")
            return render_template('customer_form.html', customer=None)
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash("Invalid email format.", "error")
            return render_template('customer_form.html', customer=None)

        address = {
            'house': request.form.get('house', '').strip(),
            'locality': request.form.get('locality', '').strip(),
            'city': request.form.get('city', '').strip(),
            'state': request.form.get('state', '').strip(),
            'pin': request.form.get('pin', '').strip(),
        }

        top_fields = ['shoulder','bust','waist','hip','armhole','sleeve_length','top_length','neck','front_neck','back_neck']
        bottom_fields = ['waist_b','hip_b','thigh','knee','calf','ankle','bottom_length']

        top = {k: request.form.get(k, '') for k in top_fields}
        bottom = {k: request.form.get(k, '') for k in bottom_fields}

        data = {
            'name': name,
            'phone': phone,
            'email': email,
            'address': address,
            'measurements': {'top': top, 'bottom': bottom},
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        ref = db.collection('customers').add(data)
        new_id = ref.id if hasattr(ref, 'id') else ref[1].id
        flash('Customer added successfully', 'success')
        return redirect(url_for('view_customer', customer_id=new_id))

    # GET request -> render form
    return render_template('customer_form.html', customer=None)

@app.route('/customer/<customer_id>/edit', methods=['GET', 'POST'])
def edit_customer(customer_id):
    customer_ref = db.collection('customers').document(customer_id)
    customer_doc = customer_ref.get()
    if not customer_doc.exists:
        flash('Customer not found', 'error')
        return redirect(url_for('customers'))

    customer = customer_doc.to_dict()

    if request.method == 'POST':
        # Gather contact info
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()

        if not phone or not email:
            flash('Phone and Email are required.', 'error')
            return render_template('customer_form.html', customer=customer)

        # Validation
        if not re.match(r"^\+?\d{10,13}$", phone):
            flash("Invalid phone number format.", "error")
            return render_template('customer_form.html', customer=customer)
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash("Invalid email format.", "error")
            return render_template('customer_form.html', customer=customer)

        address = {
            'house': request.form.get('house', '').strip(),
            'locality': request.form.get('locality', '').strip(),
            'city': request.form.get('city', '').strip(),
            'state': request.form.get('state', '').strip(),
            'pin': request.form.get('pin', '').strip(),
        }

        top_fields = ['shoulder','bust','waist','hip','armhole','sleeve_length','top_length','neck','front_neck','back_neck']
        bottom_fields = ['waist_b','hip_b','thigh','knee','calf','ankle','bottom_length']

        top = {k: request.form.get(k, '') for k in top_fields}
        bottom = {k: request.form.get(k, '') for k in bottom_fields}

        data = {
            'name': name,
            'phone': phone,
            'email': email,
            'address': address,
            'measurements': {'top': top, 'bottom': bottom},
            'updated_at': datetime.utcnow()
        }

        customer_ref.update(data)
        flash('Customer updated successfully', 'success')
        return redirect(url_for('view_customer', customer_id=customer_id))

    # GET request -> render form with existing customer
    return render_template('customer_form.html', customer=customer)

# ---------- ORDERS ----------
@app.route('/orders')
def view_orders():
    """List all boutique orders."""
    orders = []
    for doc in db.collection('orders').stream():
        o = doc.to_dict()
        o['id'] = doc.id
        orders.append(o)
    orders.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return render_template('view_orders.html', orders=orders)

@app.route('/order/<order_id>/edit', methods=['GET', 'POST'])
def edit_order(order_id):
    order_ref = db.collection('orders').document(order_id)
    order_doc = order_ref.get()
    if not order_doc.exists:
        flash('Order not found.', 'error')
        return redirect(url_for('view_orders'))

    order = order_doc.to_dict()
    if request.method == 'POST':
        # Update fields from form
        order_data = {
            'dress_type': request.form.get('dress_type', '').strip(),
            'occasion': request.form.get('occasion', '').strip(),
            'fabric': request.form.get('fabric', '').strip(),
            'delivery_date': request.form.get('delivery_date', '').strip(),
            'design_notes': request.form.get('design_notes', '').strip(),
            'status': request.form.get('status', 'Pending')
        }

        # Handle reference links
        links = [l.strip() for l in request.form.getlist('reference_links') if l.strip()]
        single_link = request.form.get('reference_link', '').strip()
        if single_link:
            links.insert(0, single_link)
        if links:
            order_data['reference_links'] = links

        order_ref.update(order_data)
        flash('Order updated successfully!', 'success')
        return redirect(url_for('view_customer', customer_id=order['customer_id']))

    return render_template('edit_order.html', order=order)

# ---------- DELETE ORDER (Soft Delete) ----------
@app.route('/order/<order_id>/delete', methods=['POST'])
def delete_order(order_id):
    order_ref = db.collection('orders').document(order_id)
    order_doc = order_ref.get()
    if not order_doc.exists:
        flash('Order not found.', 'error')
        return redirect(request.referrer or url_for('view_orders'))

    # Soft delete: mark order as deleted
    order_ref.update({'is_deleted': True, 'deleted_at': firestore.SERVER_TIMESTAMP})
    flash('Order deleted successfully.', 'success')

    # Redirect back to the customer profile if possible
    customer_id = order_doc.to_dict().get('customer_id')
    if customer_id:
        return redirect(url_for('view_customer', customer_id=customer_id))
    return redirect(url_for('view_orders'))

@app.route('/customer/<customer_id>/new_order', methods=['GET', 'POST'])
def new_order_for_customer(customer_id):
    """Create a new order pre-selecting the given customer."""
    customer_ref = db.collection('customers').document(customer_id)
    customer_doc = customer_ref.get()
    if not customer_doc.exists:
        flash('Customer not found.', 'error')
        return redirect(url_for('customers'))

    customer = customer_doc.to_dict()

    if request.method == 'POST':
        data = {
            'customer_id': customer_id,
            'customer_name': customer.get('name'),
            'dress_type': request.form.get('dress_type', '').strip(),
            'occasion': request.form.get('occasion', '').strip(),
            'fabric': request.form.get('fabric', '').strip(),
            'delivery_date': request.form.get('delivery_date', '').strip(),
            'design_notes': request.form.get('design_notes', '').strip(),
            'status': 'Pending',
            'created_at': firestore.SERVER_TIMESTAMP
        }

        links = [l.strip() for l in request.form.getlist('reference_links') if l.strip()]
        single_link = request.form.get('reference_link', '').strip()
        if single_link:
            links.insert(0, single_link)
        if links:
            data['reference_links'] = links

        db.collection('orders').add(data)
        flash('Order added successfully!', 'success')
        return redirect(url_for('view_customer', customer_id=customer_id))

    return render_template('new_order.html', customers=[{'id': customer_id, 'name': customer.get('name')}])

@app.route('/new_order', methods=['GET', 'POST'])
def new_order():
    """Create a new order for a selected customer."""
    customers_list = []
    for doc in db.collection('customers').stream():
        d = doc.to_dict()
        customers_list.append({'id': doc.id, 'name': d.get('name', 'Unnamed')})
    customers_list.sort(key=lambda x: (x['name'] or '').lower())

    if request.method == 'POST':
        customer_id = request.form.get('customer_id')
        if not customer_id:
            flash('Please select a customer.', 'error')
            return render_template('new_order.html', customers=customers_list)

        customer_ref = db.collection('customers').document(customer_id)
        customer_doc = customer_ref.get()
        if not customer_doc.exists:
            flash('Customer not found.', 'error')
            return render_template('new_order.html', customers=customers_list)

        customer = customer_doc.to_dict()
        data = {
            'customer_id': customer_id,
            'customer_name': customer.get('name'),
            'dress_type': request.form.get('dress_type', '').strip(),
            'occasion': request.form.get('occasion', '').strip(),
            'fabric': request.form.get('fabric', '').strip(),
            'delivery_date': request.form.get('delivery_date', '').strip(),
            'design_notes': request.form.get('design_notes', '').strip(),
            'status': 'Pending',
            'created_at': firestore.SERVER_TIMESTAMP
        }

        # handle optional reference links
        links = [l.strip() for l in request.form.getlist('reference_links') if l.strip()]
        single_link = request.form.get('reference_link', '').strip()
        if single_link:
            links.insert(0, single_link)
        if links:
            data['reference_links'] = links

        db.collection('orders').add(data)
        flash('Order added successfully!', 'success')
        return redirect(url_for('view_customer', customer_id=customer_id))

    return render_template('new_order.html', customers=customers_list)


# ---------- TASKS ----------
@app.route('/tasks')
def daily_tasks():
    """Display today’s tailoring or pickup/delivery tasks."""
    today_str = datetime.now().strftime('%Y-%m-%d')
    tasks_ref = db.collection('tasks').where('date', '==', today_str)
    tasks = [t.to_dict() for t in tasks_ref.stream()]
    return render_template('tasks.html', tasks=tasks, today=today_str)


# ---------- RUN ----------
if __name__ == '__main__':
    app.run(debug=True)
