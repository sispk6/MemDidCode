import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.retrieval.brain import RAGBrain

def main():
    print("Initializing RAGBrain...")
    try:
        brain = RAGBrain()
        if hasattr(brain.model, 'model_name'): # Check if generative model has this attribute
             print(f"Model initialized: {brain.model.model_name}")
        else:
             print(f"Model initialized with name: {brain.model_name}")
        
        print("Model configuration check passed.")
        
        # Optional: Try a simple generation to be sure
        print("Attempting simple generation...")
        try:
            response = brain.model.generate_content("Hello, can you hear me?")
            print(f"Response received: {response.text[:50]}...")
            print("Verification SUCCESS.")
        except Exception as e:
            print(f"Generation failed: {e}")
            
    except Exception as e:
        print(f"Initialization failed: {e}")

if __name__ == "__main__":
    main()
