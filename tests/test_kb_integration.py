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

import pytest

TEST_DB = "./data/test_knowledge_base.db"
TEST_CHROMA = "./data/test_chromadb"

@pytest.fixture(scope="module")
def clean_env():
    """Wipe test data."""
    def _wipe():
        if os.path.exists(TEST_DB):
            try:
                os.remove(TEST_DB)
            except PermissionError:
                pass
        if os.path.exists(TEST_CHROMA):
            try:
                shutil.rmtree(TEST_CHROMA)
            except PermissionError:
                pass
    
    _wipe()
    yield
    # _wipe()

@pytest.fixture(scope="module")
def kb(clean_env):
    return KnowledgeBase(db_path=TEST_DB)

@pytest.fixture(scope="module")
def alice_id(kb):
    # 1. Create a Person: Alice
    aid = kb.add_entity("Alice Smith", metadata={"role": "Lead Engineer", "dept": "Core"})
    
    # 2. Add multiple aliases for Alice
    kb.add_alias(aid, "alice@work.com", "email")
    kb.add_alias(aid, "alice.personal@gmail.com", "email")
    kb.add_alias(aid, "U_ALICE_SLACK", "slack_id")
    
    # 3. Create an Org: ABC Corp
    abc_id = kb.add_entity("ABC Corp", entity_type="organization")
    kb.link_to_org(aid, abc_id)
    return aid

def test_kb_resolution(alice_id, kb):
    # Resolve a handle
    resolved = kb.resolve_identity("alice.personal@gmail.com")
    assert resolved is not None
    assert resolved['canonical_name'] == "Alice Smith"
    assert resolved['organization']['canonical_name'] == "ABC Corp"

def test_vector_enrichment(alice_id, kb):
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
        assert meta['sender_entity_id'] == alice_id
        assert meta['sender_org'] == "ABC Corp"
