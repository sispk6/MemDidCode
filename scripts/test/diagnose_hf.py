import requests
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('HUGGINGFACE_API_KEY')
if not api_key:
    print("No API Key found")
    exit(1)

headers = {"Authorization": f"Bearer {api_key}"}

models_to_test = [
    "openai-community/gpt2"
]

base_urls = [
    "https://router.huggingface.co/hf-inference/models",
    "https://router.huggingface.co/models",
    "https://api-inference.huggingface.co/models"
]

payload = {"inputs": "Hi process this."}

print(f"Testing with key: {api_key[:4]}...")

for model in models_to_test:
    print(f"\n--- Testing Model: {model} ---")
    for base in base_urls:
        url = f"{base}/{model}"
        try:
            print(f"Trying {url}...", end=" ")
            resp = requests.post(url, headers=headers, json=payload, timeout=10)
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                print("SUCCESS!")
                print(resp.json()[:100] if isinstance(resp.json(), str) else str(resp.json())[:100])
                # If success, we found a winner
            else:
                print(f"Error: {resp.text[:100]}")
        except Exception as e:
            print(f"Exception: {e}")
