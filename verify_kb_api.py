
import sqlite3
import json
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

from src.storage.knowledge_base import KnowledgeBase

def verify_kb_api():
    kb = KnowledgeBase()
    user_id = "465aaa1c-beb9-48d7-932a-31d11760e764" # The benchmark user
    
    print(f"Testing get_all_entities for user: {user_id}")
    try:
        entities = kb.get_all_entities(user_id=user_id)
        print(f"[OK] Successfully retrieved {len(entities)} entities.")
    except Exception as e:
        print(f"[ERROR] API logic failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    verify_kb_api()
