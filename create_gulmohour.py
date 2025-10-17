import os
from pathlib import Path
import textwrap
import zipfile

# Root directory
root = Path("gulmohour_boutique_app")
(root / "templates").mkdir(parents=True, exist_ok=True)
(root / "static").mkdir(parents=True, exist_ok=True)

# Files and their content
files = {
    "app.py": textwrap.dedent("""\
        from flask import Flask, render_template, request, redirect, url_for, flash
        import firebase_admin
        from firebase_admin import credentials, firestore
        from datetime import datetime

        app = Flask(__name__)
        app.secret_key = 'gulmohour-secret'

        cred = credentials.Certificate("firebase-key.json")
        firebase_admin.initialize_app(cred)
        db = firestore.client()

        @app.route('/')
        def dashboard():
            orders_ref = db.collection('orders')
            orders = [doc.to_dict() for doc in orders_ref.stream()]
            pending = [o for o in orders if o.get('status') != 'Delivered']
            return render_template('dashboard.html', orders=pending)

        @app.route('/new_customer', methods=['GET', 'POST'])
        def new_customer():
            if request.method == 'POST':
                data = {
                    'name': request.form['name'],
                    'phone': request.form['phone'],
                    'email': request.form['email'],
                    'measurements': {
                        'bust': request.form['bust'],
                        'waist': request.form['waist'],
                        'hips': request.form['hips'],
                        'length': request.form['length']
                    }
                }
                db.collection('customers').add(data)
                flash('Customer added successfully!')
                return redirect(url_for('new_customer'))
            return render_template('new_customer.html')

        @app.route('/new_order', methods=['GET', 'POST'])
        def new_order():
            customers = [c.to_dict() | {'id': c.id} for c in db.collection('customers').stream()]
            if request.method == 'POST':
                customer_id = request.form['customer']
                customer = db.collection('customers').document(customer_id).get().to_dict()
                measurements = customer.get('measurements', {}).copy()
                for k in measurements.keys():
                    if request.form.get(k):
                        measurements[k] = request.form[k]
                order = {
                    'customer_name': customer['name'],
                    'design_link': request.form['design_link'],
                    'customization': request.form['customization'],
                    'vendor': request.form['vendor'],
                    'amount': request.form['amount'],
                    'status': 'In Progress',
                    'delivery_date': request.form['delivery_date'],
                    'measurements': measurements,
                    'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                db.collection('orders').add(order)
                flash('Order created successfully!')
                return redirect(url_for('new_order'))
            return render_template('new_order.html', customers=customers)

        @app.route('/orders')
        def view_orders():
            orders_ref = db.collection('orders')
            orders = [doc.to_dict() for doc in orders_ref.stream()]
            return render_template('view_orders.html', orders=orders)

        @app.route('/tasks')
        def daily_tasks():
            today = datetime.now().strftime("%Y-%m-%d")
            orders_ref = db.collection('orders')
            due_orders = [o.to_dict() for o in orders_ref.stream() if o.to_dict().get('delivery_date') == today]
            return render_template('daily_tasks.html', orders=due_orders)

        if __name__ == "__main__":
            app.run(debug=True)
    """),

    "requirements.txt": "flask\nfirebase-admin\n",

    "README.txt": textwrap.dedent("""\
        🌿 Gulmohour Boutique Management App
        -------------------------------------

        This is a free, local web app to manage customers, orders, measurements,
        vendors, and deliveries for your boutique.

        ⚙️ Setup Steps
        1. Install Python 3.9 or later
        2. Open terminal (Mac/Linux) or command prompt (Windows)
        3. Run:
           pip install -r requirements.txt
        4. Follow Firebase setup in firebase_setup_instructions.txt
        5. Place your firebase-key.json in the app folder
        6. Run the app:
           python app.py
        7. Open your browser:
           http://localhost:5000

        Your data will be stored securely in Firebase (free tier).
    """),

    "firebase_setup_instructions.txt": textwrap.dedent("""\
        🔥 Firebase Setup (Free)
        -------------------------
        1. Go to https://console.firebase.google.com
        2. Click “Add Project” → name it “Gulmohour Boutique”
        3. Click Firestore Database → Create Database (Test Mode)
        4. Go to Project Settings → Service Accounts
        5. Click “Generate New Private Key”
        6. Download and rename to: firebase-key.json
        7. Place it inside the project folder.
    """),

    "templates/base.html": textwrap.dedent("""\
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="UTF-8">
          <title>Gulmohour Boutique</title>
          <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
        </head>
        <body>
          <header>
            <h1>🌿 Gulmohour Boutique</h1>
            <nav>
              <a href="/">Dashboard</a> |
              <a href="/new_customer">Add Customer</a> |
              <a href="/new_order">New Order</a> |
              <a href="/orders">View Orders</a> |
              <a href="/tasks">Today's Tasks</a>
            </nav>
          </header>
          <main>
            {% with messages = get_flashed_messages() %}
              {% if messages %}
                <ul class="flashes">
                  {% for msg in messages %}
                    <li>{{ msg }}</li>
                  {% endfor %}
                </ul>
              {% endif %}
            {% endwith %}
            {% block content %}{% endblock %}
          </main>
        </body>
        </html>
    """),

    "templates/new_customer.html": "<h2>New Customer Form (as above)</h2>",
    "templates/new_order.html": "<h2>New Order Form (as above)</h2>",
    "templates/dashboard.html": "<h2>Dashboard</h2>",
    "static/style.css": "body { font-family: Arial; background: #fafafa; }"
}

# Write files
for path, content in files.items():
    file_path = root / path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content.strip())

# Create ZIP
zip_path = Path("gulmohour_boutique_app.zip")
with zipfile.ZipFile(zip_path, 'w') as zipf:
    for folder, _, filenames in os.walk(root):
        for filename in filenames:
            filepath = Path(folder) / filename
            zipf.write(filepath, filepath.relative_to(root.parent))

print("✅ Project created successfully!")
print(f"📁 Folder: {root.resolve()}")
print(f"🗜️ ZIP: {zip_path.resolve()}")
