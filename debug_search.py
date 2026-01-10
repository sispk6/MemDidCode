
import sys
import os
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.getcwd())

from src.retrieval.search import SearchEngine
from src.storage.vector_store import VectorStore
from src.embeddings.embedder import Embedder

def debug_query(query_text, expected_id, user_id, log_file):
    vector_store = VectorStore()
    embedder = Embedder()
    engine = SearchEngine(vector_store, embedder)
    
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"\n[DEBUG] Query: {query_text}\n")
        f.write(f"[DEBUG] Expected ID: {expected_id}\n")
        
        # Retrieval
        vector_results = vector_store.search(embedder.embed_text(query_text).tolist(), user_id, n_results=60)
        bm25_results = engine.search_bm25(query_text, user_id, n_results=60)
        
        # RRF Merge
        merged = engine.rrf_merge(vector_results, bm25_results)
        m_ids = [r['id'] for r in merged]
        m_rank = m_ids.index(expected_id) + 1 if expected_id in m_ids else -1
        f.write(f"RRF Rank: {m_rank}\n")
        
        # Final
        final = engine.search(query_text, user_id, n_results=10)
        f_ids = [r['id'] for r in final]
        f_rank = f_ids.index(expected_id) + 1 if expected_id in f_ids else -1
        f.write(f"Final Rank: {f_rank}\n")
        
        f.write("\nTop 10 Final Results:\n")
        for i, res in enumerate(final, 1):
            marker = " [EXPECTED]" if res['id'] == expected_id else ""
            f.write(f"{i}. ID: {res['id']}{marker} | Similarity: {res['similarity']}\n")
            f.write(f"   Subject: {res['subject']}\n")
            f.write(f"   Snippet: {res['snippet'][:150].replace('\n', ' ')}\n")

if __name__ == "__main__":
    load_dotenv()
    user_id = "465aaa1c-beb9-48d7-932a-31d11760e764"
    log_file = "debug_log.txt"
    if os.path.exists(log_file): os.remove(log_file)
    
    # Debug Query 2
    debug_query("What is the best way for me to host a traditional Indian dinner party with minimal effort using a meal delivery service?", 
                "gmail_17b9142fdec6f1d1_chunk_1", user_id, log_file)
    
    # Debug Query 3
    debug_query("How do I get a $5 discount on my Facebook ads?", 
                "gmail_17b9683239c1ed58_chunk_3", user_id, log_file)
