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
    # Check if query provided
    if len(sys.argv) < 2:
        print("Usage: python scripts/query.py \"your search query\"")
        print()
        print("Examples:")
        print('  python scripts/query.py "When did I agree to send the report?"')
        print('  python scripts/query.py "What did Alice say about the budget?"')
        sys.exit(1)
    
    # Get query from command line
    query = " ".join(sys.argv[1:])
    
    print("=" * 80)
    print("Did-I - Personal Memory Search")
    print("=" * 80)
    print()
    
    # Load config
    config = load_config()
    embeddings_config = config['embeddings']
    storage_config = config['storage']
    
    # Initialize components
    print("🔄 Initializing search engine...")
    
    embedder = Embedder(model_name=embeddings_config['model_name'])
    
    vector_store = VectorStore(
        persist_directory=storage_config['chromadb_path'],
        collection_name=storage_config['collection_name']
    )
    
    search_engine = SearchEngine(vector_store, embedder)
    
    print()
    
    # Perform search
    results = search_engine.search(query, n_results=3)
    
    # Display results
    print(search_engine.format_results_for_display(results))
    
    print("=" * 80)
    print("💡 Tip: Refine your search by being more specific!")
    print("=" * 80)


if __name__ == "__main__":
    main()