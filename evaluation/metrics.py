"""
Standard retrieval metrics for search benchmarking.
Path: evaluation/metrics.py
"""
from typing import List, Dict, Any

def calculate_mrr(results: List[Dict[str, Any]], expected_id: str) -> float:
    """
    Calculate Mean Reciprocal Rank for a single query.
    
    Args:
        results: List of search results
        expected_id: The ID of the document known to be relevant
        
    Returns:
        MRR score (1/rank of first relevant result, or 0 if not found)
    """
    for idx, res in enumerate(results, 1):
        # We check original_id to handle chunked messages
        if res.get('metadata', {}).get('original_id') == expected_id or res.get('id') == expected_id:
            return 1.0 / idx
    return 0.0

def calculate_precision_at_k(results: List[Dict[str, Any]], expected_id: str, k: int = 5) -> float:
    """
    Calculate Precision@K (simplified for single relevant doc).
    
    Args:
        results: List of results
        expected_id: Known relevant ID
        k: Cutoff rank
        
    Returns:
        1.0 if relevant doc is in top K, else 0.0
    """
    top_k = results[:k]
    for res in top_k:
        if res.get('metadata', {}).get('original_id') == expected_id or res.get('id') == expected_id:
            return 1.0
    return 0.0

def aggregate_metrics(all_metrics: List[Dict[str, float]]) -> Dict[str, float]:
    """
    Average metrics across multiple queries.
    """
    if not all_metrics:
        return {}
        
    keys = all_metrics[0].keys()
    aggregated = {key: sum(m[key] for m in all_metrics) / len(all_metrics) for key in keys}
    return aggregated
