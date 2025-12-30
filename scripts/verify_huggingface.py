import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.retrieval.brain import RAGBrain

def main():
    print("Initializing RAGBrain (should use Hugging Face from config)...")
    try:
        brain = RAGBrain()
        
        print(f"Provider: {brain.provider}")
        print(f"Model: {brain.model_name}")
        
        if brain.provider != 'huggingface':
            print("ERROR: Provider is not 'huggingface'. Check config.yaml.")
            return

        if not os.getenv('HUGGINGFACE_API_KEY'):
             print("\n⚠️  WARNING: HUGGINGFACE_API_KEY not found in environment.")
             print("Please add 'HUGGINGFACE_API_KEY=hf_...' to your .env file.")
             # We expect it to fail below if key is missing, but good to warn.
        
        print("\nAttempting simple generation...")
        try:
            # Mock context
            contexts = [{
                'metadata': {'sender_name': 'Test', 'date': '2025-01-01', 'subject': 'Hello'},
                'snippet': 'This is a test message.'
            }]
            
            response = brain.generate_answer("What is this message about?", contexts)
            print(f"\nResponse received:\n{response.get('answer', 'No answer')}")
            
            if response.get('confidence') != 'error':
                print("\n✅ Verification SUCCESS.")
            else:
                print("\n❌ Verification FAILED (API Error).")
                
        except Exception as e:
            print(f"Generation failed: {e}")
            
    except Exception as e:
        print(f"Initialization failed: {e}")

if __name__ == "__main__":
    main()
