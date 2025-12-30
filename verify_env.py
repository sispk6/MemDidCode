
import sys
import importlib

packages = [
    "chromadb",
    "sentence_transformers",
    "googleapiclient",
    "google.auth",
    "bs4",
    "pandas",
    "dateutil",
    "dotenv",
    "yaml",
    "click",
    "pytest",
    "black",
    "flake8"
]

print(f"Python version: {sys.version}")

failed = []
for package in packages:
    try:
        importlib.import_module(package)
        print(f"[OK] {package} imported")
    except ImportError as e:
        print(f"[FAILED] {package} failed: {e}")
        failed.append(package)

if failed:
    sys.exit(1)
else:
    print("All packages verified successfully.")
