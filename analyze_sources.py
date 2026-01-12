
import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.getcwd())

from src.retrieval.search import SearchEngine
from src.storage.vector_store import VectorStore
from src.embeddings.embedder import Embedder

def analyze_sources(user_id):
    vs = VectorStore()
    eb = Embedder()
    engine = SearchEngine(vs, eb)
    
    test_queries = [
        "What is for dinner?",
        "Indian dinner party hosting",
        "Facebook discount",
        "meeting summary",
        "Home Chef meal delivery"
    ]
    
    print(f"{'Query':<30} | {'Emails':<7} | {'Attach':<7} | Top Source")
    print("-" * 60)
    
    for q in test_queries:
        res = engine.search(q, user_id, n_results=10)
        sources = [r.get('source_type', 'email_body') for r in res]
        
        email_count = sources.count('email_body')
        attach_count = len(sources) - email_count
        top_source = sources[0] if sources else "N/A"
        
        print(f"{q:<30} | {email_count:<7} | {attach_count:<7} | {top_source}")

if __name__ == "__main__":
    load_dotenv()
    user_id = "465aaa1c-beb9-48d7-932a-31d11760e764"
    analyze_sources(user_id)
