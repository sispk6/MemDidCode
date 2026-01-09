"""
Main benchmark script to evaluate search quality.
Path: evaluation/benchmark.py
"""
import sys
import time
import argparse
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.retrieval.search import SearchEngine
from src.storage.vector_store import VectorStore
from src.embeddings.embedder import Embedder
from src.utils.config_loader import load_config
from evaluation.metrics import calculate_mrr, calculate_precision_at_k, aggregate_metrics
from evaluation.evaluator import LLMJudge
from evaluation.synthetic_data import SyntheticDataGenerator

def run_benchmark(user_id: str, test_set_path: str = "evaluation/test_set.json", num_queries: int = 10):
    """
    Run the benchmark on a set of queries.
    """
    config = load_config()
    
    # Initialize Search
    embedder = Embedder(model_name=config['embeddings']['model_name'])
    vector_store = VectorStore(
        persist_directory=config['storage']['chromadb_path'],
        collection_name=config['storage']['collection_name']
    )
    search_engine = SearchEngine(vector_store, embedder)
    judge = LLMJudge()
    
    # Load or generate test set
    if not Path(test_set_path).exists():
        print(f"[INFO] Test set {test_set_path} not found. Generating new one for user {user_id}...")
        gen = SyntheticDataGenerator()
        
        # Fetch documents specific to this user
        all_docs = vector_store.collection.get(
            where={"user_id": user_id},
            limit=200
        )
        
        messages = []
        if all_docs and all_docs['ids']:
            for i in range(len(all_docs['ids'])):
                messages.append({
                    "id": all_docs['ids'][i],
                    "content": all_docs['documents'][i],
                    "subject": all_docs['metadatas'][i].get('subject', '')
                })
        
        if not messages:
            print(f"[ERROR] No messages found for user {user_id} in ChromaDB. Have you run 'python scripts/embed.py --full'?")
            return {}

        test_cases = gen.generate_test_cases(messages, count=num_queries)
        if not test_cases:
            print("[ERROR] Failed to generate any test cases. Check your API key and data quality.")
            return {}
            
        gen.save_test_set(test_cases, test_set_path)
    else:
        with open(test_set_path, 'r') as f:
            import json
            test_cases = json.load(f)
            test_cases = test_cases[:num_queries]

    print(f"\n{'='*60}")
    print(f"RUNNING SEARCH BENCHMARK - {len(test_cases)} Queries")
    print(f"{'='*60}\n")

    overall_results = []
    
    for i, test in enumerate(test_cases, 1):
        query = test['query']
        expected_id = test['expected_id']
        
        print(f"[{i}/{len(test_cases)}] Query: {query[:50]}...")
        
        start_time = time.time()
        results = search_engine.search(query, user_id=user_id, n_results=10)
        latency = (time.time() - start_time) * 1000  # ms
        
        # Calculate Technical Metrics
        mrr = calculate_mrr(results, expected_id)
        p5 = calculate_precision_at_k(results, expected_id, k=5)
        
        # LLM Relevance Score (1-5)
        llm_score = judge.evaluate_results(query, results)
        
        metrics = {
            "mrr": mrr,
            "precision@5": p5,
            "llm_relevance": llm_score,
            "latency_ms": latency
        }
        overall_results.append(metrics)
        print(f"   Done. MRR: {mrr:.2f} | P@5: {p5:.2f} | Rating: {llm_score:.1f} | Latency: {latency:.0f}ms")

    # Aggregate
    final_metrics = aggregate_metrics(overall_results)
    
    print(f"\n{'='*60}")
    print("FINAL BENCHMARK RESULTS")
    print(f"{'='*60}")
    for k, v in final_metrics.items():
        print(f"{k.upper():<15}: {v:.3f}")
    print(f"{'='*60}\n")
    
    return final_metrics

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", type=str, required=True)
    parser.add_argument("--num-queries", type=int, default=5)
    args = parser.parse_args()
    
    run_benchmark(args.user_id, num_queries=args.num_queries)
