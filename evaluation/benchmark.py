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


def run_benchmark(user_id: str, test_set_path: str = "evaluation/test_set.json", num_queries: int = 10, metrics: List[str] = None, save_path: str = None):
    """
    Run the benchmark on a set of queries.
    """
    config = load_config()
    
    # Default metrics
    if metrics is None:
        metrics = ["mrr", "p@5", "llm", "latency"]
    
    # Initialize Search
    embedder = Embedder(model_name=config['embeddings']['model_name'])
    vector_store = VectorStore(
        persist_directory=config['storage']['chromadb_path'],
        collection_name=config['storage']['collection_name']
    )
    search_engine = SearchEngine(vector_store, embedder)
    
    judge = None
    if "llm" in metrics:
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
        
        query_metrics = {}
        
        # Calculate Technical Metrics
        if "mrr" in metrics:
            query_metrics["mrr"] = calculate_mrr(results, expected_id)
        if "p@5" in metrics:
            query_metrics["precision@5"] = calculate_precision_at_k(results, expected_id, k=5)
        if "latency" in metrics:
            query_metrics["latency_ms"] = latency
        
        # LLM Relevance Score (1-5)
        if "llm" in metrics and judge:
            llm_score = judge.evaluate_results(query, results)
            query_metrics["llm_relevance"] = llm_score
        
        overall_results.append(query_metrics)
        
        # Print summary line
        parts = []
        if "mrr" in metrics: parts.append(f"MRR: {query_metrics['mrr']:.2f}")
        if "p@5" in metrics: parts.append(f"P@5: {query_metrics['precision@5']:.2f}")
        if "llm" in metrics: parts.append(f"Rating: {query_metrics.get('llm_relevance', 0):.1f}")
        if "latency" in metrics: parts.append(f"Latency: {latency:.0f}ms")
        
        print(f"   Done. {' | '.join(parts)}")

    # Aggregate
    final_metrics = aggregate_metrics(overall_results)
    
    print(f"\n{'='*60}")
    print("FINAL BENCHMARK RESULTS")
    print(f"{'='*60}")
    for k, v in final_metrics.items():
        print(f"{k.upper():<15}: {v:.3f}")
    print(f"{'='*60}\n")
    
    # Save results
    if save_path:
        output_data = {
            "timestamp": time.time(),
            "config": {
                "num_queries": num_queries,
                "metrics": metrics
            },
            "aggregated_metrics": final_metrics,
            "per_query_results": overall_results
        }
        
        # Create directory if needed
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(save_path, 'w') as f:
            import json
            json.dump(output_data, f, indent=2)
        print(f"[INFO] Results saved to {save_path}")

    return final_metrics

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", type=str, required=True)
    parser.add_argument("--num-queries", type=int, default=5)
    parser.add_argument("--metrics", type=str, default="mrr,p@5,llm,latency", help="Comma-separated list of metrics to calculate")
    parser.add_argument("--save-path", type=str, default=None, help="Path to save results JSON")
    args = parser.parse_args()
    
    metrics_list = [m.strip() for m in args.metrics.split(",")]
    
    run_benchmark(args.user_id, num_queries=args.num_queries, metrics=metrics_list, save_path=args.save_path)
