"""
Integration test for Knowledge Base and Vector Store.
Verifies that multiple identities map to the same person and enrich metadata.
"""
import sys
import os
import shutil
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage.knowledge_base import KnowledgeBase
from src.storage.vector_store import VectorStore

TEST_DB = "./data/test_knowledge_base.db"
TEST_CHROMA = "./data/test_chromadb"

def setup_clean_env():
    """Wipe test data."""
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    if os.path.exists(TEST_CHROMA):
        shutil.rmtree(TEST_CHROMA)

def test_kb_resolution():
    print("=" * 80)
    print("Testing Knowledge Base Identity Resolution")
    print("=" * 80)
    
    kb = KnowledgeBase(db_path=TEST_DB)
    
    # 1. Create a Person: Alice
    alice_id = kb.add_entity("Alice Smith", metadata={"role": "Lead Engineer", "dept": "Core"})
    print(f"[OK] Added Entity: Alice Smith ({alice_id})")
    
    # 2. Add multiple aliases for Alice
    kb.add_alias(alice_id, "alice@work.com", "email")
    kb.add_alias(alice_id, "alice.personal@gmail.com", "email")
    kb.add_alias(alice_id, "U_ALICE_SLACK", "slack_id")
    print("[OK] Mapped 3 aliases to Alice")
    
    # 3. Create an Org: ABC Corp
    abc_id = kb.add_entity("ABC Corp", entity_type="organization")
    kb.link_to_org(alice_id, abc_id)
    print("[OK] Linked Alice to ABC Corp")
    
    # 4. Resolve a handle
    resolved = kb.resolve_identity("alice.personal@gmail.com")
    assert resolved is not None
    assert resolved['canonical_name'] == "Alice Smith"
    assert resolved['organization']['canonical_name'] == "ABC Corp"
    print("[PASS] Resolved personal email to Alice Smith and ABC Corp")
    
    return alice_id, kb

def test_vector_enrichment(alice_id, kb):
    print("\n" + "=" * 80)
    print("Testing Vector Store Enrichment")
    print("=" * 80)
    
    # Initialize VectorStore with the same KB
    vs = VectorStore(persist_directory=TEST_CHROMA, kb_path=TEST_DB)
    
    # Mock messages from different aliases
    messages = [
        {
            "id": "msg_1",
            "platform": "gmail",
            "from": {"email": "alice@work.com", "name": "Alice"},
            "to": [],
            "date": "2024-12-21T10:00:00Z",
            "subject": "Work update",
            "content": "Checking in on the budget.",
            "embedding": [0.1] * 384
        },
        {
            "id": "msg_2",
            "platform": "slack",
            "from": {"email": "alice.personal@gmail.com", "name": "Ali"},
            "to": [],
            "date": "2024-12-21T11:00:00Z",
            "subject": "Evening chat",
            "content": "Budget looks good.",
            "embedding": [0.2] * 384
        }
    ]
    
    vs.add_messages(messages)
    
    # Verify metadata in ChromaDB
    results = vs.collection.get(ids=["msg_1", "msg_2"], include=['metadatas'])
    
    for meta in results['metadatas']:
        print(f"Message ID: {meta.get('thread_id','')} | From: {meta['sender_email']}")
        print(f"  -> Unified Entity ID: {meta['sender_entity_id']}")
        print(f"  -> Organization: {meta['sender_org']}")
        
        assert meta['sender_entity_id'] == alice_id
        assert meta['sender_org'] == "ABC Corp"
    
    print("\n[PASS] Both distinct emails correctly enriched with shared Entity ID and Org!")

if __name__ == "__main__":
    setup_clean_env()
    try:
        alice_id, kb = test_kb_resolution()
        test_vector_enrichment(alice_id, kb)
        print("\n" + "=" * 80)
        print("KNOWLEDGE BASE INTEGRATION SUCCESSFUL")
        print("=" * 80)
    finally:
        # cleanup
        # setup_clean_env()
        pass
