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
from src.utils.state_manager import StateManager


def load_config():
    """Load configuration from config.yaml"""
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def get_pending_raw_files(raw_data_path: str, state_mgr: StateManager):
    """Get list of JSON files in raw directory that haven't been embedded yet"""
    raw_dir = Path(raw_data_path)
    
    if not raw_dir.exists():
        print(f"❌ Directory not found: {raw_dir}")
        return []
    
    # Find all JSON files
    json_files = list(raw_dir.glob("gmail_*.json"))
    
    if not json_files:
        print(f"❌ No data files found in {raw_dir}")
        return []
    
    # Sort by modification time (oldest first)
    json_files.sort(key=lambda p: p.stat().st_mtime)
    
    pending_files = []
    for f in json_files:
        # We track files by their basename
        if not state_mgr.is_in_list("embedding", "gmail", f.name):
            pending_files.append(f)
    
    return pending_files


def process_file(file_path: Path, embedder: Embedder, vector_store: VectorStore, chunker: TextChunker, sub_batch_size: int = 100):
    """Process a single raw data file in smaller batches to save memory"""
    import gc
    print(f"[INFO] Processing: {file_path.name}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    messages = data.get('messages', [])
    if not messages:
        print(f"  [SKIP] No messages in {file_path.name}")
        return True
    
    print(f"  Step 1: Preprocessing {len(messages)} messages...")
    for msg in messages:
        msg['embedding_text'] = MessageCleaner.prepare_for_embedding(msg)
    
    print(f"  Step 2: Chunking...", flush=True)
    print(f"  [DEBUG] About to call chunker.chunk_messages with {len(messages)} messages", flush=True)
    chunked_messages = chunker.chunk_messages(messages)
    print(f"  Created {len(chunked_messages)} total chunks")
    
    # Process chunks in smaller sub-batches
    total_chunks = len(chunked_messages)
    success = True
    
    print(f"  Step 3 & 4: Embedding and Storing in sub-batches of {sub_batch_size}...")
    for i in range(0, total_chunks, sub_batch_size):
        sub_batch = chunked_messages[i:i + sub_batch_size]
        
        # Generate embeddings for this sub-batch
        sub_batch = embedder.embed_messages(sub_batch, text_key='embedding_text')
        
        # Store this sub-batch immediately
        if not vector_store.add_messages(sub_batch):
            print(f"  [ERROR] Failed to add sub-batch {i//sub_batch_size + 1}")
            success = False
            break
            
        # Clear sub-batch from memory
        del sub_batch
        gc.collect()
        
        if (i + sub_batch_size) < total_chunks:
            print(f"    Processed {min(i + sub_batch_size, total_chunks)}/{total_chunks} chunks...")

    # Clear large objects
    del chunked_messages
    del messages
    del data
    gc.collect()
    
    return success


def main():
    import argparse
    import gc
    parser = argparse.ArgumentParser(description="Generate embeddings and store in ChromaDB")
    parser.add_argument("--full", action="store_true", help="Force re-embedding of all files")
    parser.add_argument("--batch-size", type=int, default=50, help="Sub-batch size for memory safety (default: 50)")
    args = parser.parse_args()

    print("=" * 80)
    print("DidI? - Embedding Generation & Storage (Memory Optimized)")
    print("=" * 80)
    print(f"[CONFIG] Sub-batch size: {args.batch_size}")
    print()
    
    # Load config
    config = load_config()
    embeddings_config = config['embeddings']
    storage_config = config['storage']
    paths_config = config['paths']
    
    # Initialize StateManager
    state_mgr = StateManager()
    
    # Force reload of preprocessing modules to get latest code
    import sys
    import importlib
    if 'src.preprocessing.chunker' in sys.modules:
        importlib.reload(sys.modules['src.preprocessing.chunker'])
        print("[DEBUG] Reloaded chunker module before instantiation", flush=True)
    if 'src.preprocessing.semantic_cleaner' in sys.modules:
        importlib.reload(sys.modules['src.preprocessing.semantic_cleaner'])
        print("[DEBUG] Reloaded semantic_cleaner module", flush=True)
    
    # Initialize components
    print("Step 1: Initializing components...")
    chunker = TextChunker(chunk_size=2000, overlap=200)
    embedder = Embedder(model_name=embeddings_config['model_name'])
    vector_store = VectorStore(
        persist_directory=storage_config['chromadb_path'],
        collection_name=storage_config['collection_name']
    )
    print()
    
    # Find pending files
    raw_path = paths_config['raw_data']
    if args.full:
        print("[INFO] Full mode: scanning all files regardless of state")
        pending_files = sorted(list(Path(raw_path).glob("gmail_*.json")), key=lambda p: p.stat().st_mtime)
    else:
        pending_files = get_pending_raw_files(raw_path, state_mgr)
    
    if not pending_files:
        print("[OK] Everything up to date. No new files to process.")
        return
    
    print(f"Found {len(pending_files)} files to process.")
    print()
    
    processed_count = 0
    for f in pending_files:
        success = process_file(f, embedder, vector_store, chunker, sub_batch_size=args.batch_size)
        if success:
            state_mgr.add_to_list("embedding", "gmail", f.name)
            processed_count += 1
            print(f"  [OK] Finished {f.name}")
        else:
            print(f"  [ERROR] Failed to process {f.name}")
            break
        
        # Explicitly clear memory between files
        gc.collect()
        print("-" * 40)
    
    # Show stats
    stats = vector_store.get_stats()
    print()
    print("=" * 80)
    print("[OK] Embedding session complete!")
    print(f"   Files processed: {processed_count}")
    print(f"   Total messages in ChromaDB: {stats['total_messages']}")
    print("=" * 80)
    print()
    print("Next step: Run 'python scripts/query.py \"your question\"' to search")


if __name__ == "__main__":
    main()