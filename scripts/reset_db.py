#!/usr/bin/env python3
"""
Reset script to clear ChromaDB and user state.
Usage: python scripts/reset_db.py <user_id>
"""
import sys
import os
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage.vector_store import VectorStore
from src.utils.config_loader import load_config

def main():
    parser = argparse.ArgumentParser(description='Reset Did-I data for a specific user')
    parser.add_argument('user_id', type=str, help='User ID to reset data for')
    parser.add_argument('--all', action='store_true', help='Clear ENTIRE ChromaDB collection (dangerous)')
    args = parser.parse_args()

    config = load_config()
    storage_config = config['storage']
    paths_config = config['paths']
    
    print("=" * 50)
    print(f"Database Reset Tool - User: {args.user_id}")
    print("=" * 50)

    # Initialize VectorStore
    vs = VectorStore(
        persist_directory=storage_config['chromadb_path'],
        collection_name=storage_config['collection_name']
    )

    # 1. Clear ChromaDB
    if args.all:
        print("[RESET] Clearing ENTIRE ChromaDB collection...")
        if vs.clear_collection():
            print("[OK] Entire collection cleared.")
        else:
            print("[ERROR] Failed to clear collection.")
            sys.exit(1)
    else:
        print(f"[RESET] Clearing ChromaDB data for user: {args.user_id}")
        if vs.delete_user_data(args.user_id):
            print(f"[OK] User data cleared from ChromaDB.")
        else:
            print(f"[ERROR] Failed to clear user data.")
            sys.exit(1)

    # 2. Clear User State
    state_file = Path(paths_config['users_base_dir']) / args.user_id / "system_state.json"
    if state_file.exists():
        print(f"[RESET] Deleting state file: {state_file}")
        try:
            os.remove(state_file)
            print("[OK] State file deleted.")
        except Exception as e:
            print(f"[ERROR] Failed to delete state file: {e}")
    else:
        print(f"[INFO] No state file found for user {args.user_id}")

    # 3. Optional: Clear raw data for a truly fresh start?
    # For now we'll keep raw data but the next ingest --full will overwrite anyway if needed
    # or just start fresh.

    print("-" * 50)
    print(f"[SUCCESS] Reset complete for user {args.user_id}.")
    print("=" * 50)

if __name__ == "__main__":
    main()
