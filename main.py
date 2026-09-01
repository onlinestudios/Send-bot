
import threading
import os
from bot import run_bot
from web import app

def start_web():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), use_reloader=False)

if __name__ == "__main__":
    t = threading.Thread(target=start_web, daemon=True)
    t.start()
    run_bot()
