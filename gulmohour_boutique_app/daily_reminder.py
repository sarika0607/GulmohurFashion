"""
daily_reminder.py
Run daily via PythonAnywhere scheduler to email tomorrow's deliveries.
"""

import sys
import os
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta

# --- Add app directory to path so we can reuse Firebase setup ---
sys.path.insert(0, os.path.dirname(__file__))

# --- Config (must match app.py) ---
from dotenv import load_dotenv
load_dotenv()
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')

EMAIL_CONFIG = {
    'sender_email': 'contact.gulmohurfashion@gmail.com',
    'sender_name': 'Gulmohur Fashion',
    'reminder_recipient': 'contact.gulmohurfashion@gmail.com',  # email where you want to receive the reminder
}

FIREBASE_CREDENTIALS = os.environ.get('FIREBASE_CREDENTIALS')

# --- Firebase init ---
import firebase_admin
from firebase_admin import credentials, firestore

def init_firebase():
    try:
        try:
            firebase_admin.get_app()
        except ValueError:
            if FIREBASE_CREDENTIALS:
                cred_dict = json.loads(FIREBASE_CREDENTIALS)
                cred = credentials.Certificate(cred_dict)
            else:
                cred_path = os.path.join(os.path.dirname(__file__), 'firebase-key.json')
                cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception as e:
        print(f"Firebase init failed: {e}")
        return None

# --- Fetch tomorrow's orders ---
def get_tomorrows_deliveries(db):
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    orders_ref = db.collection('orders')
    
    try:
        docs = orders_ref.where('is_deleted', '==', False).stream()
        due = []
        for doc in docs:
            o = doc.to_dict()
            o['id'] = doc.id
            if (o.get('delivery_date') == tomorrow and
                    o.get('status') not in ['Completed', 'Delivered']):
                due.append(o)
        return due, tomorrow
    except Exception as e:
        print(f"Error fetching orders: {e}")
        return [], tomorrow

def get_customer(db, customer_id):
    try:
        doc = db.collection('customers').document(customer_id).get()
        if doc.exists:
            return doc.to_dict()
    except Exception:
        pass
    return None

# --- Build email body ---
def build_email(orders, db, tomorrow_str):
    tomorrow_display = datetime.strptime(tomorrow_str, '%Y-%m-%d').strftime('%d %B %Y')

    if not orders:
        subject = f"Gulmohur - No Deliveries Tomorrow ({tomorrow_display})"
        body = f"""Good morning!

No deliveries are due tomorrow ({tomorrow_display}).

Have a great day!

— Gulmohur Scheduler
"""
        return subject, body

    subject = f"Gulmohur - {len(orders)} Deliver{'y' if len(orders) == 1 else 'ies'} Due Tomorrow ({tomorrow_display})"

    lines = [
        f"Good morning!",
        f"",
        f"You have {len(orders)} order{'s' if len(orders) != 1 else ''} due for delivery tomorrow, {tomorrow_display}.",
        f"",
        f"{'='*50}",
        f"DELIVERY LIST",
        f"{'='*50}",
        f"",
    ]

    for idx, o in enumerate(orders, 1):
        customer = get_customer(db, o.get('customer_id', ''))
        name = customer.get('name', 'Unknown') if customer else o.get('customer_name', 'Unknown')
        phone = customer.get('phone', 'N/A') if customer else 'N/A'
        dress = o.get('dress_type', 'N/A')
        order_num = o.get('order_number', 'N/A')
        balance = o.get('balance_amount', 0)

        lines.append(f"{idx}. {name}")
        lines.append(f"   Phone:      {phone}")
        lines.append(f"   Dress:      {dress}")
        lines.append(f"   Order No:   #{order_num}")
        lines.append(f"   Balance Due: ₹{float(balance):.0f}")
        lines.append(f"")

    lines += [
        f"{'='*50}",
        f"",
        f"Please prepare and confirm deliveries.",
        f"",
        f"— Team Gulmohur",
    ]

    body = '\n'.join(lines)
    return subject, body

# --- Send via SendGrid ---
def send_email(subject, body):
    mail_data = {
        "personalizations": [{
            "to": [{"email": EMAIL_CONFIG['reminder_recipient']}]
        }],
        "from": {
            "email": EMAIL_CONFIG['sender_email'],
            "name": EMAIL_CONFIG['sender_name']
        },
        "subject": subject,
        "content": [{"type": "text/plain", "value": body}]
    }

    data = json.dumps(mail_data).encode('utf-8')
    req = urllib.request.Request(
        'https://api.sendgrid.com/v3/mail/send',
        data=data,
        headers={
            'Authorization': f'Bearer {SENDGRID_API_KEY}',
            'Content-Type': 'application/json'
        },
        method='POST'
    )

    try:
        with urllib.request.urlopen(req) as response:
            print(f"✅ Email sent successfully. Status: {response.status}")
            return True
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"❌ SendGrid error {e.code}: {error_body}")
        return False
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False

# --- Main ---
if __name__ == '__main__':
    print(f"🕐 Running daily reminder: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    db = init_firebase()
    if not db:
        print("❌ Could not connect to Firebase. Exiting.")
        sys.exit(1)

    orders, tomorrow_str = get_tomorrows_deliveries(db)
    print(f"📦 Found {len(orders)} orders due tomorrow ({tomorrow_str})")

    subject, body = build_email(orders, db, tomorrow_str)
    print(f"📧 Sending email: {subject}")

    success = send_email(subject, body)
    sys.exit(0 if success else 1)

