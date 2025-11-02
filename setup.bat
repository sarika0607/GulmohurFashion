@echo off
echo -------------------------------------------
echo     Gulmohur Fashion - Windows Setup
echo -------------------------------------------

REM 1. Create virtual environment
echo Creating virtual environment...
python -m venv venv

REM 2. Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate

REM 3. Install dependencies
echo Installing required Python packages...
pip install -r requirements.txt

REM 4. Create secure key directory if not exists
echo Creating key storage folder at C:\keys
if not exist C:\keys mkdir C:\keys

echo -------------------------------------------
echo IMPORTANT: Copy your Firebase key file into:
echo     C:\keys\gulmohur-service-account.json
echo Do this NOW if not already done.
echo -------------------------------------------

REM 5. Create .env file inside app folder
echo Creating .env file inside gulmohour_boutique_app...
echo FIREBASE_KEY_PATH=C:\keys\gulmohur-service-account.json > gulmohour_boutique_app\.env

REM 6. Confirm success
echo -------------------------------------------
echo Setup complete! ✅
echo To start the application:
echo.
echo     venv\Scripts\activate
echo     python gulmohour_boutique_app\app.py
echo -------------------------------------------
pause
