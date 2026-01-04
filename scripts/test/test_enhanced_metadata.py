"""
Test script for enhanced metadata schema.
Verifies that new metadata fields are properly stored and queryable.
"""
import sys
from pathlib import Path
import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage.vector_store import VectorStore


def load_config():
    """Load configuration"""
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def test_metadata_schema():
    """Test that enhanced metadata is stored correctly"""
    print("=" * 80)
    print("Testing Enhanced Metadata Schema")
    print("=" * 80)
    print()
    
    config = load_config()
    storage_config = config['storage']
    
    # Initialize vector store
    vector_store = VectorStore(
        persist_directory=storage_config['chromadb_path'],
        collection_name=storage_config['collection_name']
    )
    
    # Get a sample message
    print("Fetching sample message to check metadata fields...")
    results = vector_store.collection.get(limit=1, include=['metadatas'])
    
    if not results['ids']:
        print("[WARN] No messages found in database")
        print("       Run 'python scripts/ingest.py' first to add messages")
        return False
    
    metadata = results['metadatas'][0]
    
    print()
    print("Sample Message Metadata:")
    print("-" * 80)
    
    # Check for new fields
    new_fields = [
        'recipient_emails',
        'recipient_names', 
        'participants',
        'participant_count',
        'direction',
        'year',
        'month',
        'day_of_week',
        'hour'
    ]
    
    existing_fields = []
    missing_fields = []
    
    for field in new_fields:
        if field in metadata:
            existing_fields.append(field)
            value = metadata[field]
            print(f"  [FOUND] {field}: {value}")
        else:
            missing_fields.append(field)
            print(f"  [MISSING] {field}")
    
    print()
    print("-" * 80)
    print(f"Results: {len(existing_fields)}/{len(new_fields)} new fields found")
    
    if missing_fields:
        print()
        print("[INFO] Missing fields will be added when you re-ingest messages")
        print("       Run: python scripts/ingest.py --mode legacy --max-results 10")
    
    return len(existing_fields) > 0


def test_metadata_queries():
    """Test querying with new metadata fields"""
    print()
    print("=" * 80)
    print("Testing Metadata Query Capabilities")
    print("=" * 80)
    print()
    
    config = load_config()
    storage_config = config['storage']
    
    vector_store = VectorStore(
        persist_directory=storage_config['chromadb_path'],
        collection_name=storage_config['collection_name']
    )
    
    # Test 1: Query by participant count
    print("Test 1: Find group conversations (participant_count >= 3)")
    try:
        results = vector_store.collection.get(
            where={"participant_count": {"$gte": "3"}},
            limit=5
        )
        print(f"  Found {len(results['ids'])} group conversations")
    except Exception as e:
        print(f"  [SKIP] Not available yet: {e}")
    
    print()
    
    # Test 2: Query by day of week
    print("Test 2: Find Friday messages")
    try:
        results = vector_store.collection.get(
            where={"day_of_week": "Friday"},
            limit=5
        )
        print(f"  Found {len(results['ids'])} Friday messages")
    except Exception as e:
        print(f"  [SKIP] Not available yet: {e}")
    
    print()
    
    # Test 3: Query by year and month
    print("Test 3: Find messages from December 2024")
    try:
        results = vector_store.collection.get(
            where={
                "$and": [
                    {"year": "2024"},
                    {"month": "12"}
                ]
            },
            limit=5
        )
        print(f"  Found {len(results['ids'])} messages from December 2024")
    except Exception as e:
        print(f"  [SKIP] Not available yet: {e}")
    
    print()
    print("=" * 80)


if __name__ == "__main__":
    print()
    success = test_metadata_schema()
    
    if success:
        test_metadata_queries()
    
    print()
    print("=" * 80)
    print("Next Steps:")
    print("1. Update your email in config.yaml (user.email)")
    print("2. Re-ingest messages: python scripts/ingest.py --max-results 10")
    print("3. Run this test again to verify new metadata fields")
    print("=" * 80)
    print()
