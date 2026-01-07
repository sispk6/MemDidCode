import os
import sys
from pathlib import Path

# Add project root to path
root_path = Path(__file__).parent.parent
sys.path.insert(0, str(root_path))

from src.storage.vector_store import VectorStore
from src.utils.config_loader import load_config

def debug_vector_store():
    config = load_config()
    storage_config = config['storage']
    
    print(f"Connecting to ChromaDB at: {storage_config['chromadb_path']}")
    vs = VectorStore(
        persist_directory=storage_config['chromadb_path'],
        collection_name=storage_config['collection_name']
    )
    
    count = vs.collection.count()
    print(f"Total documents in collection: {count}")
    
    if count == 0:
        print("Collection is empty!")
        return
        
    # Peek at some documents
    peek = vs.collection.peek(limit=5)
    
    print("\n--- Sample Documents ---")
    for i in range(len(peek['ids'])):
        print(f"ID: {peek['ids'][i]}")
        metadata = peek['metadatas'][i]
        print(f"Metadata: {metadata}")
        user_id = metadata.get('user_id')
        print(f"User ID: {user_id}")
        print(f"Doc: {peek['documents'][i][:100]}...")
        print("-" * 20)

if __name__ == "__main__":
    debug_vector_store()
