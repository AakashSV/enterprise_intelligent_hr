"""
Michelle HR — Desktop Application Launcher
Packages and boots the FastAPI backend and presents a native desktop window.
"""
import os
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import threading
import time
import uvicorn
from backend.app.main import app


def start_server():
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")


def main():
    # Start FastAPI in background daemon thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    time.sleep(1.5)

    print("=" * 60)
    print("🤖 Michelle HR — Enterprise AI HR Platform [Desktop Runtime]")
    print("Human-in-the-Loop (HITL) Mode: STRICTLY ENFORCED")
    print("Serving on: http://127.0.0.1:8000")
    print("=" * 60)

    try:
        import webview
        # Open native OS desktop window
        webview.create_window(
            title="Michelle HR — Enterprise AI Agent",
            url="http://127.0.0.1:8000",
            width=1280,
            height=850,
            resizable=True
        )
        webview.start()
    except ImportError:
        # Fallback to default system browser if webview is not installed
        import webbrowser
        webbrowser.open("http://127.0.0.1:8000")
        print("Desktop Webview not installed. Launched in system browser.")
        print("Press Ctrl+C to terminate.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            sys.exit(0)


if __name__ == "__main__":
    main()
