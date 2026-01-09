"""
Synthetic test data generation for benchmarking.
Path: evaluation/synthetic_data.py
"""
import sys
import json
import random
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.retrieval.brain import RAGBrain
from src.utils.config_loader import load_config

class SyntheticDataGenerator:
    """Generate test queries from actual messages using LLM."""
    
    def __init__(self):
        self.brain = RAGBrain()
        
    def generate_test_cases(self, messages: List[Dict[str, Any]], count: int = 10) -> List[Dict[str, Any]]:
        """
        Generate (Query, DocumentID) pairs from a list of messages.
        """
        test_cases = []
        # Sample messages that have decent length
        candidates = [m for m in messages if len(m.get('content', '')) > 300]
        if not candidates:
            candidates = messages
            
        sample_msgs = random.sample(candidates, min(len(candidates), count * 2))
        
        print(f"[INFO] Generating {count} synthetic test cases...")
        
        for msg in sample_msgs:
            if len(test_cases) >= count:
                break
                
            content = msg.get('content', '')
            subject = msg.get('subject', '')
            
            prompt = f"""Given the following email content, generate a specific natural language question that this email answers perfectly.
The question should be something a user might actually ask their memory assistant.

Subject: {subject}
Content: {content}

Question:"""

            try:
                if self.brain.provider == 'gemini':
                    response = self.brain.model.generate_content(prompt)
                    query = response.text.strip().replace('"', '')
                    if query:
                        test_cases.append({
                            "query": query,
                            "expected_id": msg['id'],
                            "source_hint": subject
                        })
            except Exception as e:
                print(f"[WARN] Failed to generate test case: {e}")
                
        return test_cases

    def save_test_set(self, test_cases: List[Dict[str, Any]], path: str):
        with open(path, 'w') as f:
            json.dump(test_cases, f, indent=2)
        print(f"[OK] Saved {len(test_cases)} test cases to {path}")

    def load_test_set(self, path: str) -> List[Dict[str, Any]]:
        with open(path, 'r') as f:
            return json.load(f)
