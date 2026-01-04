"""
Did-I Dashboard Starter
Run this script to launch the standalone web interface.
Usage: python start_ui.py
"""
import uvicorn
import os
import sys
from pathlib import Path

def main():
    # Ensure dependencies are available
    try:
        import fastapi
        import uvicorn
    except ImportError:
        print("[ERROR] FastAPI and Uvicorn not found.")
        print("Please run: pip install fastapi uvicorn")
        sys.exit(1)

    print("-" * 50)
    print("      Did-I Personal Memory Assistant UI")
    print("-" * 50)
    print("Launching dashboard...")
    print("URL: http://localhost:8000")
    print("Press Ctrl+C to stop.")
    print("-" * 50)

    # Run the server
    # We point to the web_interface.api module
    uvicorn.run("web_interface.api:app", host="127.0.0.1", port=8000, reload=True)

if __name__ == "__main__":
    main()
