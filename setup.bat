@echo off
echo === Proton Mail Cleaner Setup (Windows) ===

:: Create venv if not exists
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

:: Activate venv
call venv\Scripts\activate

:: Upgrade pip
python -m pip install --upgrade pip

:: Install dependencies
echo Installing requirements...
pip install -r requirements.txt

:: Launch app
echo Starting Proton Mail Cleaner...
python run.py
