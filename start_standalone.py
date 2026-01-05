"""
Did-I Standalone Launcher
Run this script to launch the standalone web interface with dedicated configuration.
Usage: python start_standalone.py
"""
import uvicorn
import os
import sys
import webbrowser
import time
import threading
from pathlib import Path
from src.utils.config_loader import load_config

# Set the config file environment variable BEFORE importing other modules that might load it
os.environ["MEMDID_CONFIG_FILE"] = "config_standalone.yaml"

def open_browser(url):
    """Wait a bit then open the browser"""
    time.sleep(1.5)
    print(f"[INFO] Opening browser to {url}")
    webbrowser.open(url)

def main():
    print("-" * 50)
    print("      Did-I Personal Memory Assistant")
    print("      Standalone Mode")
    print("-" * 50)

    # 1. Load config to check auth status
    # Note: config_loader uses the env var we just set
    config = load_config()
    gmail_config = config.get('gmail', {})
    token_file = gmail_config.get('token_file', 'token.json')
    
    # Resolve against project root if relative
    root_path = Path(__file__).parent
    if not os.path.isabs(token_file):
        token_path = root_path / token_file
    else:
        token_path = Path(token_file)

    # 2. Determine start URL
    if token_path.exists():
        start_url = "http://localhost:8000/"
        print("[INFO] Authentication found. Launching Dashboard.")
    else:
        start_url = "http://localhost:8000/static/setup.html"
        print("[INFO] Authentication NOT found. Launching Setup Wizard.")

    # 3. Launch Browser in background thread
    threading.Thread(target=open_browser, args=(start_url,), daemon=True).start()

    # 4. Run Server
    print("Launching server...")
    print("Press Ctrl+C to stop.")
    print("-" * 50)
    
    # We point to the web_interface.api module
    uvicorn.run("web_interface.api:app", host="127.0.0.1", port=8000, reload=False)

if __name__ == "__main__":
    main()
