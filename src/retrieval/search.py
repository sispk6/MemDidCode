"""
Search and retrieval logic.
Path: src/retrieval/search.py
"""
from typing import List, Dict, Any, Optional
from datetime import datetime


class SearchEngine:
    """Handle search queries and result ranking"""
    
    def __init__(self, vector_store, embedder):
        """
        Initialize search engine.
        
        Args:
            vector_store: VectorStore instance
            embedder: Embedder instance
        """
        self.vector_store = vector_store
        self.embedder = embedder
        self.reranker = None # Lazy load reranker to save memory/startup time
        self._bm25_cache = {} # (user_id, filters_hash) -> (bm25, corpus_data)
    
    def _get_reranker(self):
        """Lazy load the reranker"""
        if self.reranker is None:
            from src.embeddings.embedder import Reranker
            self.reranker = Reranker()
        return self.reranker
    
    def rrf_merge(self, vector_results: List[Dict[str, Any]], bm25_results: List[Dict[str, Any]], k: int = 60) -> List[Dict[str, Any]]:
        """Merge results using Reciprocal Rank Fusion (RRF)"""
        scores = {} # id -> rrf_score
        all_docs = {} # id -> doc_data
        
        # Process Vector Results
        for rank, res in enumerate(vector_results, 1):
            doc_id = res['id']
            scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (k + rank)
            all_docs[doc_id] = res
            
        # Process BM25 Results
        for rank, res in enumerate(bm25_results, 1):
            doc_id = res['id']
            scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (k + rank)
            if doc_id not in all_docs:
                all_docs[doc_id] = res
                
        # Sort by RRF score
        merged_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        
        merged_results = []
        for doc_id in merged_ids:
            doc = all_docs[doc_id]
            doc['similarity'] = scores[doc_id] 
            merged_results.append(doc)
            
        return merged_results
    
    def search(self, query_text: str, user_id: str, n_results: int = 10, 
               platform: Optional[str] = None,
               sender: Optional[str] = None,
               entity_id: Optional[str] = None,
               org: Optional[str] = None,
               date_from: Optional[str] = None,
               date_to: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for messages matching the query with optional knowledge-based filters.
        """
        print(f"[SEARCH] Hybrid searching for: '{query_text}'")
        
        # Build metadata filters for Stage 1 Vector Search
        where = {}
        if platform: where['platform'] = platform
        if sender: where['sender_email'] = sender
        if entity_id: where['sender_entity_id'] = entity_id
        if org: where['sender_org'] = org
            
        where_clause = None
        if len(where) > 1:
            where_clause = {"$and": [{k: v} for k, v in where.items()]}
        elif len(where) == 1:
            where_clause = where

        # --- Stage 1: Parallel Retrieval ---
        # Fetch MORE candidates for better recall (increase from 60 to 100)
        print(f"[SEARCH] Fetching vector candidates...")
        vector_results = self.vector_store.search(
            query_embedding=self.embedder.embed_text(query_text).tolist(),
            user_id=user_id,
            n_results=100,
            where=where_clause
        )
        
        # Fetch 100 candidates from BM25 Search (using persistent index in vector_store)
        print(f"[SEARCH] Fetching BM25 candidates...")
        bm25_results = self.vector_store.search_bm25(query_text, user_id, n_results=100)
        
        # Apply metadata filters to BM25 if any (since search_bm25 uses full user corpus)
        if where: # Using 'where' dict instead of 'where_clause'
            bm25_results = [r for r in bm25_results if all(str(r['metadata'].get(k)) == str(v) for k, v in where.items())]

        # --- Stage 2: Merge with RRF ---
        print(f"[SEARCH] Merging results with RRF...")
        merged_results = self.rrf_merge(vector_results, bm25_results)
        
        # --- Stage 3: Reranking & Hybrid Scoring ---
        if merged_results:
            # 1. Enhance with snippets & formatting
            # Note: _enhance_results now maintains RRF scores without artificial boosts
            enhanced_results = self._enhance_results(merged_results)
            
            # 2. Limit candidates to top 30 for the final reranking step
            # This reduces noise and improves speed.
            candidates_to_rerank = enhanced_results[:30]
            
            # 3. Cross-Encoder Reranking (The final quality step)
            print(f"[SEARCH] Reranking {len(candidates_to_rerank)} candidates...")
            reranker = self._get_reranker()
            final_results = reranker.rerank(query_text, candidates_to_rerank, top_k=n_results)
            
            print(f"[OK] Found and reranked {len(final_results)} results")
            return final_results
        
        return []
    
    def _filter_by_date(self, results: List[Dict[str, Any]], 
                       date_from: Optional[str], 
                       date_to: Optional[str]) -> List[Dict[str, Any]]:
        """Filter results by date range"""
        filtered = []
        
        for result in results:
            msg_date_str = result['metadata'].get('date', '')
            if not msg_date_str:
                continue
            
            try:
                msg_date = datetime.fromisoformat(msg_date_str)
                
                if date_from:
                    if msg_date < datetime.fromisoformat(date_from):
                        continue
                
                if date_to:
                    if msg_date > datetime.fromisoformat(date_to):
                        continue
                
                filtered.append(result)
                
            except ValueError:
                # Skip if date parsing fails
                continue
        
        return filtered
    
    def _enhance_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add formatting and snippets to results"""
        enhanced = []
        
        for result in results:
            metadata = result['metadata']
            
            # Format date
            date_str = metadata.get('date', '')
            try:
                date_obj = datetime.fromisoformat(date_str)
                formatted_date = date_obj.strftime('%Y-%m-%d %H:%M')
            except:
                formatted_date = date_str
            
            # Create snippet
            document = result.get('document', '')
            snippet = document[:200] + "..." if len(document) > 200 else document
            
            # Similarity here is the RRF score. No arbitrary boosting.
            similarity = result.get('similarity', 0)
            
            enhanced.append({
                'id': result['id'],
                'subject': metadata.get('subject', '(No Subject)'),
                'sender': metadata.get('sender_name', metadata.get('sender_email', 'Unknown')),
                'sender_email': metadata.get('sender_email', ''),
                'date': formatted_date,
                'platform': metadata.get('platform', ''),
                'snippet': snippet,
                'url': metadata.get('url', ''),
                'similarity': round(similarity, 3),
                'source_type': metadata.get('source_type', 'email_body'),
                'filename': metadata.get('filename', ''),
                'full_text': document
            })
        
        # Re-sort by boosted similarity
        enhanced.sort(key=lambda x: x['similarity'], reverse=True)
        return enhanced
    
    def format_results_for_display(self, results: List[Dict[str, Any]]) -> str:
        """
        Format search results for terminal display.
        
        Args:
            results: List of search results
            
        Returns:
            Formatted string for display
        """
        if not results:
            return "No results found."
        
        output = []
        output.append(f"\n{'='*80}")
        output.append(f"Found {len(results)} results:")
        output.append(f"{'='*80}\n")
        
        for i, result in enumerate(results, 1):
            source_info = f" [Source: {result['source_type']}]"
            if result['filename']:
                source_info += f" ({result['filename']})"
                
            output.append(f"Result #{i} (Score: {result['similarity']}){source_info}")
            output.append(f"  Subject: {result['subject']}")
            output.append(f"  From: {result['sender']} ({result['sender_email']})")
            output.append(f"  Date: {result['date']}")
            output.append(f"  Platform: {result['platform']}")
            
            # Sanitize snippet for Windows terminal (replace non-encodable chars)
            clean_snippet = result['snippet'].encode('ascii', 'replace').decode('ascii')
            output.append(f"  Snippet: {clean_snippet}")
            
            if result['url']:
                output.append(f"  Link: {result['url']}")
            
            output.append(f"{'-'*80}\n")
        
        return '\n'.join(output).replace('\U0001f504', '[SYNC]').replace('\U0001f50d', '[SEARCH]')