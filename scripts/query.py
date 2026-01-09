"""
Query script - Search your personal memory.
Path: scripts/query.py

Usage:
    python scripts/query.py "When did I agree to send the report?"
    python scripts/query.py "What did I discuss about the Q4 budget?"
"""
import sys
from pathlib import Path
import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.embeddings.embedder import Embedder
from src.storage.vector_store import VectorStore
from src.retrieval.search import SearchEngine
from src.utils.config_loader import load_config


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Query your personal memory")
    parser.add_argument("query", type=str, nargs="+", help="The search query")
    parser.add_argument("--user-id", type=str, required=True, help="User ID for multi-tenant search")
    parser.add_argument("--results", type=int, default=3, help="Number of results to return (default: 3)")
    
    args = parser.parse_args()
    query_text = " ".join(args.query)
    user_id = args.user_id
    
    print("=" * 80)
    print(f"Did-I - Personal Memory Search (User: {user_id})")
    print("=" * 80)
    print()
    
    # Load config
    config = load_config()
    embeddings_config = config['embeddings']
    storage_config = config['storage']
    
    # Initialize components
    print("[INFO] Initializing search engine...")
    
    embedder = Embedder(model_name=embeddings_config['model_name'])
    
    vector_store = VectorStore(
        persist_directory=storage_config['chromadb_path'],
        collection_name=storage_config['collection_name']
    )
    
    search_engine = SearchEngine(vector_store, embedder)
    
    print()
    
    # Perform search
    results = search_engine.search(query_text, user_id=user_id, n_results=args.results)
    
    # Display results
    print(search_engine.format_results_for_display(results))
    
    print("=" * 80)
    print("💡 Tip: Refine your search by being more specific!")
    print("=" * 80)


if __name__ == "__main__":
    main()