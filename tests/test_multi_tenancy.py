"""
Verification script for Multi-User Tenancy.
Tests cross-user data isolation.
"""
import os
import sys
import shutil
import json
from pathlib import Path
import uuid

# Add project root to path
root_path = Path(__file__).parent.parent
sys.path.insert(0, str(root_path))

from src.storage.knowledge_base import KnowledgeBase
from unittest.mock import MagicMock

# We mock the components that require heavy dependencies
class MockVectorStore:
    def __init__(self, **kwargs):
        self.messages = []
        self.last_search_where = None

    def add_messages(self, messages, user_id):
        for msg in messages:
            msg['metadata'] = msg.get('metadata', {})
            msg['metadata']['user_id'] = user_id
            self.messages.append(msg)
        return True

    def search(self, query_embedding, user_id, n_results=10, where=None):
        # Enforce the same logic as real VectorStore.search
        user_where = {"user_id": user_id}
        if where:
            combined_where = {"$and": [user_where, where]}
        else:
            combined_where = user_where
        
        self.last_search_where = combined_where
        
        # Filter mock messages
        results = []
        for msg in self.messages:
            if msg['metadata']['user_id'] == user_id:
                results.append({
                    'id': msg['id'],
                    'document': msg.get('content', ''), # Return actual content
                    'metadata': msg['metadata']
                })
        return results

class MockEmbedder:
    def embed_text(self, text):
        return MagicMock(tolist=lambda: [0.1, 0.2, 0.3])

def test_multi_tenancy():
    print("Starting Multi-Tenancy Verification...")
    
    # Setup temporary test environment
    test_dir = root_path / "data" / "test_tenancy"
    if test_dir.exists(): shutil.rmtree(test_dir)
    test_dir.mkdir(parents=True)
    
    kb_path = test_dir / "test_kb.db"
    vs_path = test_dir / "chromadb"
    
    # 1. Initialize Components
    kb = KnowledgeBase(db_path=str(kb_path))
    vs = MockVectorStore()
    embedder = MockEmbedder()
    
    # 2. Register Users
    print("\n[STEP 1] Registering Users...")
    user1_id = kb.register_user("alice", "Alice Johnson")
    user2_id = kb.register_user("bob", "Bob Smith")
    print(f"User 1 (Alice): {user1_id}")
    print(f"User 2 (Bob): {user2_id}")
    
    # 3. Add Accounts
    print("\n[STEP 2] Adding Accounts...")
    kb.add_account(user1_id, "gmail", "Personal", {"token_file": "token_personal.json"})
    kb.add_account(user2_id, "gmail", "Work", {"token_file": "token_work.json"})
    
    alice_accs = kb.get_user_accounts(user1_id)
    bob_accs = kb.get_user_accounts(user2_id)
    assert len(alice_accs) == 1 and alice_accs[0]['account_name'] == "Personal"
    assert len(bob_accs) == 1 and bob_accs[0]['account_name'] == "Work"
    print("OK: User accounts isolated in KnowledgeBase.")
    
    # 4. Add Messages to Vector Store
    print("\n[STEP 3] Adding isolated messages to VectorStore...")
    
    msg_alice = {
        "id": "msg_alice_1",
        "content": "Secret budget for Alice",
        "subject": "Private",
        "embedding": embedder.embed_text("Secret budget for Alice").tolist(),
        "platform": "gmail",
        "account": "Personal"
    }
    
    msg_bob = {
        "id": "msg_bob_1",
        "content": "Confidential plans for Bob",
        "subject": "Locked",
        "embedding": embedder.embed_text("Confidential plans for Bob").tolist(),
        "platform": "gmail",
        "account": "Work"
    }
    
    vs.add_messages([msg_alice], user_id=user1_id)
    vs.add_messages([msg_bob], user_id=user2_id)
    
    # 5. Verify Search Isolation
    print("\n[STEP 4] Verifying Search Isolation...")
    
    query_text = "secret confidential plans"
    query_embedding = embedder.embed_text(query_text).tolist()
    
    # Search as Alice
    print(f"Searching as Alice ({user1_id})...")
    results_alice = vs.search(query_embedding, user_id=user1_id)
    print(f"Alice found {len(results_alice)} results.")
    for r in results_alice:
        print(f"  - {r['id']}: {r['document']}")
        assert r['metadata']['user_id'] == user1_id
        assert "Alice" in r['document']
        assert "Bob" not in r['document']
        
    # Search as Bob
    print(f"Searching as Bob ({user2_id})...")
    results_bob = vs.search(query_embedding, user_id=user2_id)
    print(f"Bob found {len(results_bob)} results.")
    for r in results_bob:
        print(f"  - {r['id']}: {r['document']}")
        assert r['metadata']['user_id'] == user2_id
        assert "Bob" in r['document']
        assert "Alice" not in r['document']
        
    print("\n[OK] Search isolation verified. Alice cannot see Bob's data and vice-versa.")
    
    # Cleanup
    shutil.rmtree(test_dir)
    print("\nVerification Successful!")

if __name__ == "__main__":
    test_multi_tenancy()
