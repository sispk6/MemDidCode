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
    
    def _get_reranker(self):
        """Lazy load the reranker"""
        if self.reranker is None:
            from src.embeddings.embedder import Reranker
            self.reranker = Reranker()
        return self.reranker
    
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
        print(f"[SEARCH] Searching for: '{query_text}'")
        
        # Generate query embedding
        query_embedding = self.embedder.embed_text(query_text)
        
        # Build metadata filters
        where = {}
        if platform:
            where['platform'] = platform
        if sender:
            where['sender_email'] = sender
        if entity_id:
            where['sender_entity_id'] = entity_id
        if org:
            where['sender_org'] = org
            
        # Handle multiple filters for ChromaDB
        where_clause = None
        if len(where) > 1:
            where_clause = {"$and": [{k: v} for k, v in where.items()]}
        elif len(where) == 1:
            where_clause = where
            
        # Stage 1: Fast Retrieval (fetch more candidates for reranking)
        # We fetch 40 candidates for better recall before reranking
        initial_n = max(n_results * 4, 40)
        
        results = self.vector_store.search(
            query_embedding=query_embedding.tolist(),
            user_id=user_id,
            n_results=initial_n,
            where=where_clause
        )
        
        # Stage 2: Reranking & Hybrid Scoring
        if results:
            # 1. Enhance with full text for reranker
            enhanced_results = self._enhance_results(results)
            
            # 2. Keyterm Boosting (Simple Hybrid)
            # Give a small boost to matches that contain the exact query words
            query_terms = set(query_text.lower().split())
            for res in enhanced_results:
                text_lower = res['full_text'].lower()
                matches = sum(1 for term in query_terms if term in text_lower)
                if matches > 0:
                    # Apply a small boost (0.02 per matching term)
                    res['similarity'] += (matches * 0.02)
            
            # 3. Cross-Encoder Reranking
            print(f"[SEARCH] Reranking {len(enhanced_results)} candidates...")
            reranker = self._get_reranker()
            enhanced_results = reranker.rerank(query_text, enhanced_results, top_k=n_results)
            
            print(f"[OK] Found and reranked {len(enhanced_results)} results")
            return enhanced_results
        
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
            
            # Re-ranking boost: prioritize email_body over attachment
            source_type = metadata.get('source_type', 'email_body')
            filename = metadata.get('filename', '')
            similarity = result.get('similarity', 0)
            
            if source_type == 'email_body':
                # Slight boost to keep bodies at the top if scores are close
                similarity += 0.05
            
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
                'source_type': source_type,
                'filename': filename,
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