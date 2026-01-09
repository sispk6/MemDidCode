"""
LLM-as-a-Judge evaluation logic.
Path: evaluation/evaluator.py
"""
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.retrieval.brain import RAGBrain

class LLMJudge:
    """Use an LLM to evaluate search result relevance."""
    
    def __init__(self):
        self.brain = RAGBrain()
        
    def score_relevance(self, query: str, context: str) -> int:
        """
        Ask LLM to score relevance from 1 to 5.
        """
        prompt = f"""Evaluate the relevance of the following search result to the user's query.
Score it from 1 to 5, where:
1: Completely irrelevant
2: Tangentially related but doesn't answer the query
3: Related and provides some context
4: Relevant and helps answer most of the query
5: Highly relevant, perfectly answers the query

Query: {query}
Result Content: {context}

Return ONLY the integer score (1, 2, 3, 4, or 5).
Score:"""

        try:
            # Use the new generic raw generation from RAGBrain
            score_str = self.brain.generate_raw(prompt)
            score_str = score_str.strip()
            return int(score_str[0]) if score_str and score_str[0].isdigit() else 1
        except Exception:
            return 1
        return 1

    def evaluate_results(self, query: str, results: List[Dict[str, Any]]) -> float:
        """
        Return the average LLM relevance score for the top results.
        """
        if not results:
            return 0.0
            
        scores = []
        # Score top 3 results
        for res in results[:3]:
            content = res.get('full_text', '')
            score = self.score_relevance(query, content)
            scores.append(score)
            
        return sum(scores) / len(scores) if scores else 0.0
