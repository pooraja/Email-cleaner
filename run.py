# run.py
import subprocess
import threading
import time
from cleaner import run_cleaner

INTERVAL_HOURS = 6   # how often to run cleaner

def cleaner_loop():
    while True:
        try:
            print("▶️ Running cleaner...")
            path = run_cleaner()
            print(f"✅ Report updated: {path}")
        except Exception as e:
            print(f"❌ Cleaner error: {e}")
        time.sleep(INTERVAL_HOURS * 3600)  # wait before next run

if __name__ == "__main__":
    # Start cleaner loop in background
    t = threading.Thread(target=cleaner_loop, daemon=True)
    t.start()

    # Launch Streamlit
    print("▶️ Launching Streamlit dashboard...")
    subprocess.run(["streamlit", "run", "app.py"])
