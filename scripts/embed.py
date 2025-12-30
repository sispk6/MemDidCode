"""
Embedding script - Generate embeddings and store in ChromaDB.
Path: scripts/embed.py

Usage:
    python scripts/embed.py
"""
import sys
import os
import json
from pathlib import Path
import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.embeddings.embedder import Embedder
from src.preprocessing.cleaner import MessageCleaner
from src.preprocessing.chunker import TextChunker
from src.storage.vector_store import VectorStore


def load_config():
    """Load configuration from config.yaml"""
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def load_latest_raw_data(raw_data_path: str):
    """Load the most recent raw data JSON file"""
    raw_dir = Path(raw_data_path)
    
    if not raw_dir.exists():
        print(f"❌ Directory not found: {raw_dir}")
        return None
    
    # Find all JSON files
    json_files = list(raw_dir.glob("gmail_*.json"))
    
    if not json_files:
        print(f"❌ No data files found in {raw_dir}")
        print("   Run 'python scripts/ingest.py' first")
        return None
    
    # Get the most recent file
    latest_file = max(json_files, key=lambda p: p.stat().st_mtime)
    
    print(f"📂 Loading data from: {latest_file}")
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data


def main():
    print("=" * 80)
    print("DidI? - Embedding Generation & Storage")
    print("=" * 80)
    print()
    
    # Load config
    config = load_config()
    embeddings_config = config['embeddings']
    storage_config = config['storage']
    paths_config = config['paths']
    
    # Load raw data
    print("Step 1: Loading raw message data...")
    data = load_latest_raw_data(paths_config['raw_data'])
    
    if not data:
        return
    
    messages = data.get('messages', [])
    print(f"✅ Loaded {len(messages)} messages")
    print()
    
    # Prepare text for embedding
    print("Step 2: Preprocessing messages...")
    for msg in messages:
        msg['embedding_text'] = MessageCleaner.prepare_for_embedding(msg)
    print(f"✅ Preprocessed {len(messages)} messages")
    print()
    
    # Chunk messages
    print("Step 3: Chunking long messages...")
    chunker = TextChunker(chunk_size=2000, overlap=200)
    chunked_messages = chunker.chunk_messages(messages)
    print(f"✅ Created {len(chunked_messages)} chunks from {len(messages)} messages")
    print()
    
    # Initialize embedder
    print("Step 4: Initializing embedding model...")
    embedder = Embedder(model_name=embeddings_config['model_name'])
    print()
    
    # Generate embeddings
    print("Step 5: Generating embeddings...")
    chunked_messages = embedder.embed_messages(chunked_messages, text_key='embedding_text')
    print()
    
    # Initialize vector store
    print("Step 6: Initializing ChromaDB...")
    vector_store = VectorStore(
        persist_directory=storage_config['chromadb_path'],
        collection_name=storage_config['collection_name']
    )
    print()
    
    # Store in ChromaDB
    print("Step 7: Storing embeddings in ChromaDB...")
    success = vector_store.add_messages(chunked_messages)
    print()
    
    if success:
        # Show stats
        stats = vector_store.get_stats()
        print("=" * 80)
        print("✅ Embedding & Storage complete!")
        print(f"   Collection: {stats['collection_name']}")
        print(f"   Total messages stored: {stats['total_messages']}")
        print(f"   Storage location: {stats['persist_directory']}")
        print("=" * 80)
        print()
        print("Next step: Run 'python scripts/query.py \"your question\"' to search")
    else:
        print("❌ Storage failed")


if __name__ == "__main__":
    main()