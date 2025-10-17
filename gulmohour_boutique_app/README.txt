🌿 Gulmohour Boutique Management App
-------------------------------------

This is a free, local web app to manage customers, orders, measurements,
vendors, and deliveries for your boutique.

⚙️ Setup Steps
1. Install Python 3.9 or later
2. Open terminal (Mac/Linux) or command prompt (Windows)
3. Run: If errors, do steps 5-9
   pip install -r requirements.txt
4. Follow Firebase setup in firebase_setup_instructions.txt
5. Install brew 
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

   This downloads and installs Homebrew.

   -- When it finishes, run:

   echo 'eval "$(/usr/local/bin/brew shellenv)"' >> ~/.zprofile
   eval "$(/usr/local/bin/brew shellenv)"
   
   -- Verify it works:

   brew --version

6. Now install a compatible Python:

   download 3.12 from https://www.python.org/downloads/macos/

7. Create virtual env.

   python3.12 -m venv venv
   source venv/bin/activate
   pip install flask firebase-admin

8. Test firestore
   python3.12 -c "import firebase_admin; print('Firebase working!')"

8. Place your firebase-key.json in the app folder
9. Run the app:
   python app.py
10. Open your browser:
   http://localhost:5000

Your data will be stored securely in Firebase (free tier).